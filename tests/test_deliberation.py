"""T1.2 acceptance tests for visible deterministic deliberation."""

from concord.agents.skeptical_verifier import SkepticalVerifierAgent
from concord.orchestration.casefile import ReconciliationRequest
from concord.orchestration.runner import ReconciliationRunner
from concord.storage.models import ConflictFinding
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session


def _run(runner: ReconciliationRunner, term: str):
    return runner.run(
        ReconciliationRequest(
            question=f"Why do our {term} definitions disagree?",
            term=term,
        )
    )


def test_real_conflict_claims_are_confirmed_by_pairwise_execution(
    reconciliation_runner: ReconciliationRunner,
) -> None:
    case = _run(reconciliation_runner, "Active Customer")
    results = {item.binding_id: frozenset(item.entity_ids) for item in case.execution_results}

    assert len(case.conflict_hypotheses) == 3
    assert {item.data_verdict for item in case.conflict_hypotheses} == {"confirmed"}
    assert all(item.claim and item.skeptic_challenge for item in case.conflict_hypotheses)
    assert all(len(item.evidence_ids) == 2 for item in case.conflict_hypotheses)
    assert all(
        results[item.left_binding_id] != results[item.right_binding_id]
        for item in case.conflict_hypotheses
    )

    hypothesis_step = next(
        step for step in case.agent_trace if step.agent_name == "ConflictHypothesisAgent"
    )
    assert hypothesis_step.deliberations == case.conflict_hypotheses
    assert set(hypothesis_step.evidence_ids) == {evidence.evidence_id for evidence in case.evidence}


def test_wording_decoy_claim_is_overturned_and_persisted(
    reconciliation_runner: ReconciliationRunner,
    postgres_engine: Engine,
) -> None:
    case = _run(reconciliation_runner, "Net Revenue")
    hypothesis = case.conflict_hypotheses[0]

    assert case.verdict == "consistent"
    assert hypothesis.data_verdict == "overturned"
    assert case.execution_results[0].entity_ids == case.execution_results[1].entity_ids
    assert hypothesis.evidence_ids == tuple(item.evidence_id for item in case.evidence)

    persisted_trace = reconciliation_runner.repository.get_agent_trace(case.run_id)
    assert persisted_trace is not None
    persisted_step = next(
        step for step in persisted_trace if step.agent_name == "ConflictHypothesisAgent"
    )
    assert persisted_step.deliberations == case.conflict_hypotheses

    with Session(postgres_engine) as session:
        finding = session.scalar(
            select(ConflictFinding).where(ConflictFinding.run_id == case.run_id)
        )
    assert finding is not None
    assert finding.details["conflict_hypotheses"][0]["data_verdict"] == "overturned"


def test_verifier_rejects_a_ruling_that_disagrees_with_executed_sets(
    reconciliation_runner: ReconciliationRunner,
) -> None:
    case = _run(reconciliation_runner, "Active Customer").model_copy(deep=True)
    case.conflict_hypotheses = (
        case.conflict_hypotheses[0].model_copy(update={"data_verdict": "overturned"}),
        *case.conflict_hypotheses[1:],
    )

    report = SkepticalVerifierAgent().run(case)

    assert report.passed is False
    assert report.checks["hypothesis_rulings_match_executed_sets"] is False
    assert "hypothesis_rulings_match_executed_sets" in report.failures
