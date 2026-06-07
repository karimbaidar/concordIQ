"""Microsoft Agent Framework integration acceptance tests."""

import asyncio

import pytest
from concord.config import CloudAccessDisabled, Settings
from concord.ms_agent.agents import SPECIALIST_AGENTS
from concord.ms_agent.foundry_hosted_entrypoint import build_hosted_agent
from concord.ms_agent.workflow import ConcordAgentWorkflow
from concord.orchestration.casefile import ReconciliationRequest
from concord.orchestration.runner import ReconciliationRunner
from concord.providers import FabricIQProvider, FoundryIQProvider
from concord.providers.factory import create_preferred_cloud_provider
from pydantic import SecretStr


def test_agent_framework_wrapper_calls_local_reconciliation_tool(
    reconciliation_runner: ReconciliationRunner,
) -> None:
    calls: list[tuple[str, str, str]] = []

    def local_tool(term: str, period: str, provider: str):
        calls.append((term, period, provider))
        return reconciliation_runner.run(
            ReconciliationRequest(
                question=f"Why do our {term} definitions disagree?",
                term=term,
            )
        )

    workflow = ConcordAgentWorkflow(local_tool, default_provider="local")
    result = asyncio.run(
        workflow.run_result(
            ReconciliationRequest(
                question="Why do our Active Customer dashboards disagree?",
                term="Active Customer",
            )
        )
    )

    assert result.case.verdict == "conflict"
    assert calls == [("Active Customer", "2026-03-04/2026-06-01", "local")]
    assert result.agent_trace == tuple(agent.name for agent in SPECIALIST_AGENTS)


def test_default_agent_framework_mode_makes_no_cloud_calls(
    reconciliation_runner: ReconciliationRunner,
    monkeypatch,
) -> None:
    def unexpected_cloud_call(*args, **kwargs):
        raise AssertionError("default Agent Framework mode attempted a cloud IQ call")

    monkeypatch.setattr(FabricIQProvider, "_retrieve_snapshot", unexpected_cloud_call)
    monkeypatch.setattr(FoundryIQProvider, "_retrieve_snapshot", unexpected_cloud_call)

    case = asyncio.run(
        ConcordAgentWorkflow.from_runner(reconciliation_runner).run(
            ReconciliationRequest(
                question="Are Net Revenue definitions equivalent?",
                term="Net Revenue",
            )
        )
    )

    assert case.verdict == "consistent"
    assert reconciliation_runner.provider.name == "LocalProvider"


def test_strict_workflow_executes_specialist_stages_without_giant_runner_call(
    reconciliation_runner: ReconciliationRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = ReconciliationRequest(
        question="Why do our Active Customer dashboards disagree?",
        term="Active Customer",
    )
    fast_result = asyncio.run(
        ConcordAgentWorkflow.from_runner(reconciliation_runner, mode="fast").run_result(request)
    )

    def unexpected_runner_call(*args, **kwargs):
        raise AssertionError("strict workflow called the complete runner path")

    monkeypatch.setattr(ReconciliationRunner, "run", unexpected_runner_call)
    strict_result = asyncio.run(
        ConcordAgentWorkflow.from_runner(reconciliation_runner, mode="strict").run_result(request)
    )

    assert strict_result.workflow_mode == "strict"
    assert strict_result.workflow_plan == tuple(agent.name for agent in SPECIALIST_AGENTS)
    assert strict_result.agent_trace == strict_result.workflow_plan
    assert strict_result.case.verdict == fast_result.case.verdict == "conflict"
    assert [evaluation.entity_count for evaluation in strict_result.case.execution_results] == [
        evaluation.entity_count for evaluation in fast_result.case.execution_results
    ]
    assert strict_result.case.authority_assessment == fast_result.case.authority_assessment
    assert strict_result.case.reconciliation_proposal is not None
    assert fast_result.case.reconciliation_proposal is not None
    assert (
        strict_result.case.reconciliation_proposal.canonical_definition
        == fast_result.case.reconciliation_proposal.canonical_definition
    )
    assert tuple(entry.agent for entry in strict_result.case.audit_log) == (
        "ConceptResolverAgent",
        "BindingInspectorAgent",
        "ConflictHypothesisAgent",
        "DataExecutionAgent",
        "ImpactRankerAgent",
        "AuthorityResolverAgent",
        "ReconciliationAgent",
        "SkepticalVerifierAgent",
        "AuditAgent",
        "CoordinatorAgent",
    )


def test_fabric_iq_is_preferred_when_both_cloud_providers_are_configured() -> None:
    settings = Settings(
        _env_file=None,
        fabric_iq_mcp_endpoint="https://api.fabric.microsoft.com/v1/mcp/dataPlane/test",
        fabric_iq_access_token=SecretStr("fabric-placeholder"),
        foundry_iq_endpoint="https://example.search.windows.net",
        foundry_iq_knowledge_base="concord-iq",
        foundry_iq_access_token=SecretStr("foundry-placeholder"),
    )

    assert isinstance(create_preferred_cloud_provider(settings), FabricIQProvider)


def test_foundry_iq_is_fallback_when_fabric_iq_is_unavailable() -> None:
    settings = Settings(
        _env_file=None,
        foundry_iq_endpoint="https://example.search.windows.net",
        foundry_iq_knowledge_base="concord-iq",
        foundry_iq_access_token=SecretStr("foundry-placeholder"),
    )

    assert isinstance(create_preferred_cloud_provider(settings), FoundryIQProvider)


def test_foundry_hosted_entrypoint_fails_closed_by_default() -> None:
    with pytest.raises(CloudAccessDisabled, match="Foundry Agent Service is disabled"):
        build_hosted_agent(Settings(_env_file=None))
