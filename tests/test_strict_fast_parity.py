"""P6 acceptance: strict workflow matches fast workflow across all scenarios.

The strict Agent Framework workflow drives each specialist stage individually,
while fast mode exposes the deterministic runner's trace. Both must reach an
identical verdict and decision for every scenario, including the Net Revenue
decoy, the Churned Customer refusal, and the subtle Qualified Lead conflict.
"""

import asyncio

import pytest
from concord.config import Settings
from concord.ms_agent.agents import SPECIALIST_AGENTS
from concord.ms_agent.workflow import ConcordAgentWorkflow
from concord.orchestration.casefile import ReconciliationCase, ReconciliationRequest
from concord.orchestration.runner import ReconciliationRunner

# term, expected verdict, expected decision shape: propose | refuse | none
SCENARIOS = [
    ("Active Customer", "conflict", "propose"),
    ("Net Revenue", "consistent", "none"),
    ("Churned Customer", "conflict", "refuse"),
    ("Qualified Lead", "conflict", "propose"),
]


def _run(runner: ReconciliationRunner, term: str, mode: str):
    request = ReconciliationRequest(
        question=f"Why do our {term} definitions disagree?",
        term=term,
    )
    return asyncio.run(ConcordAgentWorkflow.from_runner(runner, mode=mode).run_result(request))


def _assert_decision_shape(case: ReconciliationCase, decision: str) -> None:
    if decision == "propose":
        assert case.reconciliation_proposal is not None
        assert case.refusal_reason is None
    elif decision == "refuse":
        assert case.reconciliation_proposal is None
        assert case.refusal_reason
        assert "human approval is required" in case.refusal_reason.lower()
    else:
        assert case.reconciliation_proposal is None
        assert case.refusal_reason is None
        assert case.requires_human_approval is False


@pytest.mark.parametrize(("term", "verdict", "decision"), SCENARIOS)
def test_strict_matches_fast_for_each_scenario(
    reconciliation_runner: ReconciliationRunner,
    term: str,
    verdict: str,
    decision: str,
) -> None:
    fast = _run(reconciliation_runner, term, "fast")
    strict = _run(reconciliation_runner, term, "strict")

    # Strict mode genuinely drives the specialist stages.
    assert strict.workflow_mode == "strict"
    assert strict.workflow_plan == tuple(agent.name for agent in SPECIALIST_AGENTS)
    assert strict.agent_trace == strict.workflow_plan

    # Same verdict and decision in both modes.
    assert strict.case.verdict == fast.case.verdict == verdict
    _assert_decision_shape(fast.case, decision)
    _assert_decision_shape(strict.case, decision)

    # Same executed populations (the deterministic truth path is mode-independent).
    fast_counts = [e.entity_count for e in fast.case.execution_results]
    strict_counts = [e.entity_count for e in strict.case.execution_results]
    assert strict_counts == fast_counts
    assert strict.case.authority_assessment == fast.case.authority_assessment
    assert strict.case.verification_status == fast.case.verification_status == "passed"


def test_strict_catches_qualified_lead_subtle_gap(
    reconciliation_runner: ReconciliationRunner,
) -> None:
    strict = _run(reconciliation_runner, "Qualified Lead", "strict")

    assert strict.case.verdict == "conflict"
    assert [e.entity_count for e in strict.case.execution_results] == [1500, 1520]
    assert strict.case.impact_assessment
    assert strict.case.impact_assessment.customer_count_delta == 20
    assert strict.case.reconciliation_proposal is not None


def test_foundry_and_fabric_config_not_required_for_local_mode(
    reconciliation_runner: ReconciliationRunner,
) -> None:
    # Default settings carry no cloud configuration.
    settings = Settings(_env_file=None)
    assert settings.foundry_iq_endpoint is None
    assert settings.foundry_iq_knowledge_base is None
    assert settings.fabric_iq_mcp_endpoint is None
    assert settings.fabric_iq_access_token is None

    # Yet a local strict workflow run completes and verifies without any of them.
    strict = _run(reconciliation_runner, "Active Customer", "strict")
    assert strict.case.verdict == "conflict"
    assert strict.case.verification_status == "passed"
    assert reconciliation_runner.provider.name == "LocalProvider"


def test_env_example_documents_foundry_variables_without_enabling_cloud() -> None:
    from pathlib import Path

    text = (Path(__file__).resolve().parents[1] / ".env.example").read_text(encoding="utf-8")
    for key in (
        "FOUNDRY_IQ_ENDPOINT",
        "FOUNDRY_IQ_KNOWLEDGE_BASE",
        "FOUNDRY_PROJECT_ENDPOINT",
        "AZURE_AI_MODEL_DEPLOYMENT_NAME",
    ):
        assert key in text
    # Documented but cloud stays disabled by default.
    assert "ALLOW_CLOUD=false" in text
    assert "PROVIDER=local" in text
