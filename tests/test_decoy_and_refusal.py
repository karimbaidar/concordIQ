"""P3 acceptance tests for decoy rejection, refusal, and demo access."""

from uuid import UUID

import pytest
from concord.api.main import create_app
from concord.config import Settings
from concord.demo import run_demo
from concord.orchestration.casefile import ReconciliationCase, ReconciliationRequest
from concord.orchestration.runner import ReconciliationRunner
from concord.orchestration.state_machine import ReconciliationState
from concord.providers import LocalProvider
from concord.storage.models import ConflictFinding, EvidenceItem, SemanticProposal
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session


@pytest.fixture
def net_revenue_case(
    reconciliation_runner: ReconciliationRunner,
) -> ReconciliationCase:
    return reconciliation_runner.run(
        ReconciliationRequest(
            question="Are our Net Revenue definitions operationally equivalent?",
            term="Net Revenue",
        )
    )


@pytest.fixture
def churned_customer_case(
    reconciliation_runner: ReconciliationRunner,
) -> ReconciliationCase:
    return reconciliation_runner.run(
        ReconciliationRequest(
            question="Can we choose one enterprise Churned Customer definition?",
            term="Churned Customer",
        )
    )


def test_net_revenue_decoy_ruled_out(
    net_revenue_case: ReconciliationCase,
    postgres_engine: Engine,
) -> None:
    evaluations = net_revenue_case.execution_results

    assert net_revenue_case.state == ReconciliationState.COMPLETE
    assert net_revenue_case.verdict == "consistent"
    assert [result.entity_count for result in evaluations] == [1600, 1600]
    assert evaluations[0].entity_ids == evaluations[1].entity_ids
    assert evaluations[0].rows == evaluations[1].rows
    assert evaluations[0].metric_total == evaluations[1].metric_total
    assert net_revenue_case.reconciliation_proposal is None
    assert net_revenue_case.refusal_reason is None
    assert net_revenue_case.requires_human_approval is False
    assert net_revenue_case.impact_assessment
    assert net_revenue_case.impact_assessment.severity == "low"
    assert net_revenue_case.verifier_report
    assert net_revenue_case.verifier_report.passed is True

    with Session(postgres_engine) as session:
        finding = session.scalar(
            select(ConflictFinding).where(ConflictFinding.run_id == net_revenue_case.run_id)
        )
        evidence_count = session.scalar(
            select(func.count(EvidenceItem.id)).where(
                EvidenceItem.run_id == net_revenue_case.run_id
            )
        )
        proposal_count = session.scalar(
            select(func.count(SemanticProposal.id)).where(
                SemanticProposal.run_id == net_revenue_case.run_id
            )
        )

    assert finding and finding.verdict == "consistent"
    assert finding.details["requires_human_approval"] is False
    assert evidence_count == 2
    assert proposal_count == 0


def test_churned_customer_requires_human_approval(
    churned_customer_case: ReconciliationCase,
    postgres_engine: Engine,
) -> None:
    authority = churned_customer_case.authority_assessment

    assert churned_customer_case.state == ReconciliationState.COMPLETE
    assert churned_customer_case.verdict == "conflict"
    assert [result.entity_count for result in churned_customer_case.execution_results] == [333, 666]
    assert authority
    assert authority.status == "ambiguous"
    assert authority.owner is None
    assert {rule.status for rule in authority.rules} == {"shared", "ambiguous"}
    assert churned_customer_case.reconciliation_proposal is None
    assert churned_customer_case.requires_human_approval is True
    assert churned_customer_case.refusal_reason
    assert "human approval is required" in churned_customer_case.refusal_reason.lower()
    assert churned_customer_case.verifier_report
    assert churned_customer_case.verifier_report.passed is True

    with Session(postgres_engine) as session:
        finding = session.scalar(
            select(ConflictFinding).where(ConflictFinding.run_id == churned_customer_case.run_id)
        )
        evidence_count = session.scalar(
            select(func.count(EvidenceItem.id)).where(
                EvidenceItem.run_id == churned_customer_case.run_id
            )
        )
        proposal_count = session.scalar(
            select(func.count(SemanticProposal.id)).where(
                SemanticProposal.run_id == churned_customer_case.run_id
            )
        )

    assert finding and finding.verdict == "conflict"
    assert finding.details["refusal_reason"] == churned_customer_case.refusal_reason
    assert finding.details["requires_human_approval"] is True
    assert evidence_count == 2
    assert proposal_count == 0


def test_demo_scenarios_available(
    postgres_engine: Engine,
    p2_local_provider: LocalProvider,
) -> None:
    app = create_app(
        Settings(),
        provider=p2_local_provider,
        engine=postgres_engine,
    )
    with TestClient(app) as client:
        response = client.get("/demo/scenarios")
        run_response = client.post("/demo/run/churned-customer")

    assert response.status_code == 200
    assert [item["scenario_id"] for item in response.json()] == [
        "active-customer",
        "net-revenue",
        "churned-customer",
    ]
    assert run_response.status_code == 200
    assert UUID(run_response.json()["run_id"])
    assert run_response.json()["refusal_reason"]


def test_headless_demo_prints_all_three_verdicts(
    reconciliation_runner: ReconciliationRunner,
) -> None:
    output: list[str] = []

    cases = run_demo(reconciliation_runner, emit=output.append)

    assert [case.verdict for case in cases] == [
        "conflict",
        "consistent",
        "conflict",
    ]
    assert output == [
        (
            "Active Customer: CONFLICT | counts=1600/1500/1334 | "
            "proposal drafted; human approval required"
        ),
        ("Net Revenue: CONSISTENT | counts=1600/1600 | decoy ruled out; no reconciliation needed"),
        (
            "Churned Customer: CONFLICT | counts=333/666 | "
            "automatic reconciliation refused; human approval required"
        ),
    ]
