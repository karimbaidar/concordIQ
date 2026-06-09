"""Pairwise hypotheses that execution must confirm or reject."""

from itertools import combinations

from concord.orchestration.casefile import ConflictHypothesis
from concord.providers import DefinitionBinding


class ConflictHypothesisAgent:
    """Describe possible semantic differences without deciding the verdict."""

    def run(
        self,
        bindings: tuple[DefinitionBinding, ...],
    ) -> tuple[ConflictHypothesis, ...]:
        hypotheses: list[ConflictHypothesis] = []
        for left, right in combinations(bindings, 2):
            differences = set(left.semantic_dimensions) ^ set(right.semantic_dimensions)
            if left.time_window_days != right.time_window_days:
                differences.add("activity-window")
            if left.source_tables != right.source_tables:
                differences.add("source-lineage")
            dimensions = tuple(sorted(differences))
            dimension_text = ", ".join(item.replace("-", " ") for item in dimensions)
            hypotheses.append(
                ConflictHypothesis(
                    left_binding_id=left.binding_id,
                    right_binding_id=right.binding_id,
                    differing_dimensions=dimensions,
                    rationale=(
                        f"{left.owner} and {right.owner} use different operational "
                        "dimensions; execute both bindings to determine materiality."
                    ),
                    claim=(
                        f"{left.owner} and {right.owner} are suspected to select "
                        f"different populations because their bindings differ on "
                        f"{dimension_text or 'operational wording'}."
                    ),
                    skeptic_challenge=(
                        "Operational wording alone is not proof. Confirm the conflict "
                        "only if deterministic SQL returns unequal entity sets."
                    ),
                )
            )
        return tuple(hypotheses)
