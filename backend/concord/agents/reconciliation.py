"""Evidence-backed deterministic proposal construction."""

from concord.orchestration.casefile import (
    AuthorityAssessment,
    EvidenceRecord,
    ImpactAssessment,
    ReconciliationProposal,
)
from concord.providers import DefinitionBinding


class ReconciliationAgent:
    """Build a proposal only after deterministic authority resolution."""

    def run(
        self,
        bindings: tuple[DefinitionBinding, ...],
        impact: ImpactAssessment,
        authority: AuthorityAssessment,
        evidence: tuple[EvidenceRecord, ...],
    ) -> ReconciliationProposal:
        if authority.status != "clear" or not authority.owner:
            raise ValueError("A reconciliation proposal requires one clear authority owner.")
        finance = next(binding for binding in bindings if binding.owner == "Finance")
        customer_success = next(
            binding for binding in bindings if binding.owner == "Customer Success"
        )
        canonical_definition = (
            "Active Customer means a customer with an active contract and qualifying "
            "usage in the trailing 30 days. Finance and Sales variants remain named "
            "domain views and must not publish under the unqualified canonical term."
        )
        return ReconciliationProposal(
            canonical_definition=canonical_definition,
            rationale=(
                f"The three executed definitions diverge by "
                f"{impact.customer_count_delta} customers and "
                f"{impact.arr_delta:,.2f} ARR. The proposed canonical definition "
                f"uses the contract and usage semantics from "
                f"{customer_success.name}; {finance.name} remains a governed "
                "financial activity view."
            ),
            migration_notes=(
                "Rename domain-specific dashboard measures before changing the canonical alias.",
                "Publish the canonical definition only after steward approval.",
                "Re-run all three SQL bindings and compare the expected dashboard deltas.",
            ),
            expected_dashboard_impact=(
                f"Up to {impact.customer_count_delta} customers and "
                f"{impact.arr_delta:,.2f} ARR differ across current views."
            ),
            authority_owner=authority.owner,
            requires_human_approval=True,
            evidence_refs=tuple(item.evidence_id for item in evidence),
        )
