"""Deterministic blocking checks over verified evidence."""

from dataclasses import dataclass, field

from concord.llm import (
    DisabledLLMProvider,
    LLMProvider,
    NarrationRequest,
    NarrationTask,
)
from concord.orchestration.casefile import ReconciliationCase, VerifierReport


@dataclass(slots=True)
class SkepticalVerifierAgent:
    """Block unsupported conflicts and proposals without consulting an LLM."""

    llm_provider: LLMProvider = field(default_factory=DisabledLLMProvider)

    def run(self, case: ReconciliationCase) -> VerifierReport:
        concept_id = case.resolved_concept.concept_id if case.resolved_concept else ""
        entity_sets = {frozenset(evaluation.entity_ids) for evaluation in case.execution_results}
        evidence_ids = {item.evidence_id for item in case.evidence}
        proposal_refs = (
            set(case.reconciliation_proposal.evidence_refs)
            if case.reconciliation_proposal
            else set()
        )
        checks: dict[str, bool] = {
            "every_result_has_sql_evidence": (
                len(case.evidence) == len(case.execution_results)
                and all(item.sql_text.strip() for item in case.evidence)
            ),
        }
        if concept_id == "active_customer":
            checks.update(
                {
                    "three_definitions_executed": len(case.execution_results) == 3,
                    "conflict_has_divergent_sets": (
                        case.verdict == "conflict" and len(entity_sets) > 1
                    ),
                    "impact_is_high_and_ranked_first": (
                        case.impact_assessment is not None
                        and case.impact_assessment.severity == "high"
                        and case.impact_assessment.rank == 1
                    ),
                    "authority_is_configured": (
                        case.authority_assessment is not None
                        and case.authority_assessment.status == "clear"
                        and case.authority_assessment.owner is not None
                    ),
                    "proposal_cites_all_evidence": (
                        case.reconciliation_proposal is not None and proposal_refs == evidence_ids
                    ),
                    "proposal_requires_human_approval": (
                        case.requires_human_approval
                        and case.reconciliation_proposal is not None
                        and case.reconciliation_proposal.requires_human_approval
                    ),
                }
            )
        elif concept_id == "net_revenue":
            rows = {evaluation.rows for evaluation in case.execution_results}
            totals = {evaluation.metric_total for evaluation in case.execution_results}
            checks.update(
                {
                    "two_definitions_executed": len(case.execution_results) == 2,
                    "decoy_has_equal_entity_sets": (
                        case.verdict == "consistent" and len(entity_sets) == 1
                    ),
                    "decoy_has_equal_rows_and_totals": (len(rows) == 1 and len(totals) == 1),
                    "consistent_case_has_no_proposal_or_refusal": (
                        case.reconciliation_proposal is None
                        and case.refusal_reason is None
                        and not case.requires_human_approval
                    ),
                    "consistent_case_has_low_impact": (
                        case.impact_assessment is not None
                        and case.impact_assessment.severity == "low"
                        and case.impact_assessment.customer_count_delta == 0
                        and case.impact_assessment.arr_delta == 0
                    ),
                }
            )
        elif concept_id == "churned_customer":
            checks.update(
                {
                    "two_definitions_executed": len(case.execution_results) == 2,
                    "conflict_has_divergent_sets": (
                        case.verdict == "conflict" and len(entity_sets) > 1
                    ),
                    "authority_requires_escalation": (
                        case.authority_assessment is not None
                        and case.authority_assessment.status in {"shared", "ambiguous", "missing"}
                        and case.authority_assessment.owner is None
                    ),
                    "refusal_does_not_invent_proposal": (
                        case.reconciliation_proposal is None and bool(case.refusal_reason)
                    ),
                    "refusal_requires_human_approval": (
                        case.requires_human_approval
                        and "human approval is required" in (case.refusal_reason or "").lower()
                    ),
                }
            )
        elif concept_id == "qualified_lead":
            checks.update(
                {
                    "two_definitions_executed": len(case.execution_results) == 2,
                    "conflict_has_divergent_sets": (
                        case.verdict == "conflict" and len(entity_sets) > 1
                    ),
                    "authority_is_configured": (
                        case.authority_assessment is not None
                        and case.authority_assessment.status == "clear"
                        and case.authority_assessment.owner is not None
                    ),
                    "proposal_cites_all_evidence": (
                        case.reconciliation_proposal is not None and proposal_refs == evidence_ids
                    ),
                    "proposal_requires_human_approval": (
                        case.requires_human_approval
                        and case.reconciliation_proposal is not None
                        and case.reconciliation_proposal.requires_human_approval
                    ),
                }
            )
        else:
            checks["scenario_is_supported"] = False
        failures = tuple(name for name, passed in checks.items() if not passed)
        passed = not failures
        narration = self.llm_provider.narrate(
            NarrationRequest(
                task=NarrationTask.VERIFIER,
                facts={
                    "concept_id": concept_id,
                    "verdict": case.verdict,
                    "passed": passed,
                    "checks": checks,
                    "failure_names": failures,
                    "evidence_count": len(case.evidence),
                },
                fallback_text=(
                    "All deterministic blocking checks passed over the stored SQL "
                    "evidence and configured authority."
                    if passed
                    else f"Deterministic blocking checks failed: {', '.join(failures)}."
                ),
            )
        )
        return VerifierReport(
            passed=passed,
            checks=checks,
            failures=failures,
            advisory_notes=(narration.text,),
            narration=narration,
        )
