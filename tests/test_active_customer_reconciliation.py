"""P2 acceptance tests for the Active Customer vertical slice."""

from uuid import UUID

import pytest
from concord.api.main import create_app
from concord.config import CloudAccessDisabled, Settings
from concord.orchestration.casefile import ReconciliationCase, ReconciliationRequest
from concord.orchestration.runner import ReconciliationRunner
from concord.orchestration.state_machine import ReconciliationState
from concord.providers import FoundryIQProvider, LocalProvider
from concord.storage.models import (
    AuditEvent,
    ConflictFinding,
    EvidenceItem,
    ReconciliationRun,
    SemanticProposal,
)
from concord.storage.repositories import ReconciliationRepository
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session


@pytest.fixture
def active_case(reconciliation_runner: ReconciliationRunner) -> ReconciliationCase:
    return reconciliation_runner.run(
        ReconciliationRequest(question="Why do our Active Customer dashboards disagree?")
    )


def test_active_customer_conflict_detected(active_case: ReconciliationCase) -> None:
    assert active_case.state == ReconciliationState.COMPLETE
    assert active_case.verdict == "conflict"
    assert [result.entity_count for result in active_case.execution_results] == [
        1600,
        1500,
        1334,
    ]
    assert active_case.verifier_report
    assert active_case.verifier_report.passed is True


def test_active_customer_impact_ranked_first(active_case: ReconciliationCase) -> None:
    impact = active_case.impact_assessment

    assert impact
    assert impact.rank == 1
    assert impact.severity == "high"
    assert impact.customer_count_delta == 266
    assert impact.arr_delta > 0
    assert impact.reports_affected == 3


def test_reconciliation_proposal_contains_evidence(
    active_case: ReconciliationCase,
    postgres_engine: Engine,
) -> None:
    proposal = active_case.reconciliation_proposal

    assert proposal
    assert proposal.requires_human_approval is True
    assert set(proposal.evidence_refs) == {item.evidence_id for item in active_case.evidence}
    assert "active contract" in proposal.canonical_definition

    with Session(postgres_engine) as session:
        evidence = session.scalars(
            select(EvidenceItem).where(EvidenceItem.run_id == active_case.run_id)
        ).all()
        persisted_proposal = session.scalar(
            select(SemanticProposal).where(SemanticProposal.run_id == active_case.run_id)
        )
        finding = session.scalar(
            select(ConflictFinding).where(ConflictFinding.run_id == active_case.run_id)
        )

    assert finding and finding.verdict == "conflict"
    assert len(evidence) == 3
    assert all(item.sql_text and "SELECT" in item.sql_text for item in evidence)
    assert persisted_proposal
    assert persisted_proposal.requires_human_approval is True
    assert all(str(item.id) in persisted_proposal.proposal_text for item in evidence)


def test_verified_case_persists_complete_audit_timeline(
    active_case: ReconciliationCase,
    postgres_engine: Engine,
) -> None:
    with Session(postgres_engine) as session:
        run = session.get(ReconciliationRun, active_case.run_id)
        audit_count = session.scalar(
            select(func.count(AuditEvent.id)).where(AuditEvent.run_id == active_case.run_id)
        )

    assert run and run.status == "complete"
    assert run.context_packet["provider_metadata"]["uses_cloud"] is False
    assert audit_count == 10
    assert [entry.state for entry in active_case.audit_log] == [
        ReconciliationState.RESOLVE_CONCEPT,
        ReconciliationState.INSPECT_BINDINGS,
        ReconciliationState.HYPOTHESIZE_CONFLICTS,
        ReconciliationState.EXECUTE_DEFINITIONS,
        ReconciliationState.RANK_IMPACT,
        ReconciliationState.RESOLVE_AUTHORITY,
        ReconciliationState.PROPOSE_OR_REFUSE,
        ReconciliationState.VERIFY,
        ReconciliationState.AUDIT,
        ReconciliationState.COMPLETE,
    ]


def test_context_packet_contains_only_relevant_sections(
    active_case: ReconciliationCase,
) -> None:
    packet = active_case.context_packet

    assert packet
    assert packet.active_scenario == "active_customer"
    assert packet.candidate_definition_ids == active_case.candidate_definitions
    assert set(packet.business_units) == {
        "Finance",
        "Sales",
        "Customer Success",
    }
    assert set(packet.analytical_tables) == {
        "customers",
        "revenue_events",
        "opportunities",
        "contracts",
        "usage_events",
    }
    assert packet.provider_metadata == {
        "name": "LocalProvider",
        "mode": "local",
        "uses_cloud": False,
        "data_type": "synthetic",
        "grounding_kind": "local_registry",
        "execution_source": "deterministic_local_snapshot",
    }
    assert not hasattr(packet, "execution_results")
    assert not hasattr(packet, "reconciliation_proposal")


def test_no_cloud_calls_when_disabled(postgres_engine: Engine) -> None:
    settings = Settings(allow_cloud=False, max_cloud_calls=0)
    provider = FoundryIQProvider(settings=settings)

    with pytest.raises(CloudAccessDisabled):
        ReconciliationRunner(
            provider=provider,  # type: ignore[arg-type]
            repository=ReconciliationRepository(postgres_engine),
            settings=settings,
        )


def test_api_health(
    postgres_engine: Engine,
    p2_local_provider: LocalProvider,
) -> None:
    # Isolate from any developer .env (e.g. ALLOW_CLOUD/AGENT_WORKFLOW_MODE set for
    # a real Fabric bootstrap); health reflects the default local posture.
    app = create_app(
        Settings(_env_file=None),
        provider=p2_local_provider,
        engine=postgres_engine,
    )
    with TestClient(app) as client:
        health = client.get("/health")

    assert health.status_code == 200
    assert health.json() == {
        "status": "ok",
        "orchestration": "Microsoft Agent Framework",
        "workflow_mode": "fast",
        "provider": "LocalProvider",
        "provider_mode": "local",
        "cloud_enabled": False,
        "data_type": "synthetic",
        "llm_provider": "DisabledLLMProvider",
        "llm_enabled": False,
        "llm_model": None,
        "scenario_pack": "business",
        "runtime_profile": "local",
    }


def test_api_post_reconcile(
    postgres_engine: Engine,
    p2_local_provider: LocalProvider,
) -> None:
    app = create_app(
        Settings(),
        provider=p2_local_provider,
        engine=postgres_engine,
    )
    with TestClient(app) as client:
        response = client.post(
            "/reconcile",
            json={
                "question": "Why do our active customer dashboards disagree?",
                "term": "Active Customer",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert UUID(payload["run_id"])
    assert payload["request"]["question"] == "Why do our active customer dashboards disagree?"
    assert payload["verdict"] == "conflict"
    assert payload["state"] == "COMPLETE"
    assert payload["verifier_report"]["passed"] is True


def test_api_post_reconcile_supports_net_revenue(
    postgres_engine: Engine,
    p2_local_provider: LocalProvider,
) -> None:
    app = create_app(
        Settings(),
        provider=p2_local_provider,
        engine=postgres_engine,
    )
    with TestClient(app) as client:
        response = client.post(
            "/reconcile",
            json={
                "question": "Are our Net Revenue definitions equivalent?",
                "term": "Net Revenue",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["verdict"] == "consistent"
    assert payload["reconciliation_proposal"] is None
    assert payload["refusal_reason"] is None
