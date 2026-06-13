"""Fabric IQ two-mode capture tests (full snapshot vs honest semantic proof).

No test makes a cloud call: the MCP transport is injected and LocalProvider
supplies the deterministic snapshot.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from concord.capture import capture
from concord.config import Settings
from concord.demo import DEMO_SCENARIOS
from concord.fabric_mcp_diagnose import diagnose
from concord.providers import FabricIQProvider, LocalProvider
from concord.providers.base import ProviderMode, ProviderNotConfigured
from concord.providers.cloud import HttpResult
from concord.providers.fabric_iq import SEMANTIC_PROOF_MODE
from concord.providers.replay_schema import (
    ReplayScenarioSnapshot,
    build_replay_artifact,
    snapshot_provider_scenario,
)
from concord.replay_check import ReplayCheckError, validate_replay_artifact

EXPECTED_ENTITY = {
    "Active Customer": "ActiveCustomer",
    "Net Revenue": "NetRevenue",
    "Churned Customer": "ChurnedCustomer",
}


class QueueTransport:
    def __init__(self, responses: list[HttpResult]) -> None:
        self.responses = responses
        self.requests: list[dict[str, Any]] = []

    def request(self, method, url, *, headers, body) -> HttpResult:
        self.requests.append({"method": method, "body": body})
        return self.responses.pop(0)


def _handshake() -> list[HttpResult]:
    return [
        HttpResult(payload={"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}, headers={}),
        HttpResult(payload={}, headers={}),
        HttpResult(
            payload={
                "result": {
                    "tools": [
                        {"name": "list_ontology_entity_types", "inputSchema": {}},
                        {"name": "search_ontology", "inputSchema": {"properties": {"query": {}}}},
                    ]
                }
            },
            headers={},
        ),
    ]


def _semantic_text(entity: str) -> HttpResult:
    text = (
        f"Found ontology entity type {entity} with properties DisplayName, Description, ScenarioId."
    )
    return HttpResult(payload={"result": {"content": [{"type": "text", "text": text}]}}, headers={})


def _fabric_settings(tmp_path: Path, *, max_calls: int = 6) -> Settings:
    return Settings(
        _env_file=None,
        provider="fabric_iq",
        allow_cloud=True,
        max_cloud_calls=max_calls,
        fabric_iq_mcp_endpoint="https://api.fabric.microsoft.com/v1/mcp/dataPlane/test",
        fabric_iq_access_token="super-secret-token",
        capture_raw_dir=tmp_path / "raw",
        capture_sanitized_path=tmp_path / "sanitized" / "latest.json",
    )


def _snapshots(provider: LocalProvider) -> tuple[ReplayScenarioSnapshot, ...]:
    return tuple(snapshot_provider_scenario(provider, scenario) for scenario in DEMO_SCENARIOS)


# ---- provider modes ----


def test_full_snapshot_mode_uses_returned_snapshot(
    tmp_path: Path, p2_local_provider: LocalProvider
) -> None:
    snapshot = _snapshots(p2_local_provider)[0]
    transport = QueueTransport(
        _handshake()
        + [
            HttpResult(
                payload={
                    "result": {"content": [{"type": "text", "text": snapshot.model_dump_json()}]}
                },
                headers={},
            )
        ]
    )
    provider = FabricIQProvider(_fabric_settings(tmp_path), transport=transport)

    assert provider.resolve_concept("Active Customer") == snapshot.concept
    assert provider.semantic_proofs == {}  # full snapshot, not proof


def test_semantic_proof_mode_matches_concept_and_uses_local_snapshot(
    tmp_path: Path, p2_local_provider: LocalProvider
) -> None:
    transport = QueueTransport(_handshake() + [_semantic_text("ActiveCustomer")])
    provider = FabricIQProvider(
        _fabric_settings(tmp_path), transport=transport, local_provider=p2_local_provider
    )

    concept = provider.resolve_concept("Active Customer")
    assert concept.concept_id == "active_customer"
    assert provider.semantic_proofs["Active Customer"]["matched_entity_type"] == "ActiveCustomer"
    assert "search_ontology" in provider.fabric_tool_names
    # The deterministic local evidence is present for replay.
    bindings = provider.get_binding_semantics(concept.concept_id)
    assert {b.owner for b in bindings} == {"Finance", "Sales", "Customer Success"}


def test_provider_calls_list_entity_types_with_exact_name(
    tmp_path: Path, p2_local_provider: LocalProvider
) -> None:
    transport = QueueTransport(_handshake() + [_semantic_text("ActiveCustomer")])
    provider = FabricIQProvider(
        _fabric_settings(tmp_path), transport=transport, local_provider=p2_local_provider
    )

    provider.resolve_concept("Active Customer")

    tool_call = transport.requests[3]["body"]["params"]
    assert tool_call["name"] == "list_ontology_entity_types"
    assert tool_call["arguments"] == {"entityName": "ActiveCustomer", "includeProperties": True}
    assert provider.semantic_proofs["Active Customer"]["tool"] == "list_ontology_entity_types"


def test_connectivity_only_response_is_rejected(
    tmp_path: Path, p2_local_provider: LocalProvider
) -> None:
    transport = QueueTransport(
        _handshake()
        + [
            HttpResult(
                payload={"result": {"content": [{"type": "text", "text": "No results."}]}},
                headers={},
            )
        ]
    )
    provider = FabricIQProvider(
        _fabric_settings(tmp_path), transport=transport, local_provider=p2_local_provider
    )
    with pytest.raises(ProviderNotConfigured, match="did not match"):
        provider.resolve_concept("Active Customer")


# ---- diagnose three states ----


@pytest.mark.parametrize(
    ("last_response", "expected_state"),
    [
        ("snapshot", "full_snapshot"),
        ("semantic", "semantic_proof"),
        ("none", "none"),
    ],
)
def test_diagnose_distinguishes_three_states(
    tmp_path: Path,
    p2_local_provider: LocalProvider,
    last_response: str,
    expected_state: str,
) -> None:
    snapshot = _snapshots(p2_local_provider)[0]
    if last_response == "snapshot":
        last = HttpResult(
            payload={"result": {"content": [{"type": "text", "text": snapshot.model_dump_json()}]}},
            headers={},
        )
    elif last_response == "semantic":
        last = _semantic_text("ActiveCustomer")
    else:
        last = HttpResult(
            payload={"result": {"content": [{"type": "text", "text": "nope"}]}}, headers={}
        )
    provider = FabricIQProvider(
        _fabric_settings(tmp_path),
        transport=QueueTransport(_handshake() + [last]),
        local_provider=p2_local_provider,
    )

    report = diagnose(_fabric_settings(tmp_path), term="Active Customer", provider=provider)
    assert report["state"] == expected_state
    assert not (tmp_path / "sanitized" / "latest.json").exists()


# ---- capture end to end (mocked MCP) ----


def test_capture_builds_semantic_proof_artifact(
    tmp_path: Path, p2_local_provider: LocalProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    responses = _handshake() + [_semantic_text(EXPECTED_ENTITY[s.term]) for s in DEMO_SCENARIOS]
    provider = FabricIQProvider(
        _fabric_settings(tmp_path),
        transport=QueueTransport(responses),
        local_provider=p2_local_provider,
    )
    monkeypatch.setattr("concord.capture.create_provider", lambda _: provider)

    sanitized_path = capture(_fabric_settings(tmp_path))

    text = sanitized_path.read_text(encoding="utf-8")
    assert "super-secret-token" not in text
    artifact = validate_replay_artifact(sanitized_path)  # also proves replay_check accepts it
    assert artifact.capture.iq_proof_mode == SEMANTIC_PROOF_MODE
    assert artifact.capture.snapshot_source == "LocalProvider synthetic snapshot"
    assert artifact.capture.fabric_matched_concepts == EXPECTED_ENTITY
    assert set(artifact.capture.semantic_proof_terms) == set(EXPECTED_ENTITY)
    assert "search_ontology" in artifact.capture.fabric_tools_used


# ---- replay_check acceptance / rejection ----


def _semantic_artifact(provider: LocalProvider, **overrides: Any):
    matched = overrides.pop("matched", dict(EXPECTED_ENTITY))
    return build_replay_artifact(
        provider_name="FabricIQProvider",
        provider_mode=ProviderMode.FABRIC_IQ,
        scenarios=_snapshots(provider),
        verified_real_iq=True,
        captured_at=datetime(2026, 6, 7, tzinfo=UTC),
        api_version="MCP 2025-06-18",
        iq_proof_mode=SEMANTIC_PROOF_MODE,
        snapshot_source="LocalProvider synthetic snapshot",
        fabric_tools_used=("list_ontology_entity_types", "search_ontology"),
        fabric_matched_concepts=matched,
        semantic_proof_terms=tuple(matched),
        **overrides,
    )


def test_replay_check_accepts_valid_semantic_proof(
    tmp_path: Path, p2_local_provider: LocalProvider
) -> None:
    path = tmp_path / "proof.json"
    _semantic_artifact(p2_local_provider).write(path)
    artifact = validate_replay_artifact(path)
    assert artifact.capture.verified_real_iq is True


def test_replay_check_rejects_fake_semantic_proof(
    tmp_path: Path, p2_local_provider: LocalProvider
) -> None:
    path = tmp_path / "fake.json"
    _semantic_artifact(p2_local_provider, matched={"Active Customer": "WrongType"}).write(path)
    with pytest.raises(ReplayCheckError, match="did not prove"):
        validate_replay_artifact(path)


def test_replay_check_rejects_semantic_proof_with_secret(
    tmp_path: Path, p2_local_provider: LocalProvider
) -> None:
    path = tmp_path / "leaky.json"
    _semantic_artifact(p2_local_provider).write(path)
    leaked = path.read_text(encoding="utf-8").replace(
        '"snapshot_source"', '"Authorization": "Bearer x", "snapshot_source"'
    )
    path.write_text(leaked, encoding="utf-8")
    with pytest.raises(ReplayCheckError, match="forbidden secret-shaped"):
        validate_replay_artifact(path)


def test_fabric_falls_back_to_local_for_a_concept_not_in_the_ontology(tmp_path: Path) -> None:
    """A supporting scenario the live ontology does not register degrades to local grounding.

    The ontology is reachable (it lists the hero CertificationReady entity), but Exam Eligible
    is not a Fabric entity type, so it uses the deterministic LocalProvider snapshot — and no
    Fabric semantic proof is recorded for it. A connectivity-only response is still rejected.
    """
    from concord.config import ScenarioPack
    from concord.seed.seed_duckdb import seed_duckdb

    database_path = tmp_path / "concord-iq.duckdb"
    seed_duckdb(database_path=database_path, data_dir=tmp_path / "csv")
    local = LocalProvider.for_scenario_pack(ScenarioPack.LEARNING, duckdb_path=database_path)
    settings = Settings(
        _env_file=None,
        provider="fabric_iq",
        scenario_pack="learning",
        allow_cloud=True,
        max_cloud_calls=6,
        fabric_iq_mcp_endpoint="https://api.fabric.microsoft.com/v1/mcp/dataPlane/test",
        fabric_iq_access_token="secret",
        duckdb_path=database_path,
    )
    transport = QueueTransport(_handshake() + [_semantic_text("CertificationReady")])
    provider = FabricIQProvider(
        settings, transport=transport, local_provider=local, allow_local_fallback=True
    )

    concept = provider.resolve_concept("Exam Eligible")

    assert concept.concept_id == "exam_eligible"
    assert "Exam Eligible" not in provider.semantic_proofs


def test_fabric_without_fallback_still_rejects_an_ungrounded_concept(tmp_path: Path) -> None:
    """Capture/diagnostics keep the strict path: an unmatched concept is rejected, not local."""
    from concord.config import ScenarioPack
    from concord.seed.seed_duckdb import seed_duckdb

    database_path = tmp_path / "concord-iq.duckdb"
    seed_duckdb(database_path=database_path, data_dir=tmp_path / "csv")
    local = LocalProvider.for_scenario_pack(ScenarioPack.LEARNING, duckdb_path=database_path)
    settings = Settings(
        _env_file=None,
        provider="fabric_iq",
        scenario_pack="learning",
        allow_cloud=True,
        max_cloud_calls=6,
        fabric_iq_mcp_endpoint="https://api.fabric.microsoft.com/v1/mcp/dataPlane/test",
        fabric_iq_access_token="secret",
        duckdb_path=database_path,
    )
    transport = QueueTransport(_handshake() + [_semantic_text("CertificationReady")])
    provider = FabricIQProvider(settings, transport=transport, local_provider=local)

    with pytest.raises(ProviderNotConfigured, match="Connectivity-only"):
        provider.resolve_concept("Exam Eligible")
