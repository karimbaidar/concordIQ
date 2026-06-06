"""Foundry IQ provider boundary."""

from urllib.parse import quote

from concord.config import Settings
from concord.providers.base import ProviderMode, ProviderNotConfigured
from concord.providers.cloud import JsonTransport
from concord.providers.cloud_snapshot import CloudSnapshotProvider
from concord.providers.replay_schema import ReplayScenarioSnapshot, find_snapshot


class FoundryIQProvider(CloudSnapshotProvider):
    """Azure AI Search knowledge-base adapter used by Foundry IQ."""

    name = "FoundryIQProvider"
    mode = ProviderMode.FOUNDRY_IQ

    def __init__(self, settings: Settings, *, transport: JsonTransport | None = None) -> None:
        super().__init__(settings, transport=transport)

    def _retrieve_snapshot(self, term: str) -> ReplayScenarioSnapshot:
        endpoint = self.settings.foundry_iq_endpoint
        knowledge_base = self.settings.foundry_iq_knowledge_base
        if not endpoint or not knowledge_base:
            raise ProviderNotConfigured(
                "FoundryIQProvider requires FOUNDRY_IQ_ENDPOINT and FOUNDRY_IQ_KNOWLEDGE_BASE."
            )
        headers = {"Content-Type": "application/json"}
        if self.settings.foundry_iq_access_token:
            headers["Authorization"] = (
                f"Bearer {self.settings.foundry_iq_access_token.get_secret_value()}"
            )
        elif self.settings.foundry_iq_api_key:
            headers["api-key"] = self.settings.foundry_iq_api_key.get_secret_value()
        else:
            raise ProviderNotConfigured("FoundryIQProvider requires an access token or API key.")

        api_version = self.settings.foundry_iq_api_version
        url = (
            f"{endpoint.rstrip('/')}/knowledgebases/{quote(knowledge_base, safe='')}/retrieve"
            f"?api-version={quote(api_version, safe='')}"
        )
        search = (
            f"Return the complete Concord IQ synthetic scenario snapshot for {term!r}. "
            "The source document must contain scenario_id, term, concept, bindings, "
            "evaluations, subgraph, and authority_rules as JSON. Do not infer missing fields."
        )
        if api_version == "2026-04-01":
            body = {"intents": [{"type": "semantic", "search": search}]}
        else:
            body = {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": search}],
                    }
                ]
            }
        result = self.client.request("POST", url, headers=headers, body=body)
        return find_snapshot(result.payload)
