"""Deterministic scenario selection for the current phase."""

from concord.providers import ConceptResolution


class UnsupportedScenario(ValueError):
    """Raised when a scenario belongs to a later implementation phase."""


class CoordinatorAgent:
    """Keep the P2 execution plan scoped to Active Customer."""

    def require_supported(self, concept: ConceptResolution) -> None:
        if concept.concept_id != "active_customer":
            raise UnsupportedScenario(
                "Phase P2 supports Active Customer only; other verdicts arrive in P3."
            )
