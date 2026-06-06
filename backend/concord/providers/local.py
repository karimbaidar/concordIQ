"""Deterministic local grounding mode."""

from dataclasses import dataclass

from concord.providers.base import ProviderMode


@dataclass(frozen=True, slots=True)
class LocalProvider:
    """P0 identity for the deterministic development and reviewer mode."""

    name: str = "LocalProvider"
    mode: ProviderMode = ProviderMode.LOCAL
    uses_cloud: bool = False
