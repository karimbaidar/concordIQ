"""Tests for retrievable Fabric scenario content, parsing, and diagnostics.

No test makes a cloud call: the MCP transport and the OneLake sender are injected.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from concord.config import Settings
from concord.demo import DEMO_SCENARIOS
from concord.fabric_bootstrap import onelake_dfs_url, upload_scenario_content
from concord.fabric_mcp_diagnose import diagnose
from concord.fabric_seed import build_scenario_content
from concord.providers import FabricIQProvider, LocalProvider
from concord.providers.cloud import HttpResult
from concord.providers.replay_schema import (
    ReplayScenarioSnapshot,
    SnapshotNotFound,
    find_snapshot,
    snapshot_provider_scenario,
)


def _snapshots(provider: LocalProvider) -> tuple[ReplayScenarioSnapshot, ...]:
    return tuple(snapshot_provider_scenario(provider, scenario) for scenario in DEMO_SCENARIOS)


class QueueTransport:
    def __init__(self, responses: list[HttpResult]) -> None:
        self.responses = responses
        self.requests: list[dict[str, Any]] = []

    def request(self, method, url, *, headers, body) -> HttpResult:
        self.requests.append({"method": method, "url": url, "body": body})
        return self.responses.pop(0)


# ---- scenario content is real, retrievable snapshot JSON (not just entity types) ----


def test_build_scenario_content_holds_valid_snapshots_for_all_capture_scenarios(
    p2_local_provider: LocalProvider,
) -> None:
    content = build_scenario_content(_snapshots(p2_local_provider))
    document = json.loads(content)

    terms = {entry["term"] for entry in document["scenarios"]}
    assert terms == {scenario.term for scenario in DEMO_SCENARIOS}
    for entry in document["scenarios"]:
        # Each stored snapshot reconstructs a valid ReplayScenarioSnapshot.
        snapshot = ReplayScenarioSnapshot.model_validate(entry["snapshot"])
        assert snapshot.bindings and snapshot.evaluations and snapshot.authority_rules


def test_exported_seed_writes_scenario_content_file(tmp_path: Path) -> None:
    from concord.fabric_seed import export_fabric_seed

    manifest = export_fabric_seed(
        Settings(_env_file=None, duckdb_path=tmp_path / "data.duckdb"),
        output_dir=tmp_path / "fabric_seed",
        data_dir=tmp_path / "synthetic",
    )
    content_path = tmp_path / "fabric_seed" / "concord_iq_scenarios.json"
    assert content_path in manifest.files
    document = json.loads(content_path.read_text(encoding="utf-8"))
    assert len(document["scenarios"]) == len(DEMO_SCENARIOS)


# ---- robust parsing across direct / markdown / wrapped / prose ----


def test_find_snapshot_extracts_from_text_markdown_and_mcp_wrapper(
    p2_local_provider: LocalProvider,
) -> None:
    snapshot = _snapshots(p2_local_provider)[0]
    snapshot_json = snapshot.model_dump_json()

    direct = json.loads(snapshot_json)
    fenced = f"Here is the snapshot:\n```json\n{snapshot_json}\n```\nThanks."
    prose = f"The result is {snapshot_json} as requested."
    mcp_wrapper = {
        "jsonrpc": "2.0",
        "id": 4,
        "result": {"content": [{"type": "text", "text": snapshot_json}]},
    }

    assert find_snapshot(direct).concept == snapshot.concept
    assert find_snapshot(fenced).concept == snapshot.concept
    assert find_snapshot(prose).concept == snapshot.concept
    assert find_snapshot(mcp_wrapper).concept == snapshot.concept


def test_find_snapshot_reports_missing_fields_for_partial_response() -> None:
    partial = {
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"scenario_id": "active-customer", "term": "x"}),
                }
            ]
        }
    }
    with pytest.raises(SnapshotNotFound) as excinfo:
        find_snapshot(partial)
    assert set(excinfo.value.missing_fields) >= {"concept", "bindings", "evaluations", "subgraph"}
    assert "missing required fields" in str(excinfo.value)


def test_find_snapshot_reports_no_snapshot_for_entity_types_only_response() -> None:
    # What today's ontology returns: entity types, no scenario content.
    response = {
        "result": {"entityTypes": [{"name": "ActiveCustomer", "properties": ["DisplayName"]}]}
    }
    with pytest.raises(SnapshotNotFound) as excinfo:
        find_snapshot(response)
    assert "did not contain a Concord IQ scenario snapshot" in str(excinfo.value)
    assert "fabric-mcp-diagnose" in str(excinfo.value)


# ---- OneLake upload plumbing (no network) ----


def test_onelake_dfs_url_targets_lakehouse_files() -> None:
    url = onelake_dfs_url("ws-id", "lh-id", "Files/concord_iq_scenarios.json")
    assert url == (
        "https://onelake.dfs.fabric.microsoft.com/ws-id/lh-id/Files/concord_iq_scenarios.json"
    )


def test_upload_scenario_content_runs_create_append_flush_without_network() -> None:
    calls: list[tuple[str, str]] = []

    def sender(method: str, url: str, data: bytes | None, headers: dict[str, str]) -> int:
        assert headers["Authorization"].startswith("Bearer ")
        calls.append((method, url.split("?")[-1]))
        return 200

    status = upload_scenario_content(
        "ws-id",
        "lh-id",
        '{"scenarios": []}',
        token_loader=lambda: "storage-token",
        sender=sender,
    )
    assert status.startswith("uploaded")
    assert [method for method, _ in calls] == ["PUT", "PATCH", "PATCH"]
    assert [query for _, query in calls] == [
        "resource=file",
        "action=append&position=0",
        "action=flush&position=17",
    ]


# ---- diagnostic never writes secrets, never writes the capture artifact ----


def test_fabric_mcp_diagnose_redacts_secrets_and_skips_capture_artifact(
    tmp_path: Path,
    p2_local_provider: LocalProvider,
) -> None:
    snapshot = _snapshots(p2_local_provider)[0]
    # Embed a token, a GUID, and an email beside the snapshot to prove redaction.
    leaky_text = (
        snapshot.model_dump_json()
        + " token=super-secret-token guid=123e4567-e89b-42d3-a456-426614174000 person@example.com"
    )
    transport = QueueTransport(
        [
            HttpResult(payload={"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}, headers={}),
            HttpResult(payload={}, headers={}),
            HttpResult(
                payload={"result": {"tools": [{"name": "search_ontology", "inputSchema": {}}]}},
                headers={},
            ),
            HttpResult(
                payload={"result": {"content": [{"type": "text", "text": leaky_text}]}},
                headers={},
            ),
        ]
    )
    settings = Settings(
        _env_file=None,
        allow_cloud=True,
        max_cloud_calls=6,
        fabric_iq_mcp_endpoint="https://api.fabric.microsoft.com/v1/mcp/dataPlane/test",
        fabric_iq_access_token="super-secret-token",
        capture_raw_dir=tmp_path / "raw",
        capture_sanitized_path=tmp_path / "sanitized" / "latest.json",
    )
    provider = FabricIQProvider(settings, transport=transport)

    report = diagnose(settings, provider=provider)

    assert report["snapshot_found"] is True
    assert "search_ontology" in report["tools"]

    diagnostic_text = (tmp_path / "raw" / "diagnostic.json").read_text(encoding="utf-8")
    assert "super-secret-token" not in diagnostic_text
    assert "person@example.com" not in diagnostic_text
    assert "123e4567-e89b-42d3-a456-426614174000" not in diagnostic_text
    # Diagnose must never write the capture artifact.
    assert not (tmp_path / "sanitized" / "latest.json").exists()
