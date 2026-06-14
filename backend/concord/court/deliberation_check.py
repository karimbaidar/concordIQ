"""Validate a captured Semantic Court transcript before it is trusted as a replay.

Mirrors ``replay_check`` for the agent layer: the artifact must be free of secret-shaped
text, parse as a typed transcript, contain every court role, be a genuine capture (not an
already-replayed file), and carry a content digest that still matches its words — proving
the debate was not edited after capture.
"""

from __future__ import annotations

from pathlib import Path

from concord.config import Settings
from concord.court.transcript import (
    CourtRole,
    DeliberationTranscript,
    TranscriptMode,
    content_digest,
)
from concord.replay_check import SECRET_PATTERNS

_CAPTURE_MODES = {TranscriptMode.LIVE_CAPTURED, TranscriptMode.DETERMINISTIC_FALLBACK}


class DeliberationCheckError(RuntimeError):
    """Raised when a captured transcript is unsafe or has been altered."""


def validate_deliberation_artifact(path: Path) -> DeliberationTranscript:
    """Validate secret hygiene, structure, provenance, and digest integrity."""
    if not path.exists():
        raise DeliberationCheckError(f"Deliberation transcript does not exist: {path}")
    raw = path.read_text(encoding="utf-8")
    for pattern in SECRET_PATTERNS:
        if pattern.search(raw):
            raise DeliberationCheckError(
                f"Transcript contains forbidden secret-shaped text: {pattern.pattern}"
            )
    try:
        transcript = DeliberationTranscript.model_validate_json(raw)
    except ValueError as error:
        raise DeliberationCheckError(f"Transcript is not valid typed JSON: {error}") from error

    if not transcript.turns:
        raise DeliberationCheckError("Transcript has no deliberation turns.")
    roles = {turn.role for turn in transcript.turns}
    missing = set(CourtRole) - roles
    if missing:
        names = ", ".join(sorted(role.value for role in missing))
        raise DeliberationCheckError(f"Transcript is missing court roles: {names}.")
    if transcript.mode not in _CAPTURE_MODES:
        raise DeliberationCheckError(
            "A captured transcript must be live_captured or deterministic_fallback, "
            f"not {transcript.mode.value!r}."
        )
    expected = content_digest(
        source_run_id=transcript.source_run_id,
        term=transcript.term,
        concept_id=transcript.concept_id,
        verdict=transcript.verdict,
        outcome=transcript.outcome,
        authority_status=transcript.authority_status,
        authority_owner=transcript.authority_owner,
        source_evidence_ids=transcript.source_evidence_ids,
        turns=transcript.turns,
        workflow_trace=transcript.workflow_trace,
    )
    if expected != transcript.content_digest:
        raise DeliberationCheckError(
            "Content digest does not match the transcript words; it was altered after capture."
        )
    return transcript


def main() -> None:
    settings = Settings()
    try:
        transcript = validate_deliberation_artifact(settings.court_transcript_path)
    except DeliberationCheckError as error:
        raise SystemExit(f"Deliberation check failed: {error}") from error
    print(
        f"Deliberation transcript passed: {transcript.term}, "
        f"{len(transcript.turns)} turns, mode={transcript.mode.value}, "
        f"outcome={transcript.outcome}."
    )
    print("No obvious secrets were found. The Semantic Court replays with no cloud.")


if __name__ == "__main__":
    main()
