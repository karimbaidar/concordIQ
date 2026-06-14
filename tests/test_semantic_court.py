"""The Semantic Court voices the debate without ever touching the verdict."""

import pytest
from concord.config import ScenarioPack, Settings
from concord.court import (
    CourtNotReady,
    CourtRole,
    SemanticCourt,
    TranscriptMode,
    TurnDisposition,
)
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
    assert transcript.source_run_id == case.run_id
    assert transcript.framework == "Microsoft Agent Framework"
    assert transcript.workflow_trace[0] == "CourtCoordinatorAgent"
    assert transcript.workflow_trace[-1] == "CourtAuditAgent"
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
    assert cited == real_ids
    assert set(transcript.source_evidence_ids) == real_ids
    assert transcript.authority_status == case.authority_assessment.status
    assert transcript.authority_owner == case.authority_assessment.owner
    # Equal counts with unequal identities trigger the targeted replan branch.
    investigators = [t for t in transcript.turns if t.role is CourtRole.INVESTIGATOR]
    assert len(investigators) == 3
    assert any("24" in turn.content for turn in investigators)
    assert "InvestigatorReplanAgent" in transcript.workflow_trace


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
    assert "no proposal" in closing.content.lower()
    assert "InvestigatorReplanAgent" not in transcript.workflow_trace


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
    assert authority.disposition is TurnDisposition.REFUSED


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


# --- Tier 2: the debate is dynamic and adaptive to the evidence -------------------------


def _by_round(transcript, role, round_no):
    return [t for t in transcript.turns if t.role is role and t.round_no == round_no]


def test_conflict_drives_a_multi_round_cross_examination(
    court_runner: ReconciliationRunner,
) -> None:
    from concord.court.roles import ROUND_CHALLENGE, ROUND_REFLECT, ROUND_RESPOND

    case = _run(
        court_runner,
        "Certification Ready",
        "Do HR, Learning and Development, and managers agree on who is Certification Ready?",
    )
    transcript = SemanticCourt().deliberate(case)

    challenges = _by_round(transcript, CourtRole.SKEPTIC, ROUND_CHALLENGE)
    responses = _by_round(transcript, CourtRole.STEWARD, ROUND_RESPOND)
    reflections = _by_round(transcript, CourtRole.SKEPTIC, ROUND_REFLECT)
    assert len(challenges) == 3
    assert len(responses) == 3
    assert len(reflections) == 1
    dispositions = {turn.speaking_for: turn.disposition for turn in responses}
    assert dispositions == {
        "HR": TurnDisposition.NARROWED,
        "Learning & Development": TurnDisposition.DEFENDED,
        "Managers": TurnDisposition.REFRAMED,
    }
    assert all("concede" not in turn.content.lower() for turn in responses)
    # Turn order is well-formed: rounds never go backwards.
    rounds = [turn.round_no for turn in transcript.turns]
    assert rounds == sorted(rounds)
    # The dynamic debate still cannot change the engine's verdict.
    assert transcript.verdict == "conflict"
    assert transcript.outcome == "proposal"


def test_decoy_skips_cross_examination(court_runner: ReconciliationRunner) -> None:
    from concord.court.roles import ROUND_CHALLENGE, ROUND_RESPOND

    case = _run(
        court_runner,
        "Required Training Complete",
        "Are our Required Training Complete definitions operationally equivalent?",
    )
    transcript = SemanticCourt().deliberate(case)

    # Identical result sets => nobody is challengeable => a single consensus turn, no responses.
    skeptic_challenge_round = _by_round(transcript, CourtRole.SKEPTIC, ROUND_CHALLENGE)
    responses = _by_round(transcript, CourtRole.STEWARD, ROUND_RESPOND)
    assert len(skeptic_challenge_round) == 1
    assert "without a dispute" in skeptic_challenge_round[0].content.lower()
    assert responses == []
    assert transcript.outcome == "no_action"


def test_refusal_still_cross_examines_but_publishes_nothing(
    court_runner: ReconciliationRunner,
) -> None:
    from concord.court.roles import ROUND_CHALLENGE

    case = _run(
        court_runner,
        "Exam Eligible",
        "Can we choose one enterprise Exam Eligible definition?",
    )
    transcript = SemanticCourt().deliberate(case)

    assert len(_by_round(transcript, CourtRole.SKEPTIC, ROUND_CHALLENGE)) == 2
    assert transcript.outcome == "refusal"
    assert case.reconciliation_proposal is None
    responses = _by_round(transcript, CourtRole.STEWARD, 6)
    assert responses
    assert {turn.disposition for turn in responses} == {TurnDisposition.REFRAMED}
