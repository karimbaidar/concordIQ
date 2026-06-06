"""Deterministic operational binding inspection."""

from dataclasses import dataclass

from concord.providers import DefinitionBinding, GroundingProvider


@dataclass(frozen=True, slots=True)
class BindingInspectorAgent:
    """Return normalized rules, filters, windows, grain, and population."""

    provider: GroundingProvider

    def run(self, concept_id: str) -> tuple[DefinitionBinding, ...]:
        return tuple(self.provider.get_binding_semantics(concept_id))
