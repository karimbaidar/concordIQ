"""T2.2b — Foundry IQ advisory authority grounding.

Foundry IQ retrieval participates in a real, clearly-labelled advisory grounding step
during authority resolution, while the deterministic authority rule still decides. No
test makes a cloud call: the retrieval transport is injected.
"""

from typing import Any

from concord.agents.authority_resolver import AuthorityResolverAgent
from concord.config import Settings
from concord.demo import DEMO_SCENARIOS
from concord.orchestration.casefile import ReconciliationRequest
from concord.orchestration.runner import ReconciliationRunner
from concord.providers import LocalProvider
from concord.providers.base import AuthorityGrounding, AuthorityRule, ProviderMode
from concord.providers.cloud import HttpResult
from concord.providers.foundry_iq import FoundryIQProvider
from concord.providers.replay_schema import snapshot_provider_scenario


class QueueTransport:
    def __init__(self, responses: list[HttpResult]) -> None:
        self.responses = responses
        self.requests: list[dict[str, Any]] = []

    def request(self, method, url, *, headers, body) -> HttpResult:
        self.requests.append({"body": body})
        return self.responses.pop(0)


def _foundry_settings() -> Settings:
    return Settings(
        _env_file=None,
        provider="foundry_iq",
        allow_cloud=True,
        max_cloud_calls=6,
        foundry_iq_endpoint="https://search.example.net",
        foundry_iq_knowledge_base="concord",
        foundry_iq_access_token="super-secret-token",
    )


class _DivergentGroundingProvider:
    """LocalProvider authority rules, but a clue that names a *different* owner.

    Proves the advisory clue can never override the deterministic decision.
    """

    name = "RogueProvider"
    mode = ProviderMode.LOCAL
    uses_cloud = False

    def __init__(self, local: LocalProvider) -> None:
        self._local = local

    def get_authority_rules(self, concept_id: str) -> list[AuthorityRule]:
        return self._local.get_authority_rules(concept_id)

    def retrieve_authority_grounding(self, concept_id: str) -> AuthorityGrounding:
        return AuthorityGrounding(
            source="Rogue retrieval",
            retrieved_owner="Rogue Owner",
            citation="rogue:1",
            note="A retrieval that disagrees with the configured authority.",
        )


def test_foundry_iq_grounding_is_advisory_and_decision_stays_deterministic(
    p2_local_provider: LocalProvider,
) -> None:
    scenario = next(item for item in DEMO_SCENARIOS if item.term == "Active Customer")
    snapshot = snapshot_provider_scenario(p2_local_provider, scenario)
    transport = QueueTransport([HttpResult(payload=snapshot.model_dump(mode="json"), headers={})])
    provider = FoundryIQProvider(_foundry_settings(), transport=transport)
    provider.resolve_concept("Active Customer")  # one injected Foundry IQ retrieval

    assessment = AuthorityResolverAgent(provider).run("active_customer")

    # The deterministic authority rule decided.
    assert assessment.status == "clear"
    assert assessment.owner == "Data Governance Council"
    # Foundry IQ contributed a clearly-labelled advisory clue that corroborates it.
    grounding = assessment.advisory_grounding
    assert grounding is not None
    assert "FoundryIQProvider" in grounding.source
    assert grounding.retrieved_owner == "Data Governance Council"
    assert grounding.agrees_with_rule is True
    assert grounding.advisory_only is True


def test_advisory_clue_never_overrides_the_deterministic_owner(
    p2_local_provider: LocalProvider,
) -> None:
    provider = _DivergentGroundingProvider(p2_local_provider)

    assessment = AuthorityResolverAgent(provider).run("active_customer")

    # The deterministic owner wins; the rogue clue is recorded but flagged as NOT agreeing.
    assert assessment.owner == "Data Governance Council"
    assert assessment.status == "clear"
    assert assessment.advisory_grounding is not None
    assert assessment.advisory_grounding.retrieved_owner == "Rogue Owner"
    assert assessment.advisory_grounding.agrees_with_rule is False
    assert assessment.advisory_grounding.advisory_only is True


def test_local_run_surfaces_advisory_grounding(
    reconciliation_runner: ReconciliationRunner,
) -> None:
    case = reconciliation_runner.run(
        ReconciliationRequest(question="Why do our Active Customer dashboards disagree?")
    )

    grounding = case.authority_assessment.advisory_grounding
    assert grounding is not None
    assert grounding.source == "Deterministic local registry"
    assert grounding.retrieved_owner == "Data Governance Council"
    assert grounding.agrees_with_rule is True
    # The deterministic decision is unchanged.
    assert case.authority_assessment.owner == "Data Governance Council"
