"""Cloud-free Foundry Agent Service hosting acceptance tests."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest
from concord.config import CloudAccessDisabled, Settings
from concord.demo import DEMO_SCENARIOS
from concord.ms_agent.foundry_hosted_entrypoint import dry_run, run_smoke
from concord.providers import FabricIQProvider, FoundryIQProvider, LocalProvider
from concord.providers.base import ProviderMode
from concord.providers.replay_schema import (
    build_replay_artifact,
    snapshot_provider_scenario,
)
from sqlalchemy import Engine

pytest.importorskip("agent_framework_foundry_hosting")


def _database_url(engine: Engine) -> str:
    return engine.url.render_as_string(hide_password=False)


def test_foundry_agent_dry_run_builds_protocol_without_cloud(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_cloud_call(*args, **kwargs):
        raise AssertionError("Foundry dry-run attempted a cloud IQ call")

    monkeypatch.setattr(FabricIQProvider, "_retrieve_snapshot", unexpected_cloud_call)
    monkeypatch.setattr(FoundryIQProvider, "_retrieve_snapshot", unexpected_cloud_call)

    result = dry_run(
        Settings(_env_file=None, allow_cloud=False, max_cloud_calls=0),
        provider="local",
        workflow_mode="strict",
    )

    assert result["status"] == "ready"
    assert result["provider_mode"] == "local"
    assert result["workflow_mode"] == "strict"
    assert result["cloud_enabled"] is False
    assert {"/readiness", "/responses"}.issubset(result["routes"])


def test_foundry_agent_local_smoke_executes_responses_protocol(
    postgres_engine: Engine,
    p2_local_provider: LocalProvider,
) -> None:
    result = asyncio.run(
        run_smoke(
            Settings(
                _env_file=None,
                database_url=_database_url(postgres_engine),
                duckdb_path=p2_local_provider.duckdb_path,
                allow_cloud=False,
                max_cloud_calls=0,
            ),
            provider="local",
            workflow_mode="strict",
        )
    )

    assert result.provider_mode == "local"
    assert result.workflow_mode == "strict"
    # run_smoke defaults to the challenge-facing learning term.
    assert result.term == "Certification Ready"
    assert result.verdict == "conflict"
    assert result.verification_status == "passed"
    assert result.specialist_steps == 10
    assert result.readiness_status == 200
    assert result.response_status == 200


def test_foundry_agent_smoke_supports_verified_replay_without_cloud(
    tmp_path: Path,
    postgres_engine: Engine,
    p2_local_provider: LocalProvider,
) -> None:
    artifact_path = tmp_path / "verified-replay.json"
    build_replay_artifact(
        provider_name="FabricIQProvider",
        provider_mode=ProviderMode.FABRIC_IQ,
        scenarios=tuple(
            snapshot_provider_scenario(p2_local_provider, scenario) for scenario in DEMO_SCENARIOS
        ),
        verified_real_iq=True,
        captured_at=datetime(2026, 6, 7, tzinfo=UTC),
        api_version="test",
    ).write(artifact_path)

    result = asyncio.run(
        run_smoke(
            Settings(
                _env_file=None,
                database_url=_database_url(postgres_engine),
                replay_artifact_path=artifact_path,
                allow_cloud=False,
                max_cloud_calls=0,
            ),
            provider="replay",
            workflow_mode="strict",
            term="Net Revenue",
        )
    )

    assert result.provider_mode == "replay"
    assert result.verdict == "consistent"
    assert result.verification_status == "passed"
    assert result.specialist_steps == 10


def test_real_foundry_host_still_fails_closed_without_cloud_permission() -> None:
    with pytest.raises(CloudAccessDisabled, match="Foundry Agent Service is disabled"):
        dry_run(
            Settings(
                _env_file=None,
                fabric_iq_mcp_endpoint="https://api.fabric.microsoft.com/v1/mcp/dataPlane/test",
                fabric_iq_access_token="placeholder",
                allow_cloud=False,
                max_cloud_calls=0,
            ),
            provider="auto",
        )
