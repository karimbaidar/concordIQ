"""Deterministic scenario selection for implemented reconciliation cases."""

from concord.providers import ConceptResolution


class UnsupportedScenario(ValueError):
    """Raised when a scenario has no implemented deterministic decision path."""


class CoordinatorAgent:
    """Limit execution to the reviewed synthetic scenarios."""

    supported_concepts = frozenset(
        {
            "active_customer",
            "net_revenue",
            "churned_customer",
            "qualified_lead",
            "certification_ready",
            "required_training_complete",
            "exam_eligible",
        }
    )

    def require_supported(self, concept: ConceptResolution) -> None:
        if concept.concept_id not in self.supported_concepts:
            raise UnsupportedScenario(
                f"No deterministic reconciliation path is implemented for {concept.canonical_name}."
            )
