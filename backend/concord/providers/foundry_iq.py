"""Foundry IQ provider boundary."""

from dataclasses import dataclass

from concord.providers.base import CloudProviderScaffold, ProviderMode


@dataclass(slots=True)
class FoundryIQProvider(CloudProviderScaffold):
    """Fail-closed Foundry IQ scaffold; the verified adapter is a later phase."""

    name: str = "FoundryIQProvider"
    mode: ProviderMode = ProviderMode.FOUNDRY_IQ
