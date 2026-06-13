"""Foundry Agent Service hosted-runtime tooling tests (no cloud calls)."""

import json
from pathlib import Path
from typing import Any

import pytest
from concord.config import CloudAccessDisabled, Settings
from concord.ms_agent.foundry_hosted import (
    HostedSmokeError,
    HostedSmokeProof,
    cli_smoke_settings,
    extract_hosted_proof,
    hosted_dry_run,
    hosted_package,
    hosted_smoke,
    validate_hosted_proof,
)


def _valid_proof(**overrides: Any) -> dict[str, Any]:
    proof = {
        "provider_mode": "replay",
        "workflow_mode": "strict",
        "term": "Certification Ready",
        "verdict": "conflict",
        "verification_status": "passed",
        "specialist_steps": 10,
    }
    proof.update(overrides)
    return proof


def _responses_payload(proof: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps({"concord_iq_proof": proof, "case": {"stub": True}})
    return {"output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}]}


def _hosted_settings(tmp_path: Path, **overrides: Any) -> Settings:
    base = {
        "_env_file": None,
        "allow_cloud": True,
        "max_cloud_calls": 1,
        "foundry_hosted_endpoint": "https://concord-agent.example.com",
        "foundry_access_token": "super-secret-token",
        "replay_artifact_path": tmp_path / "latest.json",
    }
    base.update(overrides)
    return Settings(**base)


# ---- dry run (no cloud) ----


def test_hosted_dry_run_validates_entrypoint_and_artifact(tmp_path: Path) -> None:
    artifact = tmp_path / "latest.json"
    artifact.write_text("{}", encoding="utf-8")
    report = hosted_dry_run(Settings(_env_file=None, learning_replay_artifact_path=artifact))

    assert report["status"] == "ready"
    assert report["intended_runtime"] == "Foundry Agent Service"
    assert report["provider_mode"] == "replay"
    assert report["workflow_mode"] == "strict"
    env = report["required_env"]
    assert env["PROVIDER"] == "replay"
    assert env["CONCORD_WORKFLOW_MODE"] == "strict"
    assert "ReplayProvider is used" in report["explanation"]


def test_hosted_dry_run_requires_committed_artifact(tmp_path: Path) -> None:
    with pytest.raises(HostedSmokeError, match="replay artifact is missing"):
        hosted_dry_run(
            Settings(
                _env_file=None,
                learning_replay_artifact_path=tmp_path / "missing.json",
            )
        )


# ---- package (no secrets / raw) ----


def test_hosted_package_excludes_secrets_and_raw(tmp_path: Path) -> None:
    artifact = tmp_path / "latest.json"
    artifact.write_text("{}", encoding="utf-8")
    report_path = hosted_package(
        Settings(_env_file=None, learning_replay_artifact_path=artifact),
        output_dir=tmp_path / "foundry",
    )
    text = report_path.read_text(encoding="utf-8")

    assert "python -m concord.ms_agent.foundry_hosted_entrypoint" in text
    assert "replay" in text and "strict" in text
    # Excludes section names the things that must never ship.
    assert ".env" in text
    assert "artifacts/replay/raw/" in text
    assert ".venv/" in text and "node_modules/" in text
    # No secret-shaped values leaked.
    assert "super-secret-token" not in text
    assert "Bearer " not in text


# ---- proof validation ----


def test_validate_hosted_proof_accepts_expected_replay_strict_conflict() -> None:
    validate_hosted_proof(HostedSmokeProof.model_validate(_valid_proof()))


@pytest.mark.parametrize(
    ("overrides", "needle"),
    [
        ({"provider_mode": "local"}, "provider_mode"),
        ({"workflow_mode": "fast"}, "workflow_mode"),
        ({"verification_status": "blocked"}, "verification_status"),
        ({"specialist_steps": 8}, "specialist_steps"),
        ({"verdict": "consistent"}, "verdict"),
    ],
)
def test_validate_hosted_proof_rejects_bad_responses(
    overrides: dict[str, Any], needle: str
) -> None:
    with pytest.raises(HostedSmokeError, match=needle):
        validate_hosted_proof(HostedSmokeProof.model_validate(_valid_proof(**overrides)))


def test_extract_hosted_proof_reads_envelope() -> None:
    proof = extract_hosted_proof(_responses_payload(_valid_proof()))
    assert proof.provider_mode == "replay"
    assert proof.specialist_steps == 10


# ---- hosted smoke (injected caller; no real network) ----


def test_hosted_smoke_passes_with_valid_response(tmp_path: Path) -> None:
    captured: dict[str, Any] = {}

    def caller(url: str, headers: dict[str, str], body: bytes) -> dict[str, Any]:
        captured["url"] = url
        captured["auth"] = headers["Authorization"]
        captured["body"] = json.loads(body)
        return _responses_payload(_valid_proof())

    proof = hosted_smoke(
        _hosted_settings(tmp_path),
        caller=caller,
        output_dir=tmp_path / "foundry",
    )

    assert proof.provider_mode == "replay"
    assert proof.workflow_mode == "strict"
    assert proof.verdict == "conflict"
    assert captured["url"] == "https://concord-agent.example.com/responses"
    # Report is written and contains no token.
    report = (tmp_path / "foundry" / "hosted-smoke-report.md").read_text(encoding="utf-8")
    assert "PASSED" in report
    assert "super-secret-token" not in report


def test_cli_smoke_settings_acquires_one_short_lived_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "concord.ms_agent.foundry_hosted.get_foundry_access_token",
        lambda: "fresh-token",
    )

    settings = cli_smoke_settings(
        Settings(
            _env_file=None,
            foundry_hosted_endpoint="https://concord-agent.example.com",
            foundry_access_token="",
        )
    )

    assert settings.allow_cloud is True
    assert settings.max_cloud_calls == 1
    assert settings.foundry_access_token is not None
    assert settings.foundry_access_token.get_secret_value() == "fresh-token"


def test_hosted_smoke_refuses_without_cloud_permission(tmp_path: Path) -> None:
    with pytest.raises(CloudAccessDisabled):
        hosted_smoke(_hosted_settings(tmp_path, allow_cloud=False, max_cloud_calls=0))


def test_hosted_smoke_refuses_without_endpoint_or_token(tmp_path: Path) -> None:
    with pytest.raises(HostedSmokeError, match="FOUNDRY_HOSTED_ENDPOINT"):
        hosted_smoke(_hosted_settings(tmp_path, foundry_hosted_endpoint=None))
    with pytest.raises(HostedSmokeError, match="FOUNDRY_HOSTED_ENDPOINT"):
        hosted_smoke(_hosted_settings(tmp_path, foundry_access_token=None))


def test_hosted_smoke_rejects_budget_above_one(tmp_path: Path) -> None:
    def caller(url: str, headers: dict[str, str], body: bytes) -> dict[str, Any]:
        raise AssertionError("caller must not run when the budget is rejected")

    with pytest.raises(HostedSmokeError, match="MAX_CLOUD_CALLS"):
        hosted_smoke(_hosted_settings(tmp_path, max_cloud_calls=5), caller=caller)


def test_hosted_smoke_rejects_invalid_response(tmp_path: Path) -> None:
    def caller(url: str, headers: dict[str, str], body: bytes) -> dict[str, Any]:
        return _responses_payload(_valid_proof(workflow_mode="fast"))

    with pytest.raises(HostedSmokeError, match="workflow_mode"):
        hosted_smoke(_hosted_settings(tmp_path), caller=caller, output_dir=tmp_path / "foundry")
