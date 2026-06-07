"""Fabric IQ provider boundary."""

from typing import TYPE_CHECKING, Any

from concord.config import Settings
from concord.providers.base import ProviderMode, ProviderNotConfigured
from concord.providers.cloud import JsonTransport
from concord.providers.cloud_snapshot import CloudSnapshotProvider
from concord.providers.replay_schema import (
    ReplayScenarioSnapshot,
    SnapshotNotFound,
    expected_entity_type,
    find_semantic_match,
    find_snapshot,
    response_shape,
    snapshot_provider_scenario,
)

if TYPE_CHECKING:
    from concord.providers.local import LocalProvider

SEMANTIC_PROOF_MODE = "fabric_semantic_proof_with_deterministic_snapshot"
SEMANTIC_SNAPSHOT_SOURCE = "LocalProvider synthetic snapshot"


class FabricIQProvider(CloudSnapshotProvider):
    """Fabric IQ ontology MCP adapter with explicit session and tool discovery.

    Two honest capture modes:

    * **Full snapshot** — if the MCP returns a complete Concord IQ scenario
      snapshot, it is used exactly as captured.
    * **Semantic proof** — if the MCP only returns matching ontology entity types
      (the common preview behavior), Fabric IQ is recorded as the semantic
      grounding proof and the deterministic LocalProvider snapshot for the same
      term supplies the SQL/evidence. Connectivity-only responses with no matching
      concept are rejected.
    """

    name = "FabricIQProvider"
    mode = ProviderMode.FABRIC_IQ

    def __init__(
        self,
        settings: Settings,
        *,
        transport: JsonTransport | None = None,
        local_provider: "LocalProvider | None" = None,
    ) -> None:
        super().__init__(settings, transport=transport)
        self._session_id: str | None = None
        self._tools: tuple[dict[str, Any], ...] = ()
        self._request_id = 0
        self._local_provider = local_provider
        self._semantic_proofs: dict[str, dict[str, str]] = {}

    @property
    def fabric_tool_names(self) -> tuple[str, ...]:
        return tuple(str(tool.get("name", "")) for tool in self._tools)

    @property
    def semantic_proofs(self) -> dict[str, dict[str, str]]:
        return dict(self._semantic_proofs)

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _headers(self) -> dict[str, str]:
        if not self.settings.fabric_iq_access_token:
            raise ProviderNotConfigured("FabricIQProvider requires FABRIC_IQ_ACCESS_TOKEN.")
        headers = {
            "Authorization": (f"Bearer {self.settings.fabric_iq_access_token.get_secret_value()}"),
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        return headers

    def _mcp(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        endpoint = self.settings.fabric_iq_mcp_endpoint
        if not endpoint:
            raise ProviderNotConfigured("FabricIQProvider requires FABRIC_IQ_MCP_ENDPOINT.")
        body: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
        }
        if params is not None:
            body["params"] = params
        result = self.client.request("POST", endpoint, headers=self._headers(), body=body)
        self._session_id = result.headers.get("mcp-session-id", self._session_id)
        if "error" in result.payload:
            raise ProviderNotConfigured(f"Fabric ontology MCP error: {result.payload['error']}")
        return result.payload

    def _notify_initialized(self) -> None:
        endpoint = self.settings.fabric_iq_mcp_endpoint
        if not endpoint:
            raise ProviderNotConfigured("FabricIQProvider requires FABRIC_IQ_MCP_ENDPOINT.")
        self.client.request(
            "POST",
            endpoint,
            headers=self._headers(),
            body={"jsonrpc": "2.0", "method": "notifications/initialized"},
        )

    def _ensure_tools(self) -> None:
        if self._tools:
            return
        initialized = self._mcp(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "concord-iq", "version": "0.1.0"},
            },
        )
        if not initialized.get("result"):
            raise ProviderNotConfigured("Fabric ontology MCP initialization failed.")
        self._notify_initialized()
        listed = self._mcp("tools/list")
        self._tools = tuple(listed.get("result", {}).get("tools", ()))
        if not self._tools:
            raise ProviderNotConfigured("Fabric ontology MCP returned no tools.")

    def _retrieve_snapshot(self, term: str) -> ReplayScenarioSnapshot:
        self._ensure_tools()
        tool = next(
            (
                item
                for name in ("search_ontology", "query_ontology")
                for item in self._tools
                if item.get("name") == name
            ),
            None,
        )
        if tool is None:
            raise ProviderNotConfigured(
                "Fabric ontology MCP exposes neither search_ontology nor query_ontology."
            )
        prompt = (
            f"Retrieve the Concord IQ scenario snapshot for {term!r} from the "
            "`concord_iq_scenarios` content in this workspace. Return the stored JSON "
            "verbatim, including scenario_id, term, data_classification, concept, "
            "bindings, evaluations, subgraph, and authority_rules. Do not summarize, "
            "reformat, or infer missing fields; return the exact JSON object."
        )
        schema = tool.get("inputSchema", {})
        properties = schema.get("properties", {})
        argument_name = next(
            (name for name in ("query", "search", "text", "term") if name in properties),
            next(iter(properties), "query"),
        )
        called = self._mcp(
            "tools/call",
            {
                "name": tool["name"],
                "arguments": {argument_name: prompt},
            },
        )
        # Mode 1: Fabric returned a full Concord IQ scenario snapshot.
        try:
            return find_snapshot(called)
        except SnapshotNotFound:
            pass
        # Mode 2: Fabric returned matching ontology content but no full snapshot.
        expected = expected_entity_type(term)
        if not find_semantic_match(called, expected):
            raise ProviderNotConfigured(
                f"Fabric IQ returned neither a full snapshot nor a matching concept for "
                f"{term!r} (expected entity type {expected!r}). Connectivity-only responses "
                "are rejected — run `make fabric-mcp-diagnose` to inspect the live response."
            )
        snapshot = self._materialize_local_snapshot(term)
        self._semantic_proofs[term] = {
            "matched_entity_type": expected,
            "response_shape": response_shape(called),
        }
        return snapshot

    def _materialize_local_snapshot(self, term: str) -> ReplayScenarioSnapshot:
        """Build the deterministic LocalProvider snapshot for a proven term."""
        from concord.demo import DEMO_SCENARIOS
        from concord.providers.local import LocalProvider

        scenario = next((item for item in DEMO_SCENARIOS if item.term == term), None)
        if scenario is None:
            raise ProviderNotConfigured(
                f"No deterministic synthetic scenario is registered for {term!r}."
            )
        provider = self._local_provider or LocalProvider()
        return snapshot_provider_scenario(provider, scenario)
