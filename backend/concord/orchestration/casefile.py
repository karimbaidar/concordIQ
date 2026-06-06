"""Typed blackboard shared by the deterministic reconciliation agents."""

from datetime import date
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from concord.llm import NarrationResult
from concord.orchestration.state_machine import (
    ReconciliationState,
    require_transition,
)
from concord.providers import (
    AuthorityRule,
    ConceptResolution,
    DefinitionBinding,
    DefinitionEvaluation,
    EvaluationPeriod,
)


class CaseModel(BaseModel):
    """Mutable typed model used while the state machine advances."""

    model_config = ConfigDict(validate_assignment=True)


class ReconciliationRequest(CaseModel):
    """A deterministic reconciliation request."""

    question: str
    term: str = "Active Customer"
    period: EvaluationPeriod = Field(
        default_factory=lambda: EvaluationPeriod(
            start_date=date(2026, 3, 4),
            end_date=date(2026, 6, 1),
        )
    )


class ContextPacket(CaseModel):
    """Small, relevant context passed to the specialist agents."""

    user_question: str
    resolved_term: str
    ontology_node_ids: tuple[str, ...]
    candidate_definition_ids: tuple[str, ...]
    authority_rule_dimensions: tuple[str, ...]
    business_units: tuple[str, ...]
    analytical_tables: tuple[str, ...]
    provider_metadata: dict[str, Any]
    active_scenario: str
    prohibited_assumptions: tuple[str, ...]
    uncertainty_notes: tuple[str, ...]


class TimelineEntry(CaseModel):
    """One visible deterministic state transition."""

    sequence: int
    state: ReconciliationState
    agent: str
    summary: str
    status: Literal["completed", "failed"] = "completed"


class ConflictHypothesis(CaseModel):
    """A possible semantic conflict to be settled by execution."""

    left_binding_id: str
    right_binding_id: str
    differing_dimensions: tuple[str, ...]
    rationale: str


class ImpactAssessment(CaseModel):
    """Materiality calculated from executed populations and ARR values."""

    rank: int
    severity: Literal["low", "medium", "high"]
    customer_count_delta: int
    arr_delta: float
    reports_affected: int
    business_units_affected: tuple[str, ...]
    decision_criticality: Literal["low", "medium", "high"]


class AuthorityAssessment(CaseModel):
    """Deterministic authority result from configured rules."""

    status: Literal["clear", "shared", "ambiguous", "missing"]
    owner: str | None
    rules: tuple[AuthorityRule, ...]
    rationale: str


class EvidenceRecord(CaseModel):
    """Persistable data evidence with exact executed SQL."""

    evidence_id: UUID
    binding_id: str
    definition_id: str
    source_ref: str
    entity_count: int
    metric_total: float
    entity_ids: tuple[str, ...]
    sql_text: str


class ReconciliationProposal(CaseModel):
    """Governed proposal grounded in evidence and configured authority."""

    canonical_definition: str
    rationale: str
    migration_notes: tuple[str, ...]
    expected_dashboard_impact: str
    authority_owner: str
    requires_human_approval: bool = True
    evidence_refs: tuple[UUID, ...]


class ReconciliationDecision(CaseModel):
    """Typed proposal, refusal, or no-action decision."""

    action: Literal["propose", "refuse", "no_action"]
    proposal: ReconciliationProposal | None = None
    refusal_reason: str | None = None
    requires_human_approval: bool = False
    narration: NarrationResult | None = None


class VerifierReport(CaseModel):
    """Blocking deterministic checks over the completed casefile."""

    passed: bool
    checks: dict[str, bool]
    failures: tuple[str, ...] = ()
    advisory_notes: tuple[str, ...] = ()
    narration: NarrationResult | None = None


class ReconciliationCase(CaseModel):
    """The persisted blackboard for one reconciliation run."""

    run_id: UUID = Field(default_factory=uuid4)
    request: ReconciliationRequest
    state: ReconciliationState = ReconciliationState.START
    context_packet: ContextPacket | None = None
    resolved_concept: ConceptResolution | None = None
    candidate_definitions: tuple[str, ...] = ()
    binding_semantics: tuple[DefinitionBinding, ...] = ()
    conflict_hypotheses: tuple[ConflictHypothesis, ...] = ()
    execution_results: tuple[DefinitionEvaluation, ...] = ()
    verdict: Literal["conflict", "consistent", "incomplete"] = "incomplete"
    impact_assessment: ImpactAssessment | None = None
    authority_assessment: AuthorityAssessment | None = None
    reconciliation_proposal: ReconciliationProposal | None = None
    refusal_reason: str | None = None
    requires_human_approval: bool = False
    verifier_report: VerifierReport | None = None
    narrations: tuple[NarrationResult, ...] = ()
    evidence: tuple[EvidenceRecord, ...] = ()
    audit_log: tuple[TimelineEntry, ...] = ()

    def transition(
        self,
        requested: ReconciliationState,
        *,
        agent: str,
        summary: str,
    ) -> None:
        """Advance exactly one DAG state and append an audit timeline entry."""
        require_transition(self.state, requested)
        self.state = requested
        self.audit_log = (
            *self.audit_log,
            TimelineEntry(
                sequence=len(self.audit_log) + 1,
                state=requested,
                agent=agent,
                summary=summary,
            ),
        )
