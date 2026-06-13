"""Runtime selector coverage for the single-command reviewer demo."""

from concord.api.main import create_app
from concord.config import ScenarioPack, Settings
from concord.providers.fabric_iq import FabricIQProvider
from fastapi.testclient import TestClient


def test_cloud_provider_exposes_selected_scenario_pack() -> None:
    settings = Settings(
        _env_file=None,
        scenario_pack=ScenarioPack.LEARNING,
        allow_cloud=True,
        max_cloud_calls=6,
        fabric_iq_mcp_endpoint="https://api.fabric.microsoft.com/example",
        fabric_iq_access_token="test-token",
    )

    assert FabricIQProvider(settings).scenario_pack is ScenarioPack.LEARNING


def test_runtime_defaults_to_learning_and_business_is_disabled(
    postgres_engine,
    p2_local_provider,
) -> None:
    settings = Settings(
        _env_file=None,
        scenario_pack=ScenarioPack.LEARNING,
        runtime_switching=True,
        default_runtime_profile="local",
        enable_business=False,
        duckdb_path=p2_local_provider.duckdb_path,
    )
    app = create_app(settings, engine=postgres_engine)

    with TestClient(app) as client:
        state = client.get("/runtime")
        scenarios = client.get("/demo/scenarios")
        portfolio = client.get("/scan")
        blocked = client.post(
            "/runtime/select",
            json={
                "scenario_pack": "business",
                "runtime_profile": "local",
            },
        )

    assert state.status_code == 200
    assert state.json()["scenario_pack"] == "learning"
    assert state.json()["runtime_profile"] == "local"
    business = next(item for item in state.json()["scenario_packs"] if item["id"] == "business")
    assert business["enabled"] is False
    assert scenarios.json()[0]["scenario_id"] == "certification-ready"
    assert portfolio.status_code == 200
    assert portfolio.json()["score"]["concepts_scanned"] == 3
    assert portfolio.json()["provider"] == "LocalProvider"
    assert blocked.status_code == 409
    assert "CONCORD_ENABLE_BUSINESS=true" in blocked.json()["detail"]


def test_runtime_switches_between_learning_local_and_verified_replay(
    postgres_engine,
    p2_local_provider,
) -> None:
    settings = Settings(
        _env_file=None,
        scenario_pack=ScenarioPack.LEARNING,
        runtime_switching=True,
        default_runtime_profile="local",
        enable_business=False,
        duckdb_path=p2_local_provider.duckdb_path,
    )
    app = create_app(settings, engine=postgres_engine)

    with TestClient(app) as client:
        selected = client.post(
            "/runtime/select",
            json={
                "scenario_pack": "learning",
                "runtime_profile": "fabric_replay",
            },
        )
        health = client.get("/health")
        scenarios = client.get("/demo/scenarios")

    assert selected.status_code == 200
    assert selected.json()["runtime_profile"] == "fabric_replay"
    assert health.json()["provider_mode"] == "replay"
    assert health.json()["cloud_enabled"] is False
    assert health.json()["scenario_pack"] == "learning"
    assert scenarios.json() == [
        {
            "scenario_id": "certification-ready",
            "term": "Certification Ready",
            "question": (
                "Do HR, Learning and Development, and managers agree on who is Certification Ready?"
            ),
        }
    ]
