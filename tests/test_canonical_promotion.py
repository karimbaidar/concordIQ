"""T1.5 acceptance tests for governed canonical promotion and rerun."""

import asyncio
from uuid import UUID

import pytest
from concord.api.main import create_app
from concord.config import Settings
from concord.ms_agent.workflow import ConcordAgentWorkflow
from concord.orchestration.casefile import ReconciliationRequest
from concord.orchestration.runner import ReconciliationRunner
from concord.providers import LocalProvider
from concord.storage.models import (
    AuditEvent,
    BusinessTerm,
    MetricDefinition,
    SemanticProposal,
)
from concord.storage.repositories import ProposalAlreadyDecided, UnauthorizedApprover
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session


def _active_customer_case(runner: ReconciliationRunner):
    return runner.run(
        ReconciliationRequest(
            question="Why do our Active Customer dashboards disagree?",
            term="Active Customer",
        )
    )


def test_approval_promotes_exactly_one_canonical_and_audits_it(
    reconciliation_runner: ReconciliationRunner,
    postgres_engine: Engine,
    isolated_canonical_registry: None,
) -> None:
    case = _active_customer_case(reconciliation_runner)

    with pytest.raises(UnauthorizedApprover):
        reconciliation_runner.repository.decide_proposal(
            case.run_id,
            decision="approved",
            approver="Finance",
        )

    result = reconciliation_runner.repository.decide_proposal(
        case.run_id,
        decision="approved",
        approver="Data Governance Council",
    )

    assert result.status == "approved"
    assert result.canonical_definition_id is not None
    assert result.canonical_version == "1"
    assert result.canonical_source_definition_id == "active_customer_customer_success"
    assert result.registry_scope == "concord_iq"

    with Session(postgres_engine) as session:
        term = session.scalar(
            select(BusinessTerm).where(BusinessTerm.canonical_name == "Active Customer")
        )
        assert term is not None
        canonicals = session.scalars(
            select(MetricDefinition).where(
                MetricDefinition.term_id == term.id,
                MetricDefinition.status == "canonical",
            )
        ).all()
        proposal = session.scalar(
            select(SemanticProposal).where(SemanticProposal.run_id == case.run_id)
        )
        promotion = session.scalar(
            select(AuditEvent).where(
                AuditEvent.run_id == case.run_id,
                AuditEvent.event_type == "canonical_promoted",
            )
        )

    assert len(canonicals) == 1
    assert canonicals[0].id == result.canonical_definition_id
    assert canonicals[0].version == "1"
    assert canonicals[0].status == "canonical"
    assert "active contract and qualifying usage" in canonicals[0].rule_text
    assert proposal is not None
    assert proposal.canonical_definition_id == canonicals[0].id
    assert promotion is not None
    assert promotion.actor == "Data Governance Council"
    assert promotion.payload["registry_scope"] == "concord_iq"
    assert promotion.payload["external_writeback"] is False

    with pytest.raises(ProposalAlreadyDecided):
        reconciliation_runner.repository.decide_proposal(
            case.run_id,
            decision="approved",
            approver="Data Governance Council",
        )


def test_rejected_proposal_does_not_promote_a_definition(
    reconciliation_runner: ReconciliationRunner,
    postgres_engine: Engine,
    isolated_canonical_registry: None,
) -> None:
    case = _active_customer_case(reconciliation_runner)

    result = reconciliation_runner.repository.decide_proposal(
        case.run_id,
        decision="rejected",
        approver="Data Governance Council",
    )

    assert result.status == "rejected"
    assert result.canonical_definition_id is None
    assert result.canonical_version is None
    with Session(postgres_engine) as session:
        canonical_count = session.scalar(
            select(func.count())
            .select_from(MetricDefinition)
            .where(MetricDefinition.status == "canonical")
        )
        promotion_count = session.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(
                AuditEvent.run_id == case.run_id,
                AuditEvent.event_type == "canonical_promoted",
            )
        )
        proposal = session.scalar(
            select(SemanticProposal).where(SemanticProposal.run_id == case.run_id)
        )

    assert canonical_count == 0
    assert promotion_count == 0
    assert proposal is not None
    assert proposal.canonical_definition_id is None


