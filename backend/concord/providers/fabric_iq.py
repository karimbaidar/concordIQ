"""Fabric IQ provider boundary."""

from dataclasses import dataclass

from concord.providers.base import CloudProviderScaffold, ProviderMode


@dataclass(slots=True)
class FabricIQProvider(CloudProviderScaffold):
    """Fail-closed Fabric IQ scaffold; the verified adapter is a later phase."""

    name: str = "FabricIQProvider"
    mode: ProviderMode = ProviderMode.FABRIC_IQ
