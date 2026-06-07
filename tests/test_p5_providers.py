"""P5 provider, replay, capture, and cloud-safety acceptance tests."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from concord.api.main import create_app
from concord.capture import capture
from concord.config import CloudAccessDisabled, Settings
from concord.demo import DEMO_SCENARIOS
from concord.providers import (
    FabricIQProvider,
    FoundryIQProvider,
    LocalProvider,
    ReplayProvider,
)
from concord.providers.base import ProviderMode
from concord.providers.cloud import (
    CloudCallBudgetExceeded,
    HttpResult,
)
from concord.providers.replay_schema import (
    ReplayScenarioSnapshot,
    build_replay_artifact,
    snapshot_provider_scenario,
)
from fastapi.testclient import TestClient
from sqlalchemy import Engine


class QueueTransport:
    """Deterministic transport that records requests and returns queued responses."""

    def __init__(self, responses: list[HttpResult]) -> None:
        self.responses = responses
        self.requests: list[dict[str, Any]] = []

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any],
    ) -> HttpResult:
        self.requests.append({"method": method, "url": url, "headers": headers, "body": body})
        return self.responses.pop(0)


def _snapshots(provider: LocalProvider) -> tuple[ReplayScenarioSnapshot, ...]:
    return tuple(snapshot_provider_scenario(provider, scenario) for scenario in DEMO_SCENARIOS)


def _write_test_artifact(
    path: Path,
    provider: LocalProvider,
    *,
    verified: bool = True,
) -> None:
    artifact = build_replay_artifact(
        provider_name="FoundryIQProvider",
        provider_mode=ProviderMode.FOUNDRY_IQ,
        scenarios=_snapshots(provider),
        verified_real_iq=verified,
        captured_at=datetime(2026, 6, 6, tzinfo=UTC),
        api_version="test",
    )
    artifact.write(path)


def test_provider_contract_local_and_replay_match(
    tmp_path: Path,
    p2_local_provider: LocalProvider,
) -> None:
    artifact_path = tmp_path / "replay.json"
    _write_test_artifact(artifact_path, p2_local_provider)
    replay = ReplayProvider(artifact_path)

    for scenario in DEMO_SCENARIOS:
        period = scenario.request().period
        local_concept = p2_local_provider.resolve_concept(scenario.term)
        replay_concept = replay.resolve_concept(scenario.term)
        assert replay_concept == local_concept

        local_bindings = p2_local_provider.get_binding_semantics(local_concept.concept_id)
        replay_bindings = replay.get_binding_semantics(replay_concept.concept_id)
        assert replay_bindings == local_bindings
        assert [
            replay.evaluate_definition(binding.binding_id, period) for binding in replay_bindings
        ] == [
            p2_local_provider.evaluate_definition(binding.binding_id, period)
            for binding in local_bindings
        ]
        assert replay.get_subgraph(replay_concept.concept_id) == (
            p2_local_provider.get_subgraph(local_concept.concept_id)
        )
        assert replay.get_authority_rules(replay_concept.concept_id) == (
            p2_local_provider.get_authority_rules(local_concept.concept_id)
        )

        question = f"Why do our {scenario.term} numbers disagree?"
        local_query = p2_local_provider.nl_query(question)
        replay_query = replay.nl_query(question)
        assert local_query.matched and replay_query.matched
        assert replay_query.concept_id == local_query.concept_id
        assert replay_query.citations == local_query.citations
        assert replay_query.answer == local_query.answer


def test_replay_refuses_unverified_artifact(
    tmp_path: Path,
    p2_local_provider: LocalProvider,
) -> None:
    artifact_path = tmp_path / "unverified.json"
    _write_test_artifact(artifact_path, p2_local_provider, verified=False)

    with pytest.raises(RuntimeError, match="not marked as a verified"):
        ReplayProvider(artifact_path)


def test_foundry_cloud_guard_blocks_before_transport() -> None:
    transport = QueueTransport([])
    provider = FoundryIQProvider(
        Settings(
            allow_cloud=False,
            max_cloud_calls=0,
            foundry_iq_endpoint="https://example.search.windows.net",
            foundry_iq_knowledge_base="concord",
            foundry_iq_access_token="secret",
        ),
        transport=transport,
    )

    with pytest.raises(CloudAccessDisabled):
        provider.resolve_concept("Active Customer")

    assert transport.requests == []


def test_foundry_retrieval_parses_and_caches_typed_snapshot(
    p2_local_provider: LocalProvider,
) -> None:
    snapshot = _snapshots(p2_local_provider)[0]
    transport = QueueTransport(
        [
            HttpResult(
                payload={
                    "response": [
                        {
                            "content": [
                                {
                                    "type": "text",
                                    "text": snapshot.model_dump_json(),
                                }
                            ]
                        }
                    ]
                },
                headers={},
            )
        ]
    )
    provider = FoundryIQProvider(
        Settings(
            allow_cloud=True,
            max_cloud_calls=1,
            foundry_iq_endpoint="https://example.search.windows.net",
            foundry_iq_knowledge_base="concord",
            foundry_iq_access_token="secret",
        ),
        transport=transport,
    )

    concept = provider.resolve_concept("Active Customer")
    assert concept == snapshot.concept
    assert provider.get_binding_semantics(concept.concept_id) == list(snapshot.bindings)
    assert provider.cloud_call_count == 1
    assert len(transport.requests) == 1
    assert "api-version=2026-04-01" in transport.requests[0]["url"]
    assert "intents" in transport.requests[0]["body"]

    with pytest.raises(CloudCallBudgetExceeded):
        provider.resolve_concept("Unknown Cloud Concept")


def test_fabric_mcp_discovers_tool_and_parses_typed_snapshot(
    p2_local_provider: LocalProvider,
) -> None:
    snapshot = _snapshots(p2_local_provider)[0]
    transport = QueueTransport(
        [
            HttpResult(
                payload={"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2025-06-18"}},
                headers={"mcp-session-id": "session-123"},
            ),
            HttpResult(payload={}, headers={}),
            HttpResult(
                payload={
                    "jsonrpc": "2.0",
                    "id": 3,
                    "result": {
                        "tools": [
                            {
                                "name": "search_ontology",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {"query": {"type": "string"}},
                                },
                            }
                        ]
                    },
                },
                headers={},
            ),
            HttpResult(
                payload={
                    "jsonrpc": "2.0",
                    "id": 4,
                    "result": {"content": [{"type": "text", "text": snapshot.model_dump_json()}]},
                },
                headers={},
            ),
        ]
    )
    provider = FabricIQProvider(
        Settings(
            allow_cloud=True,
            max_cloud_calls=4,
            fabric_iq_mcp_endpoint=(
                "https://api.fabric.microsoft.com/v1/mcp/dataPlane/"
                "workspaces/workspace/items/ontology/ontologyEndpoint"
            ),
            fabric_iq_access_token="secret",
        ),
        transport=transport,
    )

    assert provider.resolve_concept("Active Customer") == snapshot.concept
    assert provider.cloud_call_count == 4
    assert transport.requests[1]["headers"]["Mcp-Session-Id"] == "session-123"
    assert transport.requests[1]["body"]["method"] == "notifications/initialized"
    assert transport.requests[3]["body"]["params"]["name"] == "search_ontology"


def test_fabric_capture_stays_within_six_call_budget(
    tmp_path: Path,
    p2_local_provider: LocalProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lock the F2 budget: a full Fabric capture is exactly six MCP calls.

    One handshake (initialize + initialized + tools/list) plus one tool call per
    scenario = 6. MAX_CLOUD_CALLS=6 must be sufficient and not exceeded.
    """
    snapshots = _snapshots(p2_local_provider)
    transport = QueueTransport(
        [
            HttpResult(
                payload={"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2025-06-18"}},
                headers={"mcp-session-id": "session-123"},
            ),
            HttpResult(payload={}, headers={}),
            HttpResult(
                payload={
                    "jsonrpc": "2.0",
                    "id": 3,
                    "result": {
                        "tools": [
                            {
                                "name": "search_ontology",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {"query": {"type": "string"}},
                                },
                            }
                        ]
                    },
                },
                headers={},
            ),
            *(
                HttpResult(
                    payload={
                        "jsonrpc": "2.0",
                        "id": index + 4,
                        "result": {
                            "content": [{"type": "text", "text": snapshot.model_dump_json()}]
                        },
                    },
                    headers={},
                )
                for index, snapshot in enumerate(snapshots)
            ),
        ]
    )
    settings = Settings(
        provider="fabric_iq",
        allow_cloud=True,
        max_cloud_calls=6,
        fabric_iq_mcp_endpoint=(
            "https://api.fabric.microsoft.com/v1/mcp/dataPlane/"
            "workspaces/workspace/items/ontology/ontologyEndpoint"
        ),
        fabric_iq_access_token="secret",
        capture_raw_dir=tmp_path / "raw",
        capture_sanitized_path=tmp_path / "sanitized" / "latest.json",
    )
    provider = FabricIQProvider(settings, transport=transport)
    monkeypatch.setattr("concord.capture.create_provider", lambda _: provider)

    sanitized_path = capture(settings)

    assert provider.cloud_call_count == 6
    replay = ReplayProvider(sanitized_path)
    assert {scenario.scenario_id for scenario in replay.artifact.scenarios} == {
        "active-customer",
        "net-revenue",
        "churned-customer",
    }


