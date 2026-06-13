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

    def _find_tool(self, names: tuple[str, ...]) -> dict[str, Any] | None:
        return next(
            (item for name in names for item in self._tools if item.get("name") == name),
            None,
        )

    def _call_tool(self, tool: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        properties = tool.get("inputSchema", {}).get("properties", {})
        accepted = {key: value for key, value in arguments.items() if key in properties}
        return self._mcp(
            "tools/call",
            {"name": tool["name"], "arguments": accepted or arguments},
        )

    @staticmethod
    def _tool_arguments(tool: dict[str, Any], term: str, expected: str) -> dict[str, Any]:
        if tool.get("name") == "list_ontology_entity_types":
            # Ask the schema tool for the governed entity type by exact name.
            return {"entityName": expected, "includeProperties": True}
        properties = tool.get("inputSchema", {}).get("properties", {})
        query_arg = next(
            (
                name
                for name in ("naturalLanguageQuery", "query", "search", "text", "term")
                if name in properties
            ),
            next(iter(properties), "naturalLanguageQuery"),
        )
        return {query_arg: f"Describe the {expected} entity type and its properties."}

    def _record_semantic_proof(
        self,
        term: str,
        expected: str,
        tool_name: str,
        response: dict[str, Any],
    ) -> ReplayScenarioSnapshot:
        snapshot = self._materialize_local_snapshot(term)
        self._semantic_proofs[term] = {
            "matched_entity_type": expected,
            "tool": tool_name,
            "response_shape": response_shape(response),
        }
        return snapshot

    def _retrieve_snapshot(self, term: str) -> ReplayScenarioSnapshot:
        self._ensure_tools()
        expected = expected_entity_type(term)
        # Prefer list_ontology_entity_types: it returns the governed entity types
        # (the semantic proof). search_ontology queries instance data, which is
        # empty for an unbound ontology and yields no proof. One call per scenario
        # keeps capture within the six-call budget.
        tool = self._find_tool(("list_ontology_entity_types", "search_ontology", "query_ontology"))
        if tool is None:
            raise ProviderNotConfigured(
                "Fabric ontology MCP exposes no usable ontology tool "
                "(expected list_ontology_entity_types or search_ontology)."
            )
        called = self._call_tool(tool, self._tool_arguments(tool, term, expected))
        # Mode 1: a full Concord IQ scenario snapshot was returned.
        try:
            return find_snapshot(called)
        except SnapshotNotFound:
            pass
        # Mode 2: the governed entity type was matched (semantic grounding proof).
        if find_semantic_match(called, expected):
            return self._record_semantic_proof(term, expected, str(tool["name"]), called)
        raise ProviderNotConfigured(
            f"Fabric IQ returned no full snapshot and did not match the {expected!r} entity "
            f"type for {term!r}. Connectivity-only responses are rejected — run "
            "`make fabric-mcp-diagnose` to inspect the live response."
        )

    def _materialize_local_snapshot(self, term: str) -> ReplayScenarioSnapshot:
        """Build the deterministic LocalProvider snapshot for a proven term."""
        from concord.demo import demo_scenarios_for_pack
        from concord.providers.local import LocalProvider

        scenario_pack = (
            self._local_provider.scenario_pack
            if self._local_provider is not None
            else self.settings.scenario_pack
        )
        scenarios = demo_scenarios_for_pack(scenario_pack)
        scenario = next((item for item in scenarios if item.term == term), None)
        if scenario is None:
            raise ProviderNotConfigured(
                f"No deterministic synthetic scenario is registered for {term!r}."
            )
        provider = self._local_provider or LocalProvider.for_scenario_pack(
            scenario_pack,
            duckdb_path=self.settings.duckdb_path,
        )
        return snapshot_provider_scenario(provider, scenario)
