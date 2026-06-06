"""Deterministic business-term resolution."""

from dataclasses import dataclass

from concord.providers import ConceptResolution, GroundingProvider


@dataclass(frozen=True, slots=True)
class ConceptResolverAgent:
    """Resolve aliases using the provider registry, never an LLM."""

    provider: GroundingProvider

    def run(self, term: str) -> ConceptResolution:
        return self.provider.resolve_concept(term)
