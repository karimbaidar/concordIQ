"""Manual, opt-in capture of typed synthetic Microsoft IQ responses."""

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from concord.config import CloudAccessDisabled, Settings
from concord.demo import DEMO_SCENARIOS
from concord.providers import FabricIQProvider, FoundryIQProvider, create_provider
from concord.providers.base import ProviderNotConfigured
from concord.providers.cloud import CloudCallBudgetExceeded, CloudTransportError
from concord.providers.fabric_iq import SEMANTIC_PROOF_MODE, SEMANTIC_SNAPSHOT_SOURCE
from concord.providers.replay_schema import build_replay_artifact, snapshot_provider_scenario

GUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b"
)
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
URL_PATTERN = re.compile(r"https://[^\s\"']+")


def sanitize_value(value: Any, *, secret_values: tuple[str, ...] = ()) -> Any:
    """Redact tenant-shaped identifiers from a JSON-compatible value."""
    if isinstance(value, dict):
        return {
            key: sanitize_value(item, secret_values=secret_values) for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize_value(item, secret_values=secret_values) for item in value]
    if isinstance(value, str):
        sanitized = value
        for secret in secret_values:
            if secret:
                sanitized = sanitized.replace(secret, "[REDACTED]")
        sanitized = GUID_PATTERN.sub("[REDACTED-GUID]", sanitized)
        sanitized = EMAIL_PATTERN.sub("[REDACTED-EMAIL]", sanitized)
        return URL_PATTERN.sub("[REDACTED-URL]", sanitized)
    return value


def _secret_values(settings: Settings) -> tuple[str, ...]:
    secrets = (
        settings.foundry_iq_access_token,
        settings.foundry_iq_api_key,
        settings.fabric_iq_access_token,
    )
    return tuple(secret.get_secret_value() for secret in secrets if secret)


def _write_raw_responses(
    raw_dir: Path,
    provider_name: str,
    responses: tuple[dict[str, object], ...],
) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = raw_dir / f"{timestamp}-{provider_name}.json"
    path.write_text(json.dumps(responses, indent=2, default=str), encoding="utf-8")
    return path


def _fabric_proof_provenance(provider: object) -> dict[str, object]:
    """Provenance kwargs when Fabric IQ proved concepts but returned no full snapshot."""
    if not isinstance(provider, FabricIQProvider) or not provider.semantic_proofs:
        return {}
    proofs = provider.semantic_proofs
    return {
        "iq_proof_mode": SEMANTIC_PROOF_MODE,
        "snapshot_source": SEMANTIC_SNAPSHOT_SOURCE,
        "fabric_tools_used": provider.fabric_tool_names,
        "fabric_matched_concepts": {
            term: proof["matched_entity_type"] for term, proof in proofs.items()
        },
        "fabric_response_shapes": tuple(
            dict.fromkeys(proof["response_shape"] for proof in proofs.values())
        ),
        "semantic_proof_terms": tuple(proofs),
    }


def capture(settings: Settings) -> Path:
    """Capture all demo scenarios from one explicitly configured cloud provider."""
    settings.require_cloud_access(settings.provider)
    provider = create_provider(settings)
    if not isinstance(provider, (FoundryIQProvider, FabricIQProvider)):
        raise ValueError("Capture requires PROVIDER=foundry_iq or PROVIDER=fabric_iq.")

    try:
        snapshots = tuple(
            snapshot_provider_scenario(provider, scenario) for scenario in DEMO_SCENARIOS
        )
    finally:
        if provider.raw_responses:
            _write_raw_responses(
                settings.capture_raw_dir,
                provider.name,
                provider.raw_responses,
            )
    api_version = (
        settings.foundry_iq_api_version
        if isinstance(provider, FoundryIQProvider)
        else "MCP 2025-06-18"
    )
    artifact = build_replay_artifact(
        provider_name=provider.name,
        provider_mode=provider.mode,
        scenarios=snapshots,
        verified_real_iq=True,
        api_version=api_version,
        **_fabric_proof_provenance(provider),
    )
    sanitized = sanitize_value(
        artifact.model_dump(mode="json"),
        secret_values=_secret_values(settings),
    )
    reviewed_artifact = type(artifact).model_validate(sanitized)
    reviewed_artifact.write(settings.capture_sanitized_path)
    return settings.capture_sanitized_path


def main() -> None:
    try:
        path = capture(Settings())
    except (
        CloudAccessDisabled,
        CloudCallBudgetExceeded,
        CloudTransportError,
        ProviderNotConfigured,
        ValueError,
    ) as error:
        raise SystemExit(f"Capture refused: {error}") from error
    print(f"Wrote sanitized replay artifact to {path}")
    print("Review the sanitized file before staging it. Raw responses remain gitignored.")


if __name__ == "__main__":
    main()