def test_capture_writes_raw_ignored_shape_and_sanitized_replay(
    tmp_path: Path,
    p2_local_provider: LocalProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshots = _snapshots(p2_local_provider)
    tenant_value = "https://tenant.example/123e4567-e89b-42d3-a456-426614174000 owner@example.com"
    transport = QueueTransport(
        [
            HttpResult(
                payload={"tenant": tenant_value, "snapshot": snapshot.model_dump(mode="json")},
                headers={},
            )
            for snapshot in snapshots
        ]
    )
    settings = Settings(
        provider="foundry_iq",
        allow_cloud=True,
        max_cloud_calls=3,
        foundry_iq_endpoint="https://example.search.windows.net",
        foundry_iq_knowledge_base="concord",
        foundry_iq_access_token="secret",
        capture_raw_dir=tmp_path / "raw",
        capture_sanitized_path=tmp_path / "sanitized" / "latest.json",
    )
    provider = FoundryIQProvider(settings, transport=transport)
    monkeypatch.setattr("concord.capture.create_provider", lambda _: provider)

    sanitized_path = capture(settings)

    raw_path = next((tmp_path / "raw").glob("*.json"))
    assert tenant_value in raw_path.read_text(encoding="utf-8")
    sanitized_text = sanitized_path.read_text(encoding="utf-8")
    assert "tenant.example" not in sanitized_text
    assert "owner@example.com" not in sanitized_text
    replay = ReplayProvider(sanitized_path)
    assert replay.resolve_concept("Active Customer") == snapshots[0].concept


def test_provider_status_endpoint_never_calls_cloud(
    postgres_engine: Engine,
    p2_local_provider: LocalProvider,
) -> None:
    app = create_app(
        Settings(),
        provider=p2_local_provider,
        engine=postgres_engine,
    )

    with TestClient(app) as client:
        response = client.get("/providers")

    assert response.status_code == 200
    statuses = {item["mode"]: item for item in response.json()}
    assert statuses["local"]["configured"] is True
    assert statuses["replay"]["configured"] is False
    assert statuses["foundry_iq"]["configured"] is False
    assert statuses["fabric_iq"]["configured"] is False


def test_product_docs_exist() -> None:
    expected = {
        "architecture.md",
        "cost-controls.md",
        "definition-of-done.md",
        "demo-script.md",
        "hackathon-submission.md",
        "iq-integration.md",
        "threat-model.md",
    }
    docs_dir = Path(__file__).resolve().parents[1] / "docs"
    assert expected <= {path.name for path in docs_dir.glob("*.md")}
