"""Execute definitions and preserve exact SQL as evidence."""

from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

from concord.orchestration.casefile import EvidenceRecord
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
    ) -> ExecutionBundle:
        evaluations = tuple(
            self.provider.evaluate_definition(binding.binding_id, period) for binding in bindings
        )
        entity_sets = {evaluation.entity_ids for evaluation in evaluations}
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
        return ExecutionBundle(
            evaluations=evaluations,
            evidence=evidence,
            verdict=verdict,
        )
