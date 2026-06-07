"""Typed Agent Framework trace acceptance tests."""

from uuid import uuid4

from concord.api.main import create_app
from concord.config import Settings
from concord.ms_agent.agents import SPECIALIST_AGENTS
from concord.orchestration.casefile import ReconciliationRequest
from concord.orchestration.runner import ReconciliationRunner
from concord.providers import LocalProvider
from concord.storage.models import AgentTraceEvent
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session


def test_completed_run_persists_complete_typed_agent_trace(
    reconciliation_runner: ReconciliationRunner,
    postgres_engine: Engine,
) -> None:
    case = reconciliation_runner.run(
        ReconciliationRequest(
            question="Why do our Active Customer dashboards disagree?",
            term="Active Customer",
        )
    )

    assert tuple(step.agent_name for step in case.agent_trace) == tuple(
        agent.name for agent in SPECIALIST_AGENTS
    )
    assert tuple(step.step_number for step in case.agent_trace) == tuple(range(1, 11))
    assert {step.provider_mode for step in case.agent_trace} == {"local"}
    assert all(step.input_summary and step.output_summary for step in case.agent_trace)
    assert all(step.duration_ms is not None for step in case.agent_trace[:-1])
    assert case.agent_trace[-1].duration_ms is None

    execution_step = case.agent_trace[4]
    verifier_step = case.agent_trace[8]
    assert execution_step.evidence_ids == tuple(item.evidence_id for item in case.evidence)
    assert verifier_step.verifier_status == "passed"

    with Session(postgres_engine) as session:
        trace_count = session.scalar(
            select(func.count(AgentTraceEvent.id)).where(AgentTraceEvent.run_id == case.run_id)
        )

    assert trace_count == 10
    assert reconciliation_runner.repository.get_agent_trace(case.run_id) == case.agent_trace


def test_agent_trace_api_returns_ordered_completed_run_artifact(
    postgres_engine: Engine,
    p2_local_provider: LocalProvider,
) -> None:
    app = create_app(
        Settings(),
        provider=p2_local_provider,
        engine=postgres_engine,
    )
    with TestClient(app) as client:
        run_response = client.post(
            "/reconcile",
            json={
                "question": "Are our Net Revenue definitions equivalent?",
                "term": "Net Revenue",
            },
        )
        run_id = run_response.json()["run_id"]
        trace_response = client.get(f"/runs/{run_id}/agent-trace")

    assert run_response.status_code == 200
    assert trace_response.status_code == 200
    trace = trace_response.json()
    assert [step["step_number"] for step in trace] == list(range(1, 11))
    assert [step["agent_name"] for step in trace] == [agent.name for agent in SPECIALIST_AGENTS]
    assert trace[4]["evidence_ids"]
    assert trace[8]["verifier_status"] == "passed"


def test_agent_trace_api_rejects_unknown_run(
    postgres_engine: Engine,
    p2_local_provider: LocalProvider,
) -> None:
    app = create_app(
        Settings(),
        provider=p2_local_provider,
        engine=postgres_engine,
    )
    with TestClient(app) as client:
        response = client.get(f"/runs/{uuid4()}/agent-trace")

    assert response.status_code == 404
