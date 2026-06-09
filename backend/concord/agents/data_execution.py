"""Execute definitions and preserve exact SQL as evidence."""

from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

from concord.orchestration.casefile import ConflictHypothesis, EvidenceRecord
from concord.providers import (
    DefinitionBinding,
    DefinitionEvaluation,
    EvaluationPeriod,
    GroundingProvider,
)


@dataclass(frozen=True, slots=True)
class ExecutionBundle:
    evaluations: tuple[DefinitionEvaluation, ...]
    evidence: tuple[EvidenceRecord, ...]
    hypotheses: tuple[ConflictHypothesis, ...]
    verdict: str


@dataclass(frozen=True, slots=True)
class DataExecutionAgent:
    """Settle conflict versus equivalence through DuckDB result sets."""

    provider: GroundingProvider

    def run(
        self,
        run_id: str,
        bindings: tuple[DefinitionBinding, ...],
        period: EvaluationPeriod,
        hypotheses: tuple[ConflictHypothesis, ...] = (),
    ) -> ExecutionBundle:
        evaluations = tuple(
            self.provider.evaluate_definition(binding.binding_id, period) for binding in bindings
        )
        entity_sets = {frozenset(evaluation.entity_ids) for evaluation in evaluations}
        verdict = "conflict" if len(entity_sets) > 1 else "consistent"
        evidence = tuple(
            EvidenceRecord(
                evidence_id=uuid5(
                    NAMESPACE_URL,
                    f"concord-iq:{run_id}:{evaluation.binding_id}",
                ),
                binding_id=evaluation.binding_id,
                definition_id=evaluation.definition_id,
                source_ref=f"duckdb:{evaluation.binding_id}",
                entity_count=evaluation.entity_count,
                metric_total=evaluation.metric_total,
                entity_ids=evaluation.entity_ids,
                sql_text=evaluation.executed_sql,
            )
            for evaluation in evaluations
        )
        ruled_hypotheses = self._rule_on_hypotheses(hypotheses, evaluations, evidence)
        return ExecutionBundle(
            evaluations=evaluations,
            evidence=evidence,
            hypotheses=ruled_hypotheses,
            verdict=verdict,
        )

    @staticmethod
    def _rule_on_hypotheses(
        hypotheses: tuple[ConflictHypothesis, ...],
        evaluations: tuple[DefinitionEvaluation, ...],
        evidence: tuple[EvidenceRecord, ...],
    ) -> tuple[ConflictHypothesis, ...]:
        evaluations_by_binding = {item.binding_id: item for item in evaluations}
        evidence_by_binding = {item.binding_id: item for item in evidence}
        ruled: list[ConflictHypothesis] = []
        for hypothesis in hypotheses:
            left = evaluations_by_binding[hypothesis.left_binding_id]
            right = evaluations_by_binding[hypothesis.right_binding_id]
            unequal_sets = frozenset(left.entity_ids) != frozenset(right.entity_ids)
            ruled.append(
                hypothesis.model_copy(
                    update={
                        "data_verdict": "confirmed" if unequal_sets else "overturned",
                        "evidence_ids": (
                            evidence_by_binding[hypothesis.left_binding_id].evidence_id,
                            evidence_by_binding[hypothesis.right_binding_id].evidence_id,
                        ),
                    }
                )
            )
        return tuple(ruled)
