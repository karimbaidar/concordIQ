"""Evidence-backed deterministic proposal construction."""

from dataclasses import dataclass, field

from concord.llm import (
    DisabledLLMProvider,
    LLMProvider,
    NarrationRequest,
    NarrationResult,
    NarrationTask,
)
from concord.orchestration.casefile import (
    AuthorityAssessment,
    EvidenceRecord,
    ImpactAssessment,
    ReconciliationDecision,
    ReconciliationProposal,
)
from concord.providers import DefinitionBinding


@dataclass(slots=True)
class ReconciliationAgent:
    """Choose proposal, refusal, or no action from verified deterministic inputs."""

    llm_provider: LLMProvider = field(default_factory=DisabledLLMProvider)

    def run(
        self,
        concept_id: str,
        verdict: str,
        bindings: tuple[DefinitionBinding, ...],
        impact: ImpactAssessment,
        authority: AuthorityAssessment,
        evidence: tuple[EvidenceRecord, ...],
    ) -> ReconciliationDecision:
        if verdict == "consistent":
            decision = ReconciliationDecision(action="no_action")
            return decision.model_copy(
                update={
                    "narration": self._narrate(
                        decision,
                        concept_id=concept_id,
                        verdict=verdict,
                        impact=impact,
                        authority=authority,
                        evidence=evidence,
                    )
                }
            )
        if authority.status != "clear" or not authority.owner:
            dimensions = ", ".join(rule.semantic_dimension for rule in authority.rules)
            decision = ReconciliationDecision(
                action="refuse",
                refusal_reason=(
                    "Automatic reconciliation refused because configured authority is "
                    f"{authority.status} for {dimensions}. No single owner can approve "
                    "a canonical definition; human approval is required."
                ),
                requires_human_approval=True,
            )
            return decision.model_copy(
                update={
                    "narration": self._narrate(
                        decision,
                        concept_id=concept_id,
                        verdict=verdict,
                        impact=impact,
                        authority=authority,
                        evidence=evidence,
                    )
                }
            )
        if concept_id == "active_customer":
            proposal = self._active_customer_proposal(bindings, impact, authority, evidence)
        else:
            proposal = self._generic_proposal(concept_id, bindings, impact, authority, evidence)
        decision = ReconciliationDecision(
            action="propose",
            proposal=proposal,
            requires_human_approval=True,
        )
        return decision.model_copy(
            update={
                "narration": self._narrate(
                    decision,
                    concept_id=concept_id,
                    verdict=verdict,
                    impact=impact,
                    authority=authority,
                    evidence=evidence,
                )
            }
        )

    @staticmethod
    def _active_customer_proposal(
        bindings: tuple[DefinitionBinding, ...],
        impact: ImpactAssessment,
        authority: AuthorityAssessment,
        evidence: tuple[EvidenceRecord, ...],
    ) -> ReconciliationProposal:
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
            authority_owner=authority.owner or "",
            requires_human_approval=True,
            evidence_refs=tuple(item.evidence_id for item in evidence),
            canonical_source_definition_id=customer_success.definition_id,
        )

    @staticmethod
    def _generic_proposal(
        concept_id: str,
        bindings: tuple[DefinitionBinding, ...],
        impact: ImpactAssessment,
        authority: AuthorityAssessment,
        evidence: tuple[EvidenceRecord, ...],
    ) -> ReconciliationProposal:
        """Build an evidence-backed proposal for any clear-authority conflict.

        The most conservative (smallest-population) definition becomes the
        canonical anchor; every other variant is named as a governed domain view.
        Selection is deterministic and never decided by the LLM.
        """
        counts = {item.binding_id: item.entity_count for item in evidence}
        anchor = min(
            bindings,
            key=lambda binding: (counts.get(binding.binding_id, 0), binding.binding_id),
        )
        variants = tuple(binding for binding in bindings if binding.binding_id != anchor.binding_id)
        concept_label = concept_id.replace("_", " ").title()
        variant_names = ", ".join(binding.name for binding in variants) or "no other variant"
        return ReconciliationProposal(
            canonical_definition=(
                f"{concept_label} is canonically defined as: {anchor.rule_text} "
                f"Other variants ({variant_names}) remain named domain views and "
                "must not publish under the unqualified canonical term."
            ),
            rationale=(
                f"The {len(bindings)} executed definitions diverge by "
                f"{impact.customer_count_delta} entities and {impact.arr_delta:,.2f} "
                f"in value. {authority.owner} governs this term and can approve the "
                f"canonical definition anchored on {anchor.name}."
            ),
            migration_notes=(
                "Rename domain-specific dashboard measures before changing the canonical alias.",
                f"Publish the canonical definition only after {authority.owner} approval.",
                "Re-run every SQL binding and compare the expected dashboard deltas.",
            ),
            expected_dashboard_impact=(
                f"Up to {impact.customer_count_delta} entities and "
                f"{impact.arr_delta:,.2f} in value differ across current views."
            ),
            authority_owner=authority.owner or "",
            requires_human_approval=True,
            evidence_refs=tuple(item.evidence_id for item in evidence),
            canonical_source_definition_id=anchor.definition_id,
        )

    def _narrate(
        self,
        decision: ReconciliationDecision,
        *,
        concept_id: str,
        verdict: str,
        impact: ImpactAssessment,
        authority: AuthorityAssessment,
        evidence: tuple[EvidenceRecord, ...],
    ) -> NarrationResult:
        fallbacks = {
            "propose": (
                "The executed definitions materially diverge. Configured authority "
                "supports a draft canonical definition, but human approval is required."
            ),
            "refuse": (
                "The executed definitions diverge, but no single configured authority "
                "can approve a canonical definition. Concord IQ routes the decision to people."
            ),
            "no_action": (
                "The definitions use different wording but return the same result set "
                "for the evaluated period, so no reconciliation is proposed."
            ),
        }
        return self.llm_provider.narrate(
            NarrationRequest(
                task=NarrationTask.DECISION,
                facts={
                    "concept_id": concept_id,
                    "verdict": verdict,
                    "decision_action": decision.action,
                    "customer_count_delta": impact.customer_count_delta,
                    "metric_delta": impact.arr_delta,
                    "authority_status": authority.status,
                    "authority_owner": authority.owner,
                    "requires_human_approval": decision.requires_human_approval,
                    "evidence_count": len(evidence),
                },
                fallback_text=fallbacks[decision.action],
            )
        )
