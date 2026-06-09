"""PostgreSQL repositories for reconciliation runs and evidence."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from concord.orchestration.casefile import (
    AgentTraceStep,
    ConflictHypothesis,
    ReconciliationCase,
)
from concord.storage.db import ensure_schema_compatibility
from concord.storage.models import (
    AgentTraceEvent,
    AuditEvent,
    Base,
    BusinessTerm,
    ConflictFinding,
    EvidenceItem,
    ReconciliationRun,
    SemanticProposal,
    utc_now,
)


class ProposalNotFound(LookupError):
    """Raised when a run has no governed proposal to approve (e.g. a refusal)."""


class ProposalAlreadyDecided(RuntimeError):
    """Raised when a proposal has already been approved or rejected."""


class UnauthorizedApprover(PermissionError):
    """Raised when a non-owner attempts to approve or reject a proposal."""


@dataclass(frozen=True, slots=True)
class ProposalDecisionResult:
    """The outcome of a Semantic-PR approval-gate decision."""

    run_id: UUID
    term: str
    status: Literal["approved", "rejected"]
    authority_owner: str
    decided_by: str
    decided_at: datetime


@dataclass(slots=True)
class ReconciliationRepository:
    """Persist a verified casefile atomically in PostgreSQL."""

    engine: Engine
    _sessions: sessionmaker[Session] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._sessions = sessionmaker(self.engine, expire_on_commit=False)

    def initialize(self) -> None:
        Base.metadata.create_all(self.engine)
        ensure_schema_compatibility(self.engine)

    def save(self, case: ReconciliationCase) -> UUID:
        if not case.verifier_report or not case.verifier_report.passed:
            raise ValueError("Only verifier-approved cases may be persisted as complete.")
        if case.verification_status != "passed":
            raise ValueError("Only cases with passed verification status may be persisted.")
        if not case.context_packet or not case.resolved_concept:
            raise ValueError("Resolved concept and context packet are required.")
        if not case.impact_assessment or not case.authority_assessment:
            raise ValueError("Impact and authority assessments are required.")

        with self._sessions.begin() as session:
            term = self._get_or_create_term(session, case)
            run = ReconciliationRun(
                id=case.run_id,
                request_text=case.request.question,
                provider_name=case.context_packet.provider_metadata["name"],
                status="complete",
                context_packet=case.context_packet.model_dump(mode="json"),
                completed_at=utc_now(),
            )
            session.add(run)
            session.flush()
            finding_id = uuid5(
                NAMESPACE_URL,
                f"concord-iq:{case.run_id}:{case.resolved_concept.concept_id}-finding",
            )
            finding = ConflictFinding(
                id=finding_id,
                run_id=case.run_id,
                term_id=term.id,
                verdict=case.verdict,
                impact_score=self._impact_score(case),
                details={
                    "counts": {
                        result.definition_id: result.entity_count
                        for result in case.execution_results
                    },
                    "metric_totals": {
                        result.definition_id: result.metric_total
                        for result in case.execution_results
                    },
                    "impact": case.impact_assessment.model_dump(mode="json"),
                    "authority": case.authority_assessment.model_dump(mode="json"),
                    "refusal_reason": case.refusal_reason,
                    "requires_human_approval": case.requires_human_approval,
                    "verifier": case.verifier_report.model_dump(mode="json"),
                    "narrations": [
                        narration.model_dump(mode="json") for narration in case.narrations
                    ],
                    "conflict_hypotheses": [
                        hypothesis.model_dump(mode="json")
                        for hypothesis in case.conflict_hypotheses
                    ],
                },
            )
            session.add(finding)
            session.flush()
            session.add_all(
                EvidenceItem(
                    id=item.evidence_id,
                    run_id=case.run_id,
                    finding_id=finding_id,
                    evidence_type="definition_evaluation",
                    source_ref=item.source_ref,
                    sql_text=item.sql_text,
                    payload={
                        "binding_id": item.binding_id,
                        "definition_id": item.definition_id,
                        "entity_count": item.entity_count,
                        "metric_total": item.metric_total,
                        "entity_ids": list(item.entity_ids),
                    },
                )
                for item in case.evidence
            )
            if case.reconciliation_proposal:
                session.add(
                    SemanticProposal(
                        id=uuid5(
                            NAMESPACE_URL,
                            f"concord-iq:{case.run_id}:{case.resolved_concept.concept_id}-proposal",
                        ),
                        run_id=case.run_id,
                        finding_id=finding_id,
                        canonical_definition_id=None,
                        status="draft",
                        proposal_text=case.reconciliation_proposal.model_dump_json(),
                        requires_human_approval=(
                            case.reconciliation_proposal.requires_human_approval
                        ),
                    )
                )
            session.add_all(
                AuditEvent(
                    run_id=case.run_id,
                    event_type=entry.state.value,
                    actor=entry.agent,
                    payload=entry.model_dump(mode="json"),
                )
                for entry in case.audit_log
            )
            session.add_all(
                AgentTraceEvent(
                    run_id=case.run_id,
                    step_number=step.step_number,
                    agent_name=step.agent_name,
                    input_summary=step.input_summary,
                    output_summary=step.output_summary,
                    evidence_ids=[str(evidence_id) for evidence_id in step.evidence_ids],
                    deliberations=[
                        hypothesis.model_dump(mode="json") for hypothesis in step.deliberations
                    ],
                    provider_mode=step.provider_mode,
                    verifier_status=step.verifier_status,
                    duration_ms=step.duration_ms,
                )
                for step in case.agent_trace
            )
        return case.run_id

    def get_agent_trace(self, run_id: UUID) -> tuple[AgentTraceStep, ...] | None:
        """Return the ordered specialist trace for one completed run."""
        with self._sessions() as session:
            if session.get(ReconciliationRun, run_id) is None:
                return None
            events = session.scalars(
                select(AgentTraceEvent)
                .where(AgentTraceEvent.run_id == run_id)
                .order_by(AgentTraceEvent.step_number)
            ).all()
            return tuple(
                AgentTraceStep(
                    step_number=event.step_number,
                    agent_name=event.agent_name,
                    input_summary=event.input_summary,
                    output_summary=event.output_summary,
                    evidence_ids=tuple(UUID(value) for value in event.evidence_ids),
                    deliberations=tuple(
                        ConflictHypothesis.model_validate(item)
                        for item in (event.deliberations or [])
                    ),
                    provider_mode=event.provider_mode,
                    verifier_status=event.verifier_status,
                    duration_ms=event.duration_ms,
                )
                for event in events
            )

    def get_proposal_state(self, run_id: UUID) -> dict[str, object] | None:
        """Return a non-secret view of a run's proposal for the approval gate."""
        with self._sessions() as session:
            proposal = session.scalar(
                select(SemanticProposal).where(SemanticProposal.run_id == run_id)
            )
            if proposal is None:
                return None
            term = self._term_for_finding(session, proposal.finding_id)
            owner = self._proposal_owner(proposal.proposal_text)
            return {
                "run_id": str(run_id),
                "term": term,
                "status": proposal.status,
                "authority_owner": owner,
                "requires_human_approval": proposal.requires_human_approval,
            }

    def decide_proposal(
        self,
        run_id: UUID,
        *,
        decision: Literal["approved", "rejected"],
        approver: str,
    ) -> ProposalDecisionResult:
        """Apply a Semantic-PR decision; only the configured owner may decide.

        Deterministic governance: the approver must equal the proposal's
        authority owner, the proposal must still be a draft, and the decision is
        written to the immutable audit trail. The LLM is never consulted.
        """
        with self._sessions.begin() as session:
            proposal = session.scalar(
                select(SemanticProposal).where(SemanticProposal.run_id == run_id)
            )
            if proposal is None:
                raise ProposalNotFound(f"Run {run_id} has no governed proposal to {decision[:-1]}.")
            if proposal.status != "draft":
                raise ProposalAlreadyDecided(
                    f"Proposal for run {run_id} is already {proposal.status}."
                )
            owner = self._proposal_owner(proposal.proposal_text)
            if approver != owner:
                raise UnauthorizedApprover(
                    f"Only {owner} may decide this proposal; {approver!r} is not the owner."
                )
            proposal.status = decision
            term = self._term_for_finding(session, proposal.finding_id)
            decided_at = utc_now()
            session.add(
                AuditEvent(
                    run_id=run_id,
                    event_type="proposal_decision",
                    actor=approver,
                    payload={
                        "decision": decision,
                        "authority_owner": owner,
                        "term": term,
                    },
                )
            )
        return ProposalDecisionResult(
            run_id=run_id,
            term=term,
            status=decision,
            authority_owner=owner,
            decided_by=approver,
            decided_at=decided_at,
        )

    @staticmethod
    def _proposal_owner(proposal_text: str) -> str:
        try:
            return str(json.loads(proposal_text).get("authority_owner", ""))
        except json.JSONDecodeError:
            return ""

    @staticmethod
    def _term_for_finding(session: Session, finding_id: UUID) -> str:
        finding = session.get(ConflictFinding, finding_id)
        if finding is None:
            return ""
        term = session.get(BusinessTerm, finding.term_id)
        return term.canonical_name if term else ""

    @staticmethod
    def _get_or_create_term(
        session: Session,
        case: ReconciliationCase,
    ) -> BusinessTerm:
        concept = case.resolved_concept
        if concept is None:
            raise ValueError("Resolved concept is required.")
        term = session.scalar(
            select(BusinessTerm).where(BusinessTerm.canonical_name == concept.canonical_name)
        )
        if term:
            return term
        term = BusinessTerm(
            canonical_name=concept.canonical_name,
            description=concept.description,
            aliases=list(concept.aliases),
        )
        session.add(term)
        session.flush()
        return term

    @staticmethod
    def _impact_score(case: ReconciliationCase) -> float:
        impact = case.impact_assessment
        if impact is None:
            return 0.0
        severity_weight = {"low": 0.25, "medium": 0.6, "high": 1.0}
        return severity_weight[impact.severity]
