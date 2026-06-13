"""Capture one Semantic Court session as a sanitized, replayable transcript.

This extends Concord IQ's existing capture -> replay trust model to the agent layer.
A live run (real model, real Foundry) records the debate; the sanitized transcript is
then replayed deterministically with no cloud and no model, so judges and the hosted
app see the exact same court reasoning the video shows live. The transcript holds only
synthetic facts and reviewed argument text; tenant-shaped tokens are redacted on the way
out and the content digest is recomputed over the sanitized words.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from concord.capture import _secret_values, sanitize_value
from concord.config import ScenarioPack, Settings
from concord.court.orchestrator import SemanticCourt
from concord.court.transcript import DeliberationTranscript, content_digest
from concord.llm import create_llm_provider
from concord.orchestration.casefile import ReconciliationRequest
from concord.orchestration.runner import ReconciliationRunner
from concord.providers import create_provider
from concord.storage.repositories import ReconciliationRepository

DEFAULT_TERM = "Certification Ready"
DEFAULT_QUESTION = (
    "Do HR, Learning and Development, and managers agree on who is Certification Ready?"
)


def sanitize_transcript(
    transcript: DeliberationTranscript,
    *,
    secret_values: tuple[str, ...] = (),
) -> DeliberationTranscript:
    """Redact tenant-shaped text from each turn and recompute the content digest."""
    sanitized_turns = tuple(
        turn.model_copy(
            update={"content": sanitize_value(turn.content, secret_values=secret_values)}
        )
        for turn in transcript.turns
    )
    digest = content_digest(
        term=transcript.term,
        concept_id=transcript.concept_id,
        verdict=transcript.verdict,
        outcome=transcript.outcome,
        turns=sanitized_turns,
    )
    return transcript.model_copy(update={"turns": sanitized_turns, "content_digest": digest})


@contextmanager
def _fresh_runner(settings: Settings) -> Iterator[ReconciliationRunner]:
    """Yield a runner over a disposable schema so capture never pollutes shared state."""
    schema = f"concord_court_{uuid4().hex}"
    admin_engine = create_engine(settings.database_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped_url = make_url(settings.database_url).update_query_dict(
        {"options": f"-csearch_path={schema}"}
    )
    engine = create_engine(scoped_url, pool_pre_ping=True)
    repository = ReconciliationRepository(engine)
    repository.initialize()
    runner = ReconciliationRunner(
        provider=create_provider(settings),
        repository=repository,
        settings=settings,
        llm_provider=create_llm_provider(settings),
    )
    try:
        yield runner
    finally:
        engine.dispose()
        with admin_engine.connect() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


def capture_deliberation(
    settings: Settings | None = None,
    *,
    term: str = DEFAULT_TERM,
    question: str | None = None,
    output_path: Path | None = None,
) -> DeliberationTranscript:
    """Run one Semantic Court session and write the sanitized transcript to disk."""
    # Ground the case in deterministic local data (the counts are identical across providers);
    # the debate's words still come from whatever model `create_llm_provider` returns.
    active = (settings or Settings()).model_copy(
        update={"scenario_pack": ScenarioPack.LEARNING, "provider": "local"}
    )
    destination = output_path or active.court_transcript_path
    with _fresh_runner(active) as runner:
        case = runner.run(ReconciliationRequest(question=question or DEFAULT_QUESTION, term=term))
        transcript = SemanticCourt(runner.llm_provider).deliberate(case)
    sanitized = sanitize_transcript(transcript, secret_values=_secret_values(active))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(sanitized.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return sanitized


def main() -> None:
    """Capture the Certification Ready deliberation (a `make` target)."""
    settings = Settings()
    transcript = capture_deliberation(settings)
    print(f"Wrote Semantic Court transcript to {settings.court_transcript_path}")
    print(
        f"  term={transcript.term} | verdict={transcript.verdict} | "
        f"outcome={transcript.outcome} | mode={transcript.mode.value} | "
        f"turns={len(transcript.turns)}"
    )
    print("Review the sanitized transcript before staging it.")


if __name__ == "__main__":
    main()
