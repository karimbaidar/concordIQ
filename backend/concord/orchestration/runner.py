"""Coordinator for deterministic semantic reconciliation scenarios."""

from dataclasses import dataclass, field

from concord.agents import (
    AuditAgent,
    AuthorityResolverAgent,
    BindingInspectorAgent,
    ConceptResolverAgent,
    ConflictHypothesisAgent,
    CoordinatorAgent,
    DataExecutionAgent,
    ImpactRankerAgent,
    ReconciliationAgent,
    SkepticalVerifierAgent,
)
from concord.config import Settings
from concord.orchestration.casefile import ReconciliationCase, ReconciliationRequest
from concord.orchestration.context_packet import build_context_packet
from concord.orchestration.state_machine import ReconciliationState
from concord.providers import GroundingProvider
from concord.storage.repositories import ReconciliationRepository


class VerificationFailed(RuntimeError):
    """Raised when deterministic blocking checks reject a case."""


@dataclass(slots=True)
class ReconciliationRunner:
    """Drive specialist agents through the typed reconciliation state machine."""

    provider: GroundingProvider
    repository: ReconciliationRepository
    settings: Settings = field(default_factory=Settings)

    def __post_init__(self) -> None:
        if self.provider.uses_cloud:
            self.settings.require_cloud_access(self.provider.name)

    def run(self, request: ReconciliationRequest) -> ReconciliationCase:
        case = ReconciliationCase(request=request)

        concept = ConceptResolverAgent(self.provider).run(request.term)
        CoordinatorAgent().require_supported(concept)
        case.resolved_concept = concept
        case.candidate_definitions = concept.definition_ids
        case.transition(
            ReconciliationState.RESOLVE_CONCEPT,
            agent="ConceptResolverAgent",
            summary=f"Resolved {request.term!r} to {concept.canonical_name}.",
        )

        bindings = BindingInspectorAgent(self.provider).run(concept.concept_id)
        case.binding_semantics = bindings
        case.transition(
            ReconciliationState.INSPECT_BINDINGS,
            agent="BindingInspectorAgent",
            summary=f"Normalized {len(bindings)} operational definitions.",
        )

        hypotheses = ConflictHypothesisAgent().run(bindings)
        case.conflict_hypotheses = hypotheses
        case.transition(
            ReconciliationState.HYPOTHESIZE_CONFLICTS,
            agent="ConflictHypothesisAgent",
            summary=f"Generated {len(hypotheses)} pairwise hypotheses for execution.",
        )

        execution = DataExecutionAgent(self.provider).run(
            str(case.run_id),
            bindings,
            request.period,
        )
        case.execution_results = execution.evaluations
        case.evidence = execution.evidence
        case.verdict = execution.verdict
        case.transition(
            ReconciliationState.EXECUTE_DEFINITIONS,
            agent="DataExecutionAgent",
            summary=(
                "Executed all definitions and found divergent entity sets."
                if execution.verdict == "conflict"
                else "Executed all definitions and found equal entity sets."
            ),
        )

        impact = ImpactRankerAgent().run(bindings, execution.evaluations)
        case.impact_assessment = impact
        case.transition(
            ReconciliationState.RANK_IMPACT,
            agent="ImpactRankerAgent",
            summary=(
                f"Ranked impact {impact.severity} with "
                f"{impact.customer_count_delta} customers of population delta."
            ),
        )

        authority = AuthorityResolverAgent(self.provider).run(concept.concept_id)
        case.authority_assessment = authority
        subgraph = self.provider.get_subgraph(concept.concept_id)
        case.context_packet = build_context_packet(
            request.question,
            self.provider,
            concept,
            list(bindings),
            subgraph,
            list(authority.rules),
        )
        case.transition(
            ReconciliationState.RESOLVE_AUTHORITY,
            agent="AuthorityResolverAgent",
            summary=f"Authority is {authority.status}: {authority.owner or 'no owner'}.",
        )

        decision = ReconciliationAgent().run(
            concept.concept_id,
            execution.verdict,
            bindings,
            impact,
            authority,
            execution.evidence,
        )
        case.reconciliation_proposal = decision.proposal
        case.refusal_reason = decision.refusal_reason
        case.requires_human_approval = decision.requires_human_approval
        decision_summaries = {
            "propose": "Created a draft canonical definition with human approval required.",
            "refuse": "Refused automatic reconciliation and routed it to human approval.",
            "no_action": "Ruled out the decoy by result-set equality; no reconciliation needed.",
        }
        case.transition(
            ReconciliationState.PROPOSE_OR_REFUSE,
            agent="ReconciliationAgent",
            summary=decision_summaries[decision.action],
        )

        verifier = SkepticalVerifierAgent().run(case)
        case.verifier_report = verifier
        case.transition(
            ReconciliationState.VERIFY,
            agent="SkepticalVerifierAgent",
            summary=(
                "All deterministic blocking checks passed."
                if verifier.passed
                else f"Blocking checks failed: {', '.join(verifier.failures)}."
            ),
        )
        if not verifier.passed:
            case.verdict = "incomplete"
            raise VerificationFailed(", ".join(verifier.failures))

        case.transition(
            ReconciliationState.AUDIT,
            agent="AuditAgent",
            summary="Prepared run, finding, evidence, decision, and timeline for persistence.",
        )
        case.transition(
            ReconciliationState.COMPLETE,
            agent="CoordinatorAgent",
            summary=f"Completed the verified {concept.canonical_name} reconciliation.",
        )
        AuditAgent(self.repository).run(case)
        return case
