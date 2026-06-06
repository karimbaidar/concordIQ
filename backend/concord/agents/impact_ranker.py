"""Deterministic business impact ranking."""

from concord.orchestration.casefile import ImpactAssessment
from concord.providers import DefinitionBinding, DefinitionEvaluation


class ImpactRankerAgent:
    """Rank materiality from population and ARR differences."""

    def run(
        self,
        bindings: tuple[DefinitionBinding, ...],
        evaluations: tuple[DefinitionEvaluation, ...],
    ) -> ImpactAssessment:
        counts = [evaluation.entity_count for evaluation in evaluations]
        totals = [evaluation.metric_total for evaluation in evaluations]
        customer_delta = max(counts) - min(counts)
        arr_delta = round(max(totals) - min(totals), 2)
        units = tuple(dict.fromkeys(binding.owner for binding in bindings))
        if customer_delta == 0 and arr_delta == 0:
            return ImpactAssessment(
                rank=0,
                severity="low",
                customer_count_delta=0,
                arr_delta=0.0,
                reports_affected=len(units),
                business_units_affected=units,
                decision_criticality="low",
            )
        high_impact = customer_delta >= 10 or arr_delta >= 1_000_000
        return ImpactAssessment(
            rank=1,
            severity="high" if high_impact else "medium",
            customer_count_delta=customer_delta,
            arr_delta=arr_delta,
            reports_affected=len(units),
            business_units_affected=units,
            decision_criticality="high",
        )
