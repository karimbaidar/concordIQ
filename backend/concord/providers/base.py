"""Shared provider types for the P0 architecture boundary."""

from dataclasses import dataclass, field
from enum import StrEnum

from concord.config import Settings


class ProviderMode(StrEnum):
    """Supported semantic grounding modes."""

    LOCAL = "local"
    REPLAY = "replay"
    FOUNDRY_IQ = "foundry_iq"
    FABRIC_IQ = "fabric_iq"


class ProviderNotConfigured(RuntimeError):
    """Raised when a provider scaffold has no verified external configuration."""


@dataclass(slots=True)
class CloudProviderScaffold:
    """Fail-closed base for cloud adapters implemented in Phase P5."""

    settings: Settings = field(default_factory=Settings)
    name: str = "CloudProvider"
    mode: ProviderMode = ProviderMode.LOCAL

    def require_ready(self) -> None:
        """Verify cloud opt-in, then report that the P0 adapter is not configured."""
        self.settings.require_cloud_access(self.name)
        raise ProviderNotConfigured(
            f"{self.name} is an architecture scaffold in Phase P0; no endpoint is configured."
        )
