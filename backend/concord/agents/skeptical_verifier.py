"""Deterministic blocking checks over verified evidence."""

from dataclasses import dataclass, field
from uuid import NAMESPACE_URL, uuid5

from concord.llm import (
    DisabledLLMProvider,
    LLMProvider,
    NarrationRequest,
    NarrationTask,
)
from concord.orchestration.casefile import (
    ReconciliationCase,
    VerificationRecoveryStage,
    VerifierReport,
)


@dataclass(slots=True)
class SkepticalVerifierAgent:
    """Block unsupported conflicts and proposals without consulting an LLM."""

    llm_provider: LLMProvider = field(default_factory=DisabledLLMProvider)

    def run(self, case: ReconciliationCase) -> VerifierReport:
        concept_id = case.resolved_concept.concept_id if case.resolved_concept else ""
        entity_sets = {frozenset(evaluation.entity_ids) for evaluation in case.execution_results}
        evidence_ids = [item.evidence_id for item in case.evidence]
        evidence_by_binding = {item.binding_id: item for item in case.evidence}
        results_by_binding = {item.binding_id: item for item in case.execution_results}
        binding_ids = {item.binding_id for item in case.binding_semantics}
        result_binding_ids = set(results_by_binding)
        evidence_binding_ids = set(evidence_by_binding)
        proposal_refs = (
            set(case.reconciliation_proposal.evidence_refs)
            if case.reconciliation_proposal
            else set()
        )
        checks: dict[str, bool] = {
            "resolved_concept_is_present": case.resolved_concept is not None,
            "bindings_match_candidate_definitions": (
                bool(case.binding_semantics)
                and {item.definition_id for item in case.binding_semantics}
                == set(case.candidate_definitions)
            ),
            "every_binding_has_one_execution": (
                bool(case.execution_results)
                and len(results_by_binding) == len(case.execution_results)
                and result_binding_ids == binding_ids
            ),
            "evidence_ids_are_unique": (
                bool(evidence_ids) and len(set(evidence_ids)) == len(evidence_ids)
            ),
            "evidence_ids_match_run_and_bindings": (
                bool(case.evidence)
                and all(
                    item.evidence_id
                    == uuid5(
                        NAMESPACE_URL,
                        f"concord-iq:{case.run_id}:{item.binding_id}",
                    )
                    for item in case.evidence
                )
            ),
            "every_result_has_matching_evidence": (
                bool(case.evidence)
                and len(evidence_by_binding) == len(case.evidence)
                and evidence_binding_ids == result_binding_ids
                and all(
                    self._evidence_matches_result(
                        evidence_by_binding[result.binding_id],
                        result,
                    )
                    for result in case.execution_results
                    if result.binding_id in evidence_by_binding
                )
            ),
            "every_result_has_sql_evidence": (
                bool(case.evidence)
                and all(
                    item.sql_text.strip()
                    and item.binding_id in results_by_binding
                    and item.sql_text == results_by_binding[item.binding_id].executed_sql
                    and bool(results_by_binding[item.binding_id].executed_sql.strip())
                    for item in case.evidence
                )
            ),
            "verdict_matches_executed_sets": (
                bool(case.execution_results)
                and (
                    (case.verdict == "conflict" and len(entity_sets) > 1)
                    or (case.verdict == "consistent" and len(entity_sets) == 1)
                )
            ),
            "authority_and_decision_are_consistent": (
                self._authority_and_decision_are_consistent(case)
            ),
            "proposal_cites_required_evidence": (
                case.reconciliation_proposal is None or proposal_refs == set(evidence_ids)
            ),
        }
        self._add_scenario_checks(checks, case, concept_id, entity_sets)
        failures = tuple(name for name, passed in checks.items() if not passed)
        passed = not failures
        recovery_stage = self._recovery_stage(case) if not passed else None
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
                    "recoverable": recovery_stage is not None,
                    "recovery_stage": recovery_stage,
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
            recoverable=recovery_stage is not None,
            recovery_stage=recovery_stage,
            advisory_notes=(narration.text,),
            narration=narration,
        )

    @staticmethod
    def _evidence_matches_result(evidence, result) -> bool:
        return (
            evidence.definition_id == result.definition_id
            and evidence.entity_count == result.entity_count
            and evidence.metric_total == result.metric_total
            and evidence.entity_ids == result.entity_ids
        )

    @staticmethod
    def _authority_and_decision_are_consistent(
        case: ReconciliationCase,
    ) -> bool:
        authority = case.authority_assessment
        if authority is None:
            return False
        if case.verdict == "consistent":
            return (
                case.reconciliation_proposal is None
                and case.refusal_reason is None
                and not case.requires_human_approval
            )
        if case.verdict != "conflict":
            return False
        if authority.status == "clear" and authority.owner:
            proposal = case.reconciliation_proposal
            return (
                proposal is not None
                and case.refusal_reason is None
                and case.requires_human_approval
                and proposal.requires_human_approval
                and proposal.authority_owner == authority.owner
            )
        return (
            authority.status in {"shared", "ambiguous", "missing"}
            and authority.owner is None
            and case.reconciliation_proposal is None
            and bool(case.refusal_reason)
            and case.requires_human_approval
        )

    @staticmethod
    def _recovery_stage(
        case: ReconciliationCase,
    ) -> VerificationRecoveryStage | None:
        """Identify one wholly missing deterministic stage, never corrupt data."""
        if case.binding_semantics and (
            (not case.execution_results and not case.evidence)
            or (case.execution_results and not case.evidence)
        ):
            return "execute_definitions"
        if case.execution_results and case.evidence and case.impact_assessment is None:
            return "rank_impact"
        if case.impact_assessment is not None and (
            case.authority_assessment is None or case.context_packet is None
        ):
            return "resolve_authority"
        if (
            case.authority_assessment is not None
            and case.verdict == "conflict"
            and case.reconciliation_proposal is None
            and case.refusal_reason is None
        ):
            return "reconcile_or_refuse"
        return None

    @staticmethod
    def _add_scenario_checks(
        checks: dict[str, bool],
        case: ReconciliationCase,
        concept_id: str,
        entity_sets: set[frozenset[str]],
    ) -> None:
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
                    "proposal_requires_human_approval": (
                        case.requires_human_approval
                        and case.reconciliation_proposal is not None
                        and case.reconciliation_proposal.requires_human_approval
                    ),
                }
            )
        else:
            checks["scenario_is_supported"] = False
