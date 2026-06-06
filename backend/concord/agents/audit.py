"""Persist verified casefiles and audit timelines."""

from dataclasses import dataclass
from uuid import UUID

from concord.llm import LLMProvider, NarrationRequest, NarrationTask
from concord.orchestration.casefile import ReconciliationCase
from concord.storage.repositories import ReconciliationRepository


@dataclass(slots=True)
class AuditAgent:
    """Write the final typed case to PostgreSQL."""

    repository: ReconciliationRepository
    llm_provider: LLMProvider

    def run(self, case: ReconciliationCase) -> UUID:
        narration = self.llm_provider.narrate(
            NarrationRequest(
                task=NarrationTask.AUDIT,
                facts={
                    "term": (
                        case.resolved_concept.canonical_name
                        if case.resolved_concept
                        else case.request.term
                    ),
                    "verdict": case.verdict,
                    "definition_counts": {
                        result.definition_id: result.entity_count
                        for result in case.execution_results
                    },
                    "impact": (
                        case.impact_assessment.model_dump(mode="json")
                        if case.impact_assessment
                        else None
                    ),
                    "authority": (
                        case.authority_assessment.model_dump(mode="json")
                        if case.authority_assessment
                        else None
                    ),
                    "requires_human_approval": case.requires_human_approval,
                    "evidence_count": len(case.evidence),
                    "verifier_passed": bool(case.verifier_report and case.verifier_report.passed),
                },
                fallback_text=(
                    f"Concord IQ completed {case.request.term} with verdict "
                    f"{case.verdict}, {len(case.evidence)} stored evidence records, "
                    "and deterministic verifier approval."
                ),
            )
        )
        case.narrations = (*case.narrations, narration)
        return self.repository.save(case)
