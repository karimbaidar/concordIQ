"""Fabric IQ provider boundary."""

from typing import Any

from concord.config import Settings
from concord.providers.base import ProviderMode, ProviderNotConfigured
from concord.providers.cloud import JsonTransport
from concord.providers.cloud_snapshot import CloudSnapshotProvider
from concord.providers.replay_schema import ReplayScenarioSnapshot, find_snapshot


class FabricIQProvider(CloudSnapshotProvider):
    """Fabric IQ ontology MCP adapter with explicit session and tool discovery."""

    name = "FabricIQProvider"
    mode = ProviderMode.FABRIC_IQ

    def __init__(self, settings: Settings, *, transport: JsonTransport | None = None) -> None:
        super().__init__(settings, transport=transport)
        self._session_id: str | None = None
        self._tools: tuple[dict[str, Any], ...] = ()
        self._request_id = 0

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
            f"Find the Concord IQ synthetic scenario snapshot for {term!r}. "
            "Return the registered JSON with concept, bindings, evaluations, subgraph, "
            "and authority_rules. Do not infer missing fields."
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
        return find_snapshot(called)
