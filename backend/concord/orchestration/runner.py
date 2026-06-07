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
from concord.llm import DisabledLLMProvider, LLMProvider
from concord.orchestration.casefile import (
    AuthorityAssessment,
    ImpactAssessment,
    ReconciliationCase,
    ReconciliationRequest,
    TimelineEntry,
    VerificationRecoveryStage,
    VerifierReport,
)
from concord.orchestration.context_packet import build_context_packet
from concord.orchestration.state_machine import ReconciliationState
from concord.providers import ConceptResolution, GroundingProvider
from concord.storage.repositories import ReconciliationRepository


class VerificationFailed(RuntimeError):
    """Raised when deterministic blocking checks reject a case."""


@dataclass(slots=True)
class ReconciliationRunner:
    """Expose deterministic reconciliation as composable specialist stages."""

    provider: GroundingProvider
    repository: ReconciliationRepository
    settings: Settings = field(default_factory=Settings)
    llm_provider: LLMProvider = field(default_factory=DisabledLLMProvider)

    def __post_init__(self) -> None:
        if self.provider.uses_cloud:
            self.settings.require_cloud_access(self.provider.name)

    @staticmethod
    def create_case(request: ReconciliationRequest) -> ReconciliationCase:
        """Create the typed blackboard before any specialist executes."""
        return ReconciliationCase(request=request)

    def resolve_concept(self, case: ReconciliationCase) -> ReconciliationCase:
        """Resolve one business term and advance only the concept stage."""
        concept = ConceptResolverAgent(self.provider).run(case.request.term)
        CoordinatorAgent().require_supported(concept)
        case.resolved_concept = concept
        case.candidate_definitions = concept.definition_ids
        case.transition(
            ReconciliationState.RESOLVE_CONCEPT,
            agent="ConceptResolverAgent",
            summary=(f"Resolved {case.request.term!r} to {concept.canonical_name}."),
        )
        return case

    def inspect_bindings(self, case: ReconciliationCase) -> ReconciliationCase:
        """Retrieve and normalize bindings for the resolved concept."""
        concept = self._resolved_concept(case)
        bindings = BindingInspectorAgent(self.provider).run(concept.concept_id)
        case.binding_semantics = bindings
        case.transition(
            ReconciliationState.INSPECT_BINDINGS,
            agent="BindingInspectorAgent",
            summary=f"Normalized {len(bindings)} operational definitions.",
        )
        return case

    def hypothesize_conflicts(self, case: ReconciliationCase) -> ReconciliationCase:
        """Create pairwise hypotheses without deciding the final verdict."""
        hypotheses = ConflictHypothesisAgent().run(case.binding_semantics)
        case.conflict_hypotheses = hypotheses
        case.transition(
            ReconciliationState.HYPOTHESIZE_CONFLICTS,
            agent="ConflictHypothesisAgent",
            summary=f"Generated {len(hypotheses)} pairwise hypotheses for execution.",
        )
        return case

    def execute_definitions(self, case: ReconciliationCase) -> ReconciliationCase:
        """Execute every binding and settle conflict versus equivalence."""
        execution = DataExecutionAgent(self.provider).run(
            str(case.run_id),
            case.binding_semantics,
            case.request.period,
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
        return case

    def rank_impact(self, case: ReconciliationCase) -> ReconciliationCase:
        """Compute deterministic materiality from executed definition results."""
        impact = ImpactRankerAgent().run(
            case.binding_semantics,
            case.execution_results,
        )
        case.impact_assessment = impact
        case.transition(
            ReconciliationState.RANK_IMPACT,
            agent="ImpactRankerAgent",
            summary=(
                f"Ranked impact {impact.severity} with "
                f"{impact.customer_count_delta} customers of population delta."
            ),
        )
        return case

    def resolve_authority(self, case: ReconciliationCase) -> ReconciliationCase:
        """Resolve governance rules and build the compact context packet."""
        concept = self._resolved_concept(case)
        authority = AuthorityResolverAgent(self.provider).run(concept.concept_id)
        case.authority_assessment = authority
        subgraph = self.provider.get_subgraph(concept.concept_id)
        case.context_packet = build_context_packet(
            case.request.question,
            self.provider,
            concept,
            list(case.binding_semantics),
            subgraph,
            list(authority.rules),
        )
        case.transition(
            ReconciliationState.RESOLVE_AUTHORITY,
            agent="AuthorityResolverAgent",
            summary=f"Authority is {authority.status}: {authority.owner or 'no owner'}.",
        )
        return case

    def reconcile_or_refuse(self, case: ReconciliationCase) -> ReconciliationCase:
        """Create a governed proposal, refusal, or no-action decision."""
        concept = self._resolved_concept(case)
        impact = self._impact_assessment(case)
        authority = self._authority_assessment(case)
        decision = ReconciliationAgent(self.llm_provider).run(
            concept.concept_id,
            case.verdict,
            case.binding_semantics,
            impact,
            authority,
            case.evidence,
        )
        case.reconciliation_proposal = decision.proposal
        case.refusal_reason = decision.refusal_reason
        case.requires_human_approval = decision.requires_human_approval
        if decision.narration:
            case.narrations = (*case.narrations, decision.narration)
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
        return case

    def verify(self, case: ReconciliationCase) -> ReconciliationCase:
        """Run the stable fast-mode verifier and raise on blocking failure."""
        report = self._evaluate_verifier(case, attempt=1)
        self._finalize_verification(case, report)
        if not report.passed:
            case.verification_status = "blocked"
            case.verdict = "incomplete"
            raise VerificationFailed(", ".join(report.failures))
        return case

    def verify_strict(self, case: ReconciliationCase) -> ReconciliationCase:
        """Verify, retry one missing stage once, then return a safe status."""
        report = self._evaluate_verifier(case, attempt=1)
        if not report.passed and report.recoverable and report.recovery_stage:
            case.verification_recovery = report.recovery_stage
            self._recover_missing_stage(case, report.recovery_stage)
            report = self._evaluate_verifier(case, attempt=2)
        self._finalize_verification(case, report)
        if not report.passed:
            case.verification_status = "needs_review" if case.verification_recovery else "blocked"
            case.verdict = "incomplete"
        return case

    def audit(self, case: ReconciliationCase) -> ReconciliationCase:
        """Finalize the timeline and persist one verifier-approved case."""
        if not case.verifier_report or not case.verifier_report.passed:
            case.audit_log = (
                *case.audit_log,
                TimelineEntry(
                    sequence=len(case.audit_log) + 1,
                    state=case.state,
                    agent="AuditAgent",
                    summary=(
                        "Skipped complete persistence because deterministic "
                        f"verification ended {case.verification_status}."
                    ),
                    status="failed",
                ),
            )
            return case
        concept = self._resolved_concept(case)
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
        AuditAgent(self.repository, self.llm_provider).run(case)
        return case

    def run(self, request: ReconciliationRequest) -> ReconciliationCase:
        """Run the stable fast path through the same deterministic stages."""
        case = self.create_case(request)
        self.resolve_concept(case)
        self.inspect_bindings(case)
        self.hypothesize_conflicts(case)
        self.execute_definitions(case)
        self.rank_impact(case)
        self.resolve_authority(case)
        self.reconcile_or_refuse(case)
        self.verify(case)
        return self.audit(case)

    @staticmethod
    def _resolved_concept(case: ReconciliationCase) -> ConceptResolution:
        if case.resolved_concept is None:
            raise ValueError("The concept resolution stage must complete first.")
        return case.resolved_concept

    @staticmethod
    def _impact_assessment(case: ReconciliationCase) -> ImpactAssessment:
        if case.impact_assessment is None:
            raise ValueError("The impact ranking stage must complete first.")
        return case.impact_assessment

    @staticmethod
    def _authority_assessment(case: ReconciliationCase) -> AuthorityAssessment:
        if case.authority_assessment is None:
            raise ValueError("The authority resolution stage must complete first.")
        return case.authority_assessment

    def _evaluate_verifier(
        self,
        case: ReconciliationCase,
        *,
        attempt: int,
    ) -> VerifierReport:
        report = SkepticalVerifierAgent(self.llm_provider).run(case)
        return report.model_copy(update={"attempt": attempt})

    @staticmethod
    def _finalize_verification(
        case: ReconciliationCase,
        report: VerifierReport,
    ) -> None:
        case.verifier_report = report
        case.verifier_attempts = report.attempt
        case.verification_status = "passed" if report.passed else "blocked"
        if report.narration:
            case.narrations = (*case.narrations, report.narration)
        recovery_note = (
            f" after retrying {case.verification_recovery}" if case.verification_recovery else ""
        )
        case.transition(
            ReconciliationState.VERIFY,
            agent="SkepticalVerifierAgent",
            summary=(
                f"All deterministic blocking checks passed{recovery_note}."
                if report.passed
                else (f"Blocking checks failed{recovery_note}: {', '.join(report.failures)}.")
            ),
        )

    def _recover_missing_stage(
        self,
        case: ReconciliationCase,
        stage: VerificationRecoveryStage,
    ) -> None:
        """Recompute one wholly missing output from source; never patch evidence."""
        if stage == "execute_definitions":
            execution = DataExecutionAgent(self.provider).run(
                str(case.run_id),
                case.binding_semantics,
                case.request.period,
            )
            case.execution_results = execution.evaluations
            case.evidence = execution.evidence
            case.verdict = execution.verdict
            return
        if stage == "rank_impact":
            case.impact_assessment = ImpactRankerAgent().run(
                case.binding_semantics,
                case.execution_results,
            )
            return
        if stage == "resolve_authority":
            concept = self._resolved_concept(case)
            authority = AuthorityResolverAgent(self.provider).run(concept.concept_id)
            case.authority_assessment = authority
            case.context_packet = build_context_packet(
                case.request.question,
                self.provider,
                concept,
                list(case.binding_semantics),
                self.provider.get_subgraph(concept.concept_id),
                list(authority.rules),
            )
            return
        if stage == "reconcile_or_refuse":
            concept = self._resolved_concept(case)
            decision = ReconciliationAgent(self.llm_provider).run(
                concept.concept_id,
                case.verdict,
                case.binding_semantics,
                self._impact_assessment(case),
                self._authority_assessment(case),
                case.evidence,
            )
            case.reconciliation_proposal = decision.proposal
            case.refusal_reason = decision.refusal_reason
            case.requires_human_approval = decision.requires_human_approval
            if decision.narration:
                case.narrations = (*case.narrations, decision.narration)
            return
        raise ValueError(f"Unsupported verifier recovery stage: {stage}")
