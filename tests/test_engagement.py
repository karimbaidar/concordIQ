"""Phase 2 acceptance tests for the engagement layer.

Autonomous portfolio scan, the Concord Score, and the Semantic-PR approval gate
(only the configured authority owner may approve, enforced deterministically).
"""

import pytest
from concord.api.main import create_app
from concord.config import Settings
from concord.orchestration.casefile import ReconciliationCase, ReconciliationRequest
from concord.orchestration.portfolio import scan_portfolio
from concord.orchestration.runner import ReconciliationRunner
from concord.providers import LocalProvider
from concord.storage.repositories import (
    ProposalAlreadyDecided,
    ProposalNotFound,
    UnauthorizedApprover,
)
from fastapi.testclient import TestClient
from sqlalchemy import Engine


def test_portfolio_scan_ranks_conflicts(p2_local_provider: LocalProvider) -> None:
    scan = scan_portfolio(p2_local_provider)

    assert scan.score.concepts_scanned == 4
    # Conflicts ranked by business impact (ARR delta): Churned > Active > Qualified Lead.
    ranked_conflicts = [item.term for item in scan.concepts if item.verdict == "conflict"]
    assert ranked_conflicts == ["Churned Customer", "Active Customer", "Qualified Lead"]
    assert [item.rank for item in scan.concepts if item.verdict == "conflict"] == [1, 2, 3]

    by_term = {item.term: item for item in scan.concepts}
    assert by_term["Net Revenue"].verdict == "consistent"
    assert by_term["Net Revenue"].rank == 0
    assert by_term["Net Revenue"].recommended_action == "monitor"
    assert by_term["Active Customer"].recommended_action == "propose"
    assert by_term["Churned Customer"].recommended_action == "refuse"
    assert by_term["Qualified Lead"].recommended_action == "propose"
    assert by_term["Qualified Lead"].customer_count_delta == 20


def test_concord_score_reflects_conflict_load(p2_local_provider: LocalProvider) -> None:
    score = scan_portfolio(p2_local_provider).score

    assert score.conflicts == 3
    assert score.consistent == 1
    assert score.refusals == 1
    # high(12) + high+refusal(16) + high(12) = 40 penalty -> 60/100, grade D.
    assert score.overall == 60
    assert score.grade == "D"

    units = {unit.business_unit: unit for unit in score.by_business_unit}
    assert set(units) == {"Finance", "Sales", "Customer Success", "Marketing"}
    # Finance carries Active (12) + Churned (16) = 28 -> 72.
    assert units["Finance"].score == 72
    assert units["Marketing"].open_conflicts == 1
    assert units["Marketing"].score == 88


@pytest.fixture
def active_case(reconciliation_runner: ReconciliationRunner) -> ReconciliationCase:
    return reconciliation_runner.run(
        ReconciliationRequest(question="Why do our Active Customer dashboards disagree?")
    )


def test_only_authority_owner_can_approve(
    active_case: ReconciliationCase,
    reconciliation_runner: ReconciliationRunner,
    isolated_canonical_registry: None,
) -> None:
    repository = reconciliation_runner.repository

    state = repository.get_proposal_state(active_case.run_id)
    assert state is not None
    assert state["status"] == "draft"
    assert state["authority_owner"] == "Data Governance Council"

    with pytest.raises(UnauthorizedApprover):
        repository.decide_proposal(active_case.run_id, decision="approved", approver="Finance")

    result = repository.decide_proposal(
        active_case.run_id, decision="approved", approver="Data Governance Council"
    )
    assert result.status == "approved"
    assert result.decided_by == "Data Governance Council"
    assert result.term == "Active Customer"

    # A decided proposal cannot be re-decided.
    with pytest.raises(ProposalAlreadyDecided):
        repository.decide_proposal(
            active_case.run_id, decision="rejected", approver="Data Governance Council"
        )


def test_refusal_has_no_proposal_to_approve(
    reconciliation_runner: ReconciliationRunner,
) -> None:
    case = reconciliation_runner.run(
        ReconciliationRequest(
            question="Can we choose one Churned Customer definition?",
            term="Churned Customer",
        )
    )
    repository = reconciliation_runner.repository

    assert repository.get_proposal_state(case.run_id) is None
    with pytest.raises(ProposalNotFound):
        repository.decide_proposal(case.run_id, decision="approved", approver="Finance")


def test_scan_and_score_endpoints(
    postgres_engine: Engine,
    p2_local_provider: LocalProvider,
) -> None:
    app = create_app(Settings(), provider=p2_local_provider, engine=postgres_engine)
    with TestClient(app) as client:
        scan_response = client.get("/scan")
        score_response = client.get("/score")

    assert scan_response.status_code == 200
    assert len(scan_response.json()["concepts"]) == 4
    assert score_response.status_code == 200
    assert score_response.json()["grade"] == "D"


def test_approval_gate_endpoint_enforces_owner(
    postgres_engine: Engine,
    p2_local_provider: LocalProvider,
    isolated_canonical_registry: None,
) -> None:
    app = create_app(Settings(), provider=p2_local_provider, engine=postgres_engine)
    with TestClient(app) as client:
        run = client.post("/demo/run/active-customer").json()
        run_id = run["run_id"]
        forbidden = client.post(f"/proposals/{run_id}/approve", json={"approver": "Sales"})
        approved = client.post(
            f"/proposals/{run_id}/approve",
            json={"approver": "Data Governance Council"},
        )

    assert forbidden.status_code == 403
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
