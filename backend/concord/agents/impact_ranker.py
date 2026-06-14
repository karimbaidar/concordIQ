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
        concept_id = bindings[0].concept_id if bindings else ""
        counts = [evaluation.entity_count for evaluation in evaluations]
        totals = [evaluation.metric_total for evaluation in evaluations]
        customer_delta = max(counts) - min(counts)
        arr_delta = round(max(totals) - min(totals), 2)
        units = tuple(dict.fromkeys(binding.owner for binding in bindings))
        entity_sets = [set(evaluation.entity_ids) for evaluation in evaluations]
        affected_entity_ids = tuple(
            sorted(set().union(*entity_sets) - set.intersection(*entity_sets))
        )
        if customer_delta == 0 and arr_delta == 0:
            learning_case = concept_id == "certification_ready"
            return ImpactAssessment(
                rank=0,
                severity="low",
                customer_count_delta=0,
                arr_delta=0.0,
                reports_affected=len(units),
                business_units_affected=units,
                decision_criticality="low",
                entity_label="learners" if learning_case else "customers",
                value_label="exam spend at risk" if learning_case else "metric delta",
                affected_entity_ids=affected_entity_ids,
            )
        high_impact = customer_delta >= 10 or arr_delta >= 1_000_000
        if concept_id == "certification_ready":
            evaluation_by_owner = {
                binding.owner: evaluation
                for binding, evaluation in zip(bindings, evaluations, strict=True)
            }
            hr = evaluation_by_owner["HR"]
            learning = evaluation_by_owner["Learning & Development"]
            learning_ids = set(learning.entity_ids)
            false_ready_rows = tuple(row for row in hr.rows if row.entity_id not in learning_ids)
            false_ready_ids = tuple(row.entity_id for row in false_ready_rows)
            exam_spend_at_risk = round(
                sum(row.metric_value for row in false_ready_rows),
                2,
            )
            return ImpactAssessment(
                rank=1,
                severity="high",
                customer_count_delta=customer_delta,
                arr_delta=exam_spend_at_risk,
                reports_affected=len(units),
                business_units_affected=units,
                decision_criticality="high",
                entity_label="learners",
                value_label="exam spend at risk",
                affected_entity_ids=affected_entity_ids,
                false_positive_count=len(false_ready_ids),
                false_positive_label="false-ready learners",
                false_positive_entity_ids=false_ready_ids,
            )
        return ImpactAssessment(
            rank=1,
            severity="high" if high_impact else "medium",
            customer_count_delta=customer_delta,
            arr_delta=arr_delta,
            reports_affected=len(units),
            business_units_affected=units,
            decision_criticality="high",
            affected_entity_ids=affected_entity_ids,
        )
