"""Verifier guard, recovery, and safe-blocking acceptance tests."""

import asyncio
from uuid import uuid4

import pytest
from concord.ms_agent.agents import SPECIALIST_AGENTS
from concord.ms_agent.workflow import ConcordAgentWorkflow
from concord.orchestration.casefile import ReconciliationCase, ReconciliationRequest
from concord.orchestration.runner import ReconciliationRunner
from concord.orchestration.state_machine import ReconciliationState
from concord.storage.models import ReconciliationRun
from sqlalchemy import Engine
from sqlalchemy.orm import Session


def _case_before_verification(
    runner: ReconciliationRunner,
    *,
    term: str = "Active Customer",
) -> ReconciliationCase:
    case = runner.create_case(
        ReconciliationRequest(
            question=f"Why do our {term} definitions disagree?",
            term=term,
        )
    )
    runner.resolve_concept(case)
    runner.inspect_bindings(case)
    runner.hypothesize_conflicts(case)
    runner.execute_definitions(case)
    runner.rank_impact(case)
    runner.resolve_authority(case)
    runner.reconcile_or_refuse(case)
    return case


def test_strict_verifier_recovers_one_wholly_missing_evidence_output(
    reconciliation_runner: ReconciliationRunner,
) -> None:
    case = _case_before_verification(reconciliation_runner)
    expected_evidence_ids = tuple(item.evidence_id for item in case.evidence)
    case.evidence = ()

    verified = reconciliation_runner.verify_strict(case)

    assert verified.verification_status == "passed"
    assert verified.verifier_attempts == 2
    assert verified.verification_recovery == "execute_definitions"
    assert verified.verifier_report and verified.verifier_report.passed
    assert tuple(item.evidence_id for item in verified.evidence) == expected_evidence_ids
    assert all(item.sql_text.strip() for item in verified.evidence)


def test_strict_verifier_blocks_tampered_sql_and_evidence_ids(
    reconciliation_runner: ReconciliationRunner,
    postgres_engine: Engine,
) -> None:
    case = _case_before_verification(reconciliation_runner)
    first = case.evidence[0].model_copy(
        update={
            "evidence_id": uuid4(),
            "sql_text": "SELECT 1",
        }
    )
    case.evidence = (first, *case.evidence[1:])

    blocked = reconciliation_runner.verify_strict(case)
    finalized = reconciliation_runner.audit(blocked)

    assert finalized.verification_status == "blocked"
    assert finalized.verifier_attempts == 1
    assert finalized.verification_recovery is None
    assert finalized.verdict == "incomplete"
    assert finalized.state == ReconciliationState.VERIFY
    assert finalized.verifier_report
    assert "evidence_ids_match_run_and_bindings" in finalized.verifier_report.failures
    assert "every_result_has_sql_evidence" in finalized.verifier_report.failures
    assert "proposal_cites_required_evidence" in finalized.verifier_report.failures
    assert finalized.audit_log[-1].agent == "AuditAgent"
    assert finalized.audit_log[-1].status == "failed"
    with Session(postgres_engine) as session:
        assert session.get(ReconciliationRun, finalized.run_id) is None


def test_strict_verifier_retries_only_once_then_marks_needs_review(
    reconciliation_runner: ReconciliationRunner,
) -> None:
    case = _case_before_verification(reconciliation_runner)
    case.impact_assessment = None
    case.evidence = (
        case.evidence[0].model_copy(update={"sql_text": "SELECT 1"}),
        *case.evidence[1:],
    )

    reviewed = reconciliation_runner.verify_strict(case)

    assert reviewed.verification_status == "needs_review"
    assert reviewed.verifier_attempts == 2
    assert reviewed.verification_recovery == "rank_impact"
    assert reviewed.verifier_report and not reviewed.verifier_report.passed
    assert "every_result_has_sql_evidence" in reviewed.verifier_report.failures


def test_strict_verifier_blocks_authority_proposal_mismatch(
    reconciliation_runner: ReconciliationRunner,
) -> None:
    case = _case_before_verification(reconciliation_runner)
    assert case.authority_assessment
    case.authority_assessment = case.authority_assessment.model_copy(
        update={"owner": "Unconfigured Owner"}
    )

    blocked = reconciliation_runner.verify_strict(case)

    assert blocked.verification_status == "blocked"
    assert blocked.verifier_attempts == 1
    assert blocked.verification_recovery is None
    assert blocked.verifier_report
    assert "authority_and_decision_are_consistent" in blocked.verifier_report.failures


def test_strict_agent_workflow_returns_blocked_case_without_persistence(
    reconciliation_runner: ReconciliationRunner,
    postgres_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = ReconciliationRunner.reconcile_or_refuse

    def manipulate_evidence(
        runner: ReconciliationRunner,
        case: ReconciliationCase,
    ) -> ReconciliationCase:
        result = original(runner, case)
        result.evidence = (
            result.evidence[0].model_copy(update={"entity_count": 1}),
            *result.evidence[1:],
        )
        return result

    monkeypatch.setattr(
        ReconciliationRunner,
        "reconcile_or_refuse",
        manipulate_evidence,
    )
    result = asyncio.run(
        ConcordAgentWorkflow.from_runner(
            reconciliation_runner,
            mode="strict",
        ).run_result(
            ReconciliationRequest(
                question="Why do our Active Customer dashboards disagree?",
                term="Active Customer",
            )
        )
    )

    assert result.agent_trace == tuple(agent.name for agent in SPECIALIST_AGENTS)
    assert result.case.verification_status == "blocked"
    assert result.case.verdict == "incomplete"
    assert result.case.state == ReconciliationState.VERIFY
    assert tuple(step.agent_name for step in result.case.agent_trace) == tuple(
        agent.name for agent in SPECIALIST_AGENTS
    )
    assert result.case.agent_trace[-2].verifier_status == "blocked"
    assert result.case.agent_trace[-1].verifier_status == "blocked"
    assert result.case.verifier_report
    assert "every_result_has_matching_evidence" in result.case.verifier_report.failures
    with Session(postgres_engine) as session:
        assert session.get(ReconciliationRun, result.case.run_id) is None
