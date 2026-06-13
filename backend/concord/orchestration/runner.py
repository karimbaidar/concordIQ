"""Coordinator for deterministic semantic reconciliation scenarios."""

from dataclasses import dataclass, field
from time import perf_counter
from uuid import UUID

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
    AgentTraceStep,
    AuthorityAssessment,
    ConflictHypothesis,
    GovernedCanonical,
    ImpactAssessment,
    ReconciliationCase,
    ReconciliationRequest,
    TimelineEntry,
    VerificationRecoveryStage,
    VerifierReport,
)
from concord.orchestration.context_packet import build_context_packet
from concord.orchestration.state_machine import ReconciliationState
from concord.providers import ConceptResolution, GroundingProvider, LocalProvider
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

    def create_case(self, request: ReconciliationRequest) -> ReconciliationCase:
        """Create the typed blackboard before any specialist executes."""
        started = perf_counter()
        case = ReconciliationCase(request=request)
        self._record_trace(
            case,
            agent_name="CoordinatorAgent",
            input_summary=(
                f"Requested {request.term} for "
                f"{request.period.start_date.isoformat()} to "
                f"{request.period.end_date.isoformat()}."
            ),
            output_summary="Created the typed casefile and specialist workflow plan.",
            started=started,
        )
        return case

    def resolve_concept(self, case: ReconciliationCase) -> ReconciliationCase:
        """Resolve one business term and advance only the concept stage."""
        started = perf_counter()
        concept = ConceptResolverAgent(self.provider).run(case.request.term)
        CoordinatorAgent().require_supported(concept)
        case.resolved_concept = concept
        case.candidate_definitions = concept.definition_ids
        case.transition(
            ReconciliationState.RESOLVE_CONCEPT,
            agent="ConceptResolverAgent",
            summary=(f"Resolved {case.request.term!r} to {concept.canonical_name}."),
        )
        self._record_trace(
            case,
            agent_name="ConceptResolverAgent",
            input_summary=f"Resolve business term {case.request.term!r}.",
            output_summary=(
                f"Resolved {concept.canonical_name} with "
                f"{len(concept.definition_ids)} candidate definitions."
            ),
            started=started,
        )
        return case

    def inspect_bindings(self, case: ReconciliationCase) -> ReconciliationCase:
        """Retrieve and normalize bindings for the resolved concept."""
        started = perf_counter()
        concept = self._resolved_concept(case)
        bindings = BindingInspectorAgent(self.provider).run(concept.concept_id)
        canonical = self.repository.get_canonical_definition(concept.canonical_name)
        if canonical is not None and isinstance(self.provider, LocalProvider):
            canonical_binding, domain_views = self.provider.get_canonical_binding(
                concept.concept_id,
                source_definition_id=canonical.source_definition_id,
                rule_text=canonical.rule_text,
                version=canonical.version,
                approved_by=canonical.approved_by,
            )
            bindings = (canonical_binding,)
            case.candidate_definitions = (canonical.source_definition_id,)
            case.governed_canonical = GovernedCanonical(
                canonical_definition_id=canonical.canonical_definition_id,
                version=canonical.version,
                rule_text=canonical.rule_text,
                source_definition_id=canonical.source_definition_id,
                approved_by=canonical.approved_by,
                approved_at=canonical.approved_at,
                approving_run_id=canonical.approving_run_id,
                domain_views=domain_views,
            )
        case.binding_semantics = bindings
        case.transition(
            ReconciliationState.INSPECT_BINDINGS,
            agent="BindingInspectorAgent",
            summary=(
                f"Selected governed canonical v{case.governed_canonical.version} "
                "and retained named domain views."
                if case.governed_canonical
                else f"Normalized {len(bindings)} operational definitions."
            ),
        )
        self._record_trace(
            case,
            agent_name="BindingInspectorAgent",
            input_summary=f"Inspect bindings for concept {concept.concept_id}.",
            output_summary=(
                (
                    f"Selected Canonical v{case.governed_canonical.version}, approved by "
                    f"{case.governed_canonical.approved_by}; retained "
                    f"{len(case.governed_canonical.domain_views)} named domain views."
                )
                if case.governed_canonical
                else (
                    f"Normalized {len(bindings)} bindings owned by "
                    f"{', '.join(binding.owner for binding in bindings)}."
                )
            ),
            started=started,
        )
        return case

    def hypothesize_conflicts(self, case: ReconciliationCase) -> ReconciliationCase:
        """Create pairwise hypotheses without deciding the final verdict."""
        started = perf_counter()
        hypotheses = ConflictHypothesisAgent().run(case.binding_semantics)
        case.conflict_hypotheses = hypotheses
        case.transition(
            ReconciliationState.HYPOTHESIZE_CONFLICTS,
            agent="ConflictHypothesisAgent",
            summary=f"Generated {len(hypotheses)} pairwise hypotheses for execution.",
        )
        self._record_trace(
            case,
            agent_name="ConflictHypothesisAgent",
            input_summary=f"Compare {len(case.binding_semantics)} normalized bindings.",
            output_summary=f"Generated {len(hypotheses)} execution-testable hypotheses.",
            deliberations=hypotheses,
            started=started,
        )
        return case

    def execute_definitions(self, case: ReconciliationCase) -> ReconciliationCase:
        """Execute every binding and settle conflict versus equivalence."""
        started = perf_counter()
        execution = DataExecutionAgent(self.provider).run(
            str(case.run_id),
            case.binding_semantics,
            case.request.period,
            case.conflict_hypotheses,
        )
        case.execution_results = execution.evaluations
        case.evidence = execution.evidence
        case.conflict_hypotheses = execution.hypotheses
        case.verdict = execution.verdict
        self._settle_deliberation_trace(case)
        case.transition(
            ReconciliationState.EXECUTE_DEFINITIONS,
            agent="DataExecutionAgent",
            summary=(
                "Executed all definitions and found divergent entity sets."
                if execution.verdict == "conflict"
                else "Executed all definitions and found equal entity sets."
            ),
        )
        counts = "/".join(str(result.entity_count) for result in execution.evaluations)
        confirmed = sum(
            hypothesis.data_verdict == "confirmed" for hypothesis in execution.hypotheses
        )
        overturned = sum(
            hypothesis.data_verdict == "overturned" for hypothesis in execution.hypotheses
        )
        self._record_trace(
            case,
            agent_name="DataExecutionAgent",
            input_summary=(
                f"Execute {len(case.binding_semantics)} trusted bindings for the requested period."
            ),
            output_summary=(
                f"Settled verdict as {execution.verdict} with entity counts {counts}; "
                f"data confirmed {confirmed} claims and overturned {overturned}."
            ),
            evidence_ids=tuple(item.evidence_id for item in execution.evidence),
            started=started,
        )
        return case

    def rank_impact(self, case: ReconciliationCase) -> ReconciliationCase:
        """Compute deterministic materiality from executed definition results."""
        started = perf_counter()
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
                f"{impact.customer_count_delta} {impact.entity_label} of population delta."
            ),
        )
        self._record_trace(
            case,
            agent_name="ImpactRankerAgent",
            input_summary=(
                f"Rank materiality from {len(case.execution_results)} executed populations."
            ),
            output_summary=(
                f"Ranked {impact.severity} impact: {impact.customer_count_delta} "
                f"{impact.entity_label} and {impact.arr_delta:,.0f} {impact.value_label}."
            ),
            evidence_ids=self._evidence_ids(case),
            started=started,
        )
        return case

    def resolve_authority(self, case: ReconciliationCase) -> ReconciliationCase:
        """Resolve governance rules and build the compact context packet."""
        started = perf_counter()
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
        self._record_trace(
            case,
            agent_name="AuthorityResolverAgent",
            input_summary=(
                f"Resolve configured authority for {concept.concept_id} and its dimensions."
            ),
            output_summary=(
                f"Authority is {authority.status}; owner is "
                f"{authority.owner or 'not uniquely assigned'}."
            ),
            started=started,
        )
        return case

    def reconcile_or_refuse(self, case: ReconciliationCase) -> ReconciliationCase:
        """Create a governed proposal, refusal, or no-action decision."""
        started = perf_counter()
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
        self._record_trace(
            case,
            agent_name="ReconciliationAgent",
            input_summary=(f"Apply verdict {case.verdict} under {authority.status} authority."),
            output_summary=decision_summaries[decision.action],
            evidence_ids=self._evidence_ids(case),
            started=started,
        )
        return case

    def verify(self, case: ReconciliationCase) -> ReconciliationCase:
        """Run the stable fast-mode verifier and raise on blocking failure."""
        started = perf_counter()
        report = self._evaluate_verifier(case, attempt=1)
        self._finalize_verification(case, report)
        self._record_verifier_trace(case, report, started=started)
        if not report.passed:
            case.verification_status = "blocked"
            case.verdict = "incomplete"
            raise VerificationFailed(", ".join(report.failures))
        return case

    def verify_strict(self, case: ReconciliationCase) -> ReconciliationCase:
        """Verify, retry one missing stage once, then return a safe status."""
        started = perf_counter()
        report = self._evaluate_verifier(case, attempt=1)
        if not report.passed and report.recoverable and report.recovery_stage:
            case.verification_recovery = report.recovery_stage
            self._recover_missing_stage(case, report.recovery_stage)
            report = self._evaluate_verifier(case, attempt=2)
        self._finalize_verification(case, report)
        if not report.passed:
            case.verification_status = "needs_review" if case.verification_recovery else "blocked"
            case.verdict = "incomplete"
        self._record_verifier_trace(case, report, started=started)
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
            self._record_trace(
                case,
                agent_name="AuditAgent",
                input_summary=(f"Finalize a case with verifier status {case.verification_status}."),
                output_summary=(
                    "Skipped complete persistence because deterministic verification "
                    f"ended {case.verification_status}."
                ),
                evidence_ids=self._evidence_ids(case),
                verifier_status=case.verification_status,
                started=None,
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
        self._record_trace(
            case,
            agent_name="AuditAgent",
            input_summary=(
                f"Persist verifier-approved {concept.canonical_name} evidence and decisions."
            ),
            output_summary=(
                f"Prepared {len(case.evidence)} evidence records and the complete audit artifact."
            ),
            evidence_ids=self._evidence_ids(case),
            verifier_status=case.verification_status,
            started=None,
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
                case.conflict_hypotheses,
            )
            case.execution_results = execution.evaluations
            case.evidence = execution.evidence
            case.conflict_hypotheses = execution.hypotheses
            case.verdict = execution.verdict
            self._settle_deliberation_trace(case)
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

    def _record_verifier_trace(
        self,
        case: ReconciliationCase,
        report: VerifierReport,
        *,
        started: float,
    ) -> None:
        recovery = (
            f" after one {case.verification_recovery} recovery"
            if case.verification_recovery
            else ""
        )
        output = (
            f"Passed {len(report.checks)} deterministic checks{recovery}."
            if report.passed
            else f"Ended {case.verification_status}{recovery}: {', '.join(report.failures)}."
        )
        self._record_trace(
            case,
            agent_name="SkepticalVerifierAgent",
            input_summary=(
                f"Verify {len(case.evidence)} evidence records and the governed decision."
            ),
            output_summary=output,
            evidence_ids=self._evidence_ids(case),
            verifier_status=case.verification_status,
            started=started,
        )

    def _record_trace(
        self,
        case: ReconciliationCase,
        *,
        agent_name: str,
        input_summary: str,
        output_summary: str,
        evidence_ids: tuple[UUID, ...] = (),
        deliberations: tuple[ConflictHypothesis, ...] = (),
        verifier_status: str | None = None,
        started: float | None,
    ) -> None:
        duration_ms = None
        if started is not None:
            duration_ms = round(max(0.0, (perf_counter() - started) * 1000), 3)
        case.agent_trace = (
            *case.agent_trace,
            AgentTraceStep(
                step_number=len(case.agent_trace) + 1,
                agent_name=agent_name,
                input_summary=input_summary,
                output_summary=output_summary,
                evidence_ids=evidence_ids,
                deliberations=deliberations,
                provider_mode=self.provider.mode.value,
                verifier_status=verifier_status,
                duration_ms=duration_ms,
            ),
        )

    @staticmethod
    def _settle_deliberation_trace(case: ReconciliationCase) -> None:
        evidence_ids = tuple(item.evidence_id for item in case.evidence)
        case.agent_trace = tuple(
            step.model_copy(
                update={
                    "deliberations": case.conflict_hypotheses,
                    "evidence_ids": evidence_ids,
                    "output_summary": (
                        f"Raised {len(case.conflict_hypotheses)} claims; deterministic "
                        "execution recorded the final data rulings."
                    ),
                }
            )
            if step.agent_name == "ConflictHypothesisAgent"
            else step
            for step in case.agent_trace
        )

    @staticmethod
    def _evidence_ids(case: ReconciliationCase) -> tuple[UUID, ...]:
        return tuple(item.evidence_id for item in case.evidence)
