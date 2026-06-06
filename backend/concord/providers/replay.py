"""Sanitized Microsoft IQ response replay mode."""

from dataclasses import dataclass

from concord.providers.base import ProviderMode


@dataclass(frozen=True, slots=True)
class ReplayProvider:
    """P0 identity for deterministic replay; response loading arrives in Phase P5."""

    name: str = "ReplayProvider"
    mode: ProviderMode = ProviderMode.REPLAY
    uses_cloud: bool = False
