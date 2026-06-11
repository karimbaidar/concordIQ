"""Fabric seed, bootstrap guard, and replay-verification tests."""

import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
from concord.config import CloudAccessDisabled, Settings
from concord.demo import DEMO_SCENARIOS
from concord.fabric_bootstrap import (
    FabricHttpResponse,
    UrllibFabricTransport,
    bootstrap,
    dry_run,
    fabric_mcp_endpoint,
)
from concord.providers import LocalProvider
from concord.providers.base import ProviderMode
from concord.providers.replay_schema import (
    ReplayArtifact,
    ReplayScenarioSnapshot,
    build_replay_artifact,
    snapshot_provider_scenario,
)
from concord.replay_check import ReplayCheckError, validate_replay_artifact

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
JSON_BLOCK = re.compile(r"```json\n(.*?)\n```", re.DOTALL)


class StubFabricTransport:
    def __init__(self) -> None:
        self.requests: list[tuple[str, str, dict[str, object] | None]] = []

    def request(
        self,
        method: str,
        url: str,
        *,
        token: str,
        body: dict[str, object] | None = None,
    ) -> FabricHttpResponse:
        assert token == "test-token"
        self.requests.append((method, url, body))
        if url.endswith("/workspaces") and method == "GET":
            return FabricHttpResponse(200, {"value": []}, {})
        if url.endswith("/workspaces") and method == "POST":
            return FabricHttpResponse(201, {"id": "workspace-id"}, {})
        if "items?type=Lakehouse" in url:
            return FabricHttpResponse(200, {"value": []}, {})
        if url.endswith("/lakehouses"):
            return FabricHttpResponse(201, {"id": "lakehouse-id"}, {})
        if "items?type=Ontology" in url:
            return FabricHttpResponse(200, {"value": []}, {})
        if url.endswith("/ontologies"):
            return FabricHttpResponse(201, {"id": "ontology-id"}, {})
        if "updateDefinition" in url:
            return FabricHttpResponse(200, {}, {})
        raise AssertionError(f"unexpected Fabric request: {method} {url}")


def _snapshots(provider: LocalProvider) -> tuple[ReplayScenarioSnapshot, ...]:
    return tuple(snapshot_provider_scenario(provider, scenario) for scenario in DEMO_SCENARIOS)


def _artifact(
    provider: LocalProvider,
    *,
    verified: bool = True,
    snapshots: tuple[ReplayScenarioSnapshot, ...] | None = None,
) -> ReplayArtifact:
    return build_replay_artifact(
        provider_name="FabricIQProvider",
        provider_mode=ProviderMode.FABRIC_IQ,
        scenarios=snapshots or _snapshots(provider),
        verified_real_iq=verified,
        captured_at=datetime(2026, 6, 7, tzinfo=UTC),
        api_version="MCP 2025-06-18",
    )


def test_env_example_contains_required_bootstrap_keys() -> None:
    text = (REPOSITORY_ROOT / ".env.example").read_text(encoding="utf-8")
    required = {
        "PROVIDER",
        "ALLOW_CLOUD",
        "MAX_CLOUD_CALLS",
        "DATABASE_URL",
        "DUCKDB_PATH",
        "REPLAY_ARTIFACT_PATH",
        "CAPTURE_RAW_DIR",
        "CAPTURE_SANITIZED_PATH",
        "FABRIC_WORKSPACE_NAME",
        "FABRIC_LAKEHOUSE_NAME",
        "FABRIC_ONTOLOGY_NAME",
        "FABRIC_CAPACITY_ID",
        "FABRIC_WORKSPACE_ID",
        "FABRIC_LAKEHOUSE_ID",
        "FABRIC_ONTOLOGY_ID",
        "FABRIC_IQ_MCP_ENDPOINT",
        "FOUNDRY_IQ_ENDPOINT",
        "FOUNDRY_IQ_KNOWLEDGE_BASE",
        "FOUNDRY_PROJECT_ENDPOINT",
        "AZURE_AI_MODEL_DEPLOYMENT_NAME",
    }
    keys = {
        line.split("=", maxsplit=1)[0]
        for line in text.splitlines()
        if line and not line.startswith("#") and "=" in line
    }
    assert required <= keys
    assert "Bearer " not in text
    # Access tokens are acquired at runtime, never stored in .env.example.
    assert "FABRIC_IQ_ACCESS_TOKEN=" not in text.replace("# FABRIC_IQ_ACCESS_TOKEN=", "")


