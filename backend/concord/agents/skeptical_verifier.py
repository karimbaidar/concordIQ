"""Deterministic blocking checks over verified evidence."""

from concord.orchestration.casefile import ReconciliationCase, VerifierReport


class SkepticalVerifierAgent:
    """Block unsupported conflicts and proposals without consulting an LLM."""

    def run(self, case: ReconciliationCase) -> VerifierReport:
        entity_sets = {evaluation.entity_ids for evaluation in case.execution_results}
        evidence_ids = {item.evidence_id for item in case.evidence}
        proposal_refs = (
            set(case.reconciliation_proposal.evidence_refs)
            if case.reconciliation_proposal
            else set()
        )
        checks = {
            "three_definitions_executed": len(case.execution_results) == 3,
            "conflict_has_divergent_sets": (case.verdict == "conflict" and len(entity_sets) > 1),
            "every_result_has_sql_evidence": (
                len(case.evidence) == len(case.execution_results)
                and all(item.sql_text.strip() for item in case.evidence)
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
        }
        failures = tuple(name for name, passed in checks.items() if not passed)
        return VerifierReport(
            passed=not failures,
            checks=checks,
            failures=failures,
            advisory_notes=(
                "LLM critique is disabled; blocking checks use structured evidence only.",
            ),
        )
