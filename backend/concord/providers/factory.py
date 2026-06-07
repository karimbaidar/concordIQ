"""Configuration-driven provider construction and status reporting."""

from typing import Any

from concord.config import Settings
from concord.providers.base import GroundingProvider, ProviderMode, ProviderNotConfigured
from concord.providers.fabric_iq import FabricIQProvider
from concord.providers.foundry_hosted import FoundryHostedProvider
from concord.providers.foundry_iq import FoundryIQProvider
from concord.providers.local import LocalProvider
from concord.providers.replay import ReplayProvider


def fabric_iq_is_configured(settings: Settings) -> bool:
    """Return Fabric IQ readiness without making a network request."""
    return bool(settings.fabric_iq_mcp_endpoint and settings.fabric_iq_access_token)


def foundry_iq_is_configured(settings: Settings) -> bool:
    """Return Foundry IQ readiness without making a network request."""
    return bool(
        settings.foundry_iq_endpoint
        and settings.foundry_iq_knowledge_base
        and (settings.foundry_iq_access_token or settings.foundry_iq_api_key)
    )


def foundry_hosted_is_configured(settings: Settings) -> bool:
    """Return hosted runtime readiness without making a network request."""
    return bool(settings.foundry_hosted_endpoint and settings.foundry_access_token)


def create_preferred_cloud_provider(settings: Settings) -> GroundingProvider:
    """Prefer Fabric IQ, using Foundry IQ only when Fabric is not configured."""
    if fabric_iq_is_configured(settings):
        return FabricIQProvider(settings)
    if foundry_iq_is_configured(settings):
        return FoundryIQProvider(settings)
    raise ProviderNotConfigured(
        "No cloud IQ provider is configured. Configure Fabric IQ first or Foundry IQ "
        "as the fallback."
    )


def create_provider(settings: Settings) -> GroundingProvider:
    """Create exactly the configured provider without falling back silently."""
    try:
        mode = ProviderMode(settings.provider)
    except ValueError as error:
        raise ProviderNotConfigured(f"Unknown provider mode: {settings.provider}") from error
    if mode is ProviderMode.LOCAL:
        return LocalProvider(duckdb_path=settings.duckdb_path)
    if mode is ProviderMode.REPLAY:
        return ReplayProvider(
            settings.replay_artifact_path,
            require_verified_capture=settings.replay_require_verified_capture,
        )
    if mode is ProviderMode.FOUNDRY_IQ:
        return FoundryIQProvider(settings)
    if mode is ProviderMode.FABRIC_IQ:
        return FabricIQProvider(settings)
    if mode is ProviderMode.FOUNDRY_HOSTED:
        raise ProviderNotConfigured(
            "foundry_hosted is a complete-case runtime. Use FoundryHostedProvider "
            "through the Concord IQ API application."
        )
    raise ProviderNotConfigured(f"Unsupported provider mode: {mode}")


def provider_statuses(settings: Settings) -> list[dict[str, Any]]:
    """Report configuration readiness without making any cloud request."""
    replay_exists = settings.replay_artifact_path.exists()
    replay_verified = False
    if replay_exists:
        try:
            replay_verified = ReplayProvider(
                settings.replay_artifact_path,
                require_verified_capture=False,
            ).artifact.capture.verified_real_iq
        except (OSError, ValueError):
            replay_exists = False
    return [
        {
            "mode": ProviderMode.LOCAL,
            "name": "LocalProvider",
            "configured": True,
            "cloud": False,
            "detail": "Deterministic synthetic development and reviewer mode.",
        },
        {
            "mode": ProviderMode.REPLAY,
            "name": "ReplayProvider",
            "configured": replay_exists and replay_verified,
            "cloud": False,
            "detail": (
                "Verified sanitized IQ capture available."
                if replay_verified
                else "No verified sanitized IQ capture is configured."
            ),
        },
        {
            "mode": ProviderMode.FABRIC_IQ,
            "name": "FabricIQProvider",
            "configured": fabric_iq_is_configured(settings),
            "cloud": True,
            "detail": "Primary cloud grounding: Fabric IQ ontology MCP adapter.",
        },
        {
            "mode": ProviderMode.FOUNDRY_IQ,
            "name": "FoundryIQProvider",
            "configured": foundry_iq_is_configured(settings),
            "cloud": True,
            "detail": "Fallback cloud grounding: Azure AI Search knowledge-base adapter.",
        },
        {
            "mode": ProviderMode.FOUNDRY_HOSTED,
            "name": FoundryHostedProvider.name,
            "configured": foundry_hosted_is_configured(settings),
            "cloud": True,
            "detail": "Hosted Microsoft Agent Framework runtime through Foundry Agent Service.",
        },
    ]