def test_fabric_bootstrap_dry_run_never_calls_cloud(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_request(*args, **kwargs):
        raise AssertionError("dry run attempted a Fabric API call")

    monkeypatch.setattr(UrllibFabricTransport, "request", unexpected_request)
    settings = Settings(
        _env_file=None,
        duckdb_path=tmp_path / "data.duckdb",
    )

    manifest = dry_run(
        settings,
        output_dir=tmp_path / "fabric_seed",
        data_dir=tmp_path / "synthetic",
    )

    assert len(manifest.snapshots) == 3
    assert (manifest.output_dir / "bootstrap-report.md").exists()


def test_fabric_bootstrap_refuses_without_cloud_opt_in(tmp_path: Path) -> None:
    with pytest.raises(CloudAccessDisabled):
        bootstrap(
            Settings(
                _env_file=None,
                allow_cloud=False,
                duckdb_path=tmp_path / "data.duckdb",
            ),
            output_dir=tmp_path / "fabric_seed",
            data_dir=tmp_path / "synthetic",
            token_loader=lambda: (_ for _ in ()).throw(
                AssertionError("token loader should not run")
            ),
        )


def test_fabric_mcp_endpoint_uses_workspace_and_ontology_ids() -> None:
    assert fabric_mcp_endpoint("workspace-id", "ontology-id") == (
        "https://api.fabric.microsoft.com/v1/mcp/dataPlane/workspaces/"
        "workspace-id/items/ontology-id/ontologyEndpoint"
    )


def test_fabric_bootstrap_creates_resources_and_prints_no_token(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    transport = StubFabricTransport()
    uploads: list[tuple[str, str, str]] = []

    def stub_uploader(workspace_id: str, lakehouse_id: str, content: str) -> str:
        uploads.append((workspace_id, lakehouse_id, content))
        return "uploaded (stub)"

    result = bootstrap(
        Settings(
            _env_file=None,
            allow_cloud=True,
            duckdb_path=tmp_path / "data.duckdb",
            fabric_iq_access_token="test-token",
        ),
        output_dir=tmp_path / "fabric_seed",
        data_dir=tmp_path / "synthetic",
        transport=transport,
        content_uploader=stub_uploader,
    )

    output = capsys.readouterr().out
    assert result.workspace.resource_id == "workspace-id"
    assert result.lakehouse.resource_id == "lakehouse-id"
    assert result.ontology.resource_id == "ontology-id"
    assert result.ontology_seeded is True
    assert result.scenario_content == "uploaded (stub)"
    # The uploaded content is the retrievable scenario snapshot JSON.
    assert uploads and '"scenarios"' in uploads[0][2]
    assert "FABRIC_IQ_MCP_ENDPOINT=" in output
    assert "fabric-mcp-diagnose" in output
    assert "test-token" not in output
    assert not (tmp_path / ".env").exists()


def test_fabric_seed_contains_typed_synthetic_snapshots(tmp_path: Path) -> None:
    output_dir = tmp_path / "fabric_seed"
    manifest = dry_run(
        Settings(_env_file=None, duckdb_path=tmp_path / "data.duckdb"),
        output_dir=output_dir,
        data_dir=tmp_path / "synthetic",
    )
    expected = {
        "active-customer-snapshot.md",
        "net-revenue-snapshot.md",
        "churned-customer-snapshot.md",
        "ontology_seed.md",
        "metric_definitions.csv",
        "authority_rules.csv",
        "bootstrap-report.md",
        "README.md",
        "concord_iq_scenarios.json",
    }
    assert expected == {path.name for path in manifest.files}
    for scenario in DEMO_SCENARIOS:
        text = (output_dir / f"{scenario.scenario_id}-snapshot.md").read_text(encoding="utf-8")
        match = JSON_BLOCK.search(text)
        assert match is not None
        snapshot = ReplayScenarioSnapshot.model_validate_json(match.group(1))
        assert snapshot.scenario_id == scenario.scenario_id
        assert snapshot.data_classification == "synthetic"
        assert snapshot.bindings
        assert snapshot.evaluations
        assert snapshot.subgraph.nodes
        assert snapshot.authority_rules


def test_replay_check_rejects_missing_artifact(tmp_path: Path) -> None:
    with pytest.raises(ReplayCheckError, match="does not exist"):
        validate_replay_artifact(tmp_path / "missing.json")


def test_replay_check_accepts_verified_semantic_artifact(
    tmp_path: Path,
    p2_local_provider: LocalProvider,
) -> None:
    path = tmp_path / "verified.json"
    _artifact(p2_local_provider).write(path)

    artifact = validate_replay_artifact(path)

    assert artifact.capture.verified_real_iq is True
    assert {scenario.scenario_id for scenario in artifact.scenarios} == {
        "active-customer",
        "net-revenue",
        "churned-customer",
    }


def test_replay_check_rejects_unverified_artifact(
    tmp_path: Path,
    p2_local_provider: LocalProvider,
) -> None:
    path = tmp_path / "unverified.json"
    _artifact(p2_local_provider, verified=False).write(path)

    with pytest.raises(ReplayCheckError, match="verified_real_iq=true"):
        validate_replay_artifact(path)


def test_replay_check_rejects_connectivity_only_artifact(
    tmp_path: Path,
    p2_local_provider: LocalProvider,
) -> None:
    snapshots = list(_snapshots(p2_local_provider))
    snapshots[0] = snapshots[0].model_copy(
        update={
            "bindings": (),
            "evaluations": (),
            "authority_rules": (),
        }
    )
    path = tmp_path / "shallow.json"
    _artifact(p2_local_provider, snapshots=tuple(snapshots)).write(path)

    with pytest.raises(ReplayCheckError, match="no metric definitions"):
        validate_replay_artifact(path)


def test_replay_check_rejects_obvious_secrets(
    tmp_path: Path,
    p2_local_provider: LocalProvider,
) -> None:
    artifact = _artifact(p2_local_provider)
    path = tmp_path / "secret.json"
    artifact.write(path)
    text = path.read_text(encoding="utf-8").replace(
        "A customer included in current operating and board-level activity reporting.",
        "Bearer should-never-appear",
    )
    path.write_text(text, encoding="utf-8")

    with pytest.raises(ReplayCheckError, match="forbidden secret-shaped"):
        validate_replay_artifact(path)
