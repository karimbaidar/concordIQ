"""The Semantic Court voices the debate without ever touching the verdict."""

import pytest
from concord.config import ScenarioPack, Settings
from concord.court import CourtNotReady, CourtRole, SemanticCourt, TranscriptMode
from concord.llm import LLMMode, NarrationRequest, NarrationResult
from concord.orchestration.casefile import ReconciliationCase, ReconciliationRequest
from concord.orchestration.runner import ReconciliationRunner
from concord.providers import LocalProvider
from concord.seed.seed_duckdb import seed_duckdb
from concord.storage.repositories import ReconciliationRepository
from sqlalchemy import Engine


@pytest.fixture(scope="session")
def court_provider(tmp_path_factory: pytest.TempPathFactory) -> LocalProvider:
    data_dir = tmp_path_factory.mktemp("court-synthetic")
    database_path = data_dir / "concord-iq.duckdb"
    seed_duckdb(database_path=database_path, data_dir=data_dir / "csv")
    return LocalProvider.for_scenario_pack(ScenarioPack.LEARNING, duckdb_path=database_path)


@pytest.fixture
def court_runner(postgres_engine: Engine, court_provider: LocalProvider) -> ReconciliationRunner:
    return ReconciliationRunner(
        provider=court_provider,
        repository=ReconciliationRepository(postgres_engine),
        settings=Settings(_env_file=None, scenario_pack=ScenarioPack.LEARNING),
    )


def _run(runner: ReconciliationRunner, term: str, question: str) -> ReconciliationCase:
    return runner.run(ReconciliationRequest(question=question, term=term))


class _FakeModel:
    """A non-network narration provider that reports generated text (live-like)."""

    name = "FakeFoundryModel"
    mode = LLMMode.OLLAMA
    enabled = True
    model = "fake-court-model"

    def narrate(self, request: NarrationRequest) -> NarrationResult:
        return NarrationResult(
            task=request.task,
            text=f"[{request.task.value}] {request.fallback_text}",
            provider_name=self.name,
            model=self.model,
            generated=True,
        )


def test_court_voices_the_conflict_without_changing_it(
    court_runner: ReconciliationRunner,
) -> None:
    case = _run(
        court_runner,
        "Certification Ready",
        "Do HR, Learning and Development, and managers agree on who is Certification Ready?",
    )
    before = (case.verdict, case.reconciliation_proposal, case.refusal_reason)

    transcript = SemanticCourt().deliberate(case)

    # The court never mutates the earned outcome.
    assert (case.verdict, case.reconciliation_proposal, case.refusal_reason) == before
    assert transcript.verdict == "conflict"
    assert transcript.outcome == "proposal"
    # Every role spoke.
    roles_present = {turn.role for turn in transcript.turns}
    assert roles_present == set(CourtRole)
    # Three stewards, one per owner.
    stewards = [turn for turn in transcript.turns if turn.role is CourtRole.STEWARD]
    assert {turn.speaking_for for turn in stewards} == {"HR", "Learning & Development", "Managers"}
    # Disabled LLM => honest deterministic-fallback provenance.
    assert transcript.mode is TranscriptMode.DETERMINISTIC_FALLBACK
    assert all(turn.provenance.generated is False for turn in transcript.turns)
    # The court can only cite evidence that exists in the casefile.
    real_ids = {record.evidence_id for record in case.evidence}
    cited = {eid for turn in transcript.turns for eid in turn.cited_evidence_ids}
    assert cited and cited <= real_ids
    # The investigator quantifies the divergence from real impact evidence.
    investigator = next(t for t in transcript.turns if t.role is CourtRole.INVESTIGATOR)
    assert "24" in investigator.content


def test_court_dismisses_the_decoy(court_runner: ReconciliationRunner) -> None:
    case = _run(
        court_runner,
        "Required Training Complete",
        "Are our Required Training Complete definitions operationally equivalent?",
    )
    transcript = SemanticCourt().deliberate(case)

    assert transcript.verdict == "consistent"
    assert transcript.outcome == "no_action"
    closing = transcript.turns[-1]
    assert closing.role is CourtRole.ORCHESTRATOR
    assert "no reconciliation" in closing.content.lower()


def test_court_records_a_governed_refusal(court_runner: ReconciliationRunner) -> None:
    case = _run(
        court_runner,
        "Exam Eligible",
        "Can we choose one enterprise Exam Eligible definition?",
    )
    transcript = SemanticCourt().deliberate(case)

    assert transcript.verdict == "conflict"
    assert transcript.outcome == "refusal"
    authority = next(t for t in transcript.turns if t.role is CourtRole.AUTHORITY)
    assert "refuse" in authority.content.lower()


def test_live_model_is_labeled_live_and_still_cannot_change_the_verdict(
    court_runner: ReconciliationRunner,
) -> None:
    case = _run(
        court_runner,
        "Certification Ready",
        "Do HR, Learning and Development, and managers agree on who is Certification Ready?",
    )
    transcript = SemanticCourt(_FakeModel()).deliberate(case)

    assert transcript.mode is TranscriptMode.LIVE_CAPTURED
    assert any(turn.provenance.generated for turn in transcript.turns)
    assert all(turn.provenance.provider_name == "FakeFoundryModel" for turn in transcript.turns)
    # Live narration still reports the deterministic verdict/outcome.
    assert transcript.verdict == "conflict"
    assert transcript.outcome == "proposal"


def test_court_refuses_an_incomplete_case() -> None:
    empty = ReconciliationCase(
        request=ReconciliationRequest(question="x", term="Certification Ready")
    )
    with pytest.raises(CourtNotReady):
        SemanticCourt().deliberate(empty)