def test_new_approval_supersedes_the_previous_canonical_version(
    reconciliation_runner: ReconciliationRunner,
    postgres_engine: Engine,
    isolated_canonical_registry: None,
) -> None:
    first = _active_customer_case(reconciliation_runner)
    second = _active_customer_case(reconciliation_runner)

    first_decision = reconciliation_runner.repository.decide_proposal(
        first.run_id,
        decision="approved",
        approver="Data Governance Council",
    )
    second_decision = reconciliation_runner.repository.decide_proposal(
        second.run_id,
        decision="approved",
        approver="Data Governance Council",
    )

    assert first_decision.canonical_version == "1"
    assert second_decision.canonical_version == "2"
    with Session(postgres_engine) as session:
        definitions = session.scalars(
            select(MetricDefinition).order_by(MetricDefinition.created_at)
        ).all()

    assert [definition.status for definition in definitions] == [
        "superseded",
        "canonical",
    ]
    assert [definition.version for definition in definitions] == ["1", "2"]
    assert definitions[1].id == second_decision.canonical_definition_id


def test_rerun_uses_approved_canonical_and_retains_named_domain_views(
    reconciliation_runner: ReconciliationRunner,
    isolated_canonical_registry: None,
) -> None:
    original = _active_customer_case(reconciliation_runner)
    decision = reconciliation_runner.repository.decide_proposal(
        original.run_id,
        decision="approved",
        approver="Data Governance Council",
    )

    governed = _active_customer_case(reconciliation_runner)

    assert governed.verdict == "consistent"
    assert governed.verification_status == "passed"
    assert governed.reconciliation_proposal is None
    assert governed.requires_human_approval is False
    assert governed.impact_assessment is not None
    assert governed.impact_assessment.customer_count_delta == 0
    assert governed.impact_assessment.arr_delta == 0
    assert len(governed.binding_semantics) == 1
    assert len(governed.execution_results) == 1
    assert governed.execution_results[0].entity_count == 1334
    assert governed.binding_semantics[0].definition_id == ("active_customer_customer_success")
    assert governed.binding_semantics[0].name == (
        "Canonical v1 — approved by Data Governance Council"
    )
    assert governed.conflict_hypotheses == ()
    assert governed.governed_canonical is not None
    assert governed.governed_canonical.canonical_definition_id == (decision.canonical_definition_id)
    assert governed.governed_canonical.approving_run_id == original.run_id
    assert governed.governed_canonical.approved_by == "Data Governance Council"
    assert governed.governed_canonical.registry_scope == "concord_iq"
    assert len(governed.governed_canonical.domain_views) == 3
    assert {view.owner for view in governed.governed_canonical.domain_views} == {
        "Finance",
        "Sales",
        "Customer Success",
    }


def test_api_approve_then_rerun_returns_governed_case(
    postgres_engine: Engine,
    p2_local_provider: LocalProvider,
    isolated_canonical_registry: None,
) -> None:
    app = create_app(
        Settings(_env_file=None),
        provider=p2_local_provider,
        engine=postgres_engine,
    )
    with TestClient(app) as client:
        original = client.post("/demo/run/active-customer").json()
        approved = client.post(
            f"/proposals/{original['run_id']}/approve",
            json={"approver": "Data Governance Council"},
        )
        rerun = client.post(
            "/analyze",
            json={
                "term": "Active Customer",
                "question": "Use the governed Active Customer definition.",
            },
        )

    assert approved.status_code == 200
    assert UUID(approved.json()["canonical_definition_id"])
    assert approved.json()["canonical_version"] == "1"
    assert rerun.status_code == 200
    payload = rerun.json()
    assert payload["verdict"] == "consistent"
    assert payload["governed_canonical"]["version"] == "1"
    assert payload["governed_canonical"]["approving_run_id"] == original["run_id"]
    assert payload["reconciliation_proposal"] is None
    assert len(payload["execution_results"]) == 1


def test_strict_agent_workflow_reruns_the_governed_canonical(
    reconciliation_runner: ReconciliationRunner,
    isolated_canonical_registry: None,
) -> None:
    original = _active_customer_case(reconciliation_runner)
    reconciliation_runner.repository.decide_proposal(
        original.run_id,
        decision="approved",
        approver="Data Governance Council",
    )

    governed = asyncio.run(
        ConcordAgentWorkflow.from_runner(reconciliation_runner, mode="strict").run(
            ReconciliationRequest(
                question="Use the governed Active Customer definition.",
                term="Active Customer",
            )
        )
    )

    assert governed.verification_status == "passed"
    assert governed.verdict == "consistent"
    assert governed.governed_canonical is not None
    assert governed.governed_canonical.version == "1"
    assert len(governed.agent_trace) == 10
