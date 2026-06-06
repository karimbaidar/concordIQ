"""PostgreSQL repositories for reconciliation runs and evidence."""

from dataclasses import dataclass, field
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from concord.orchestration.casefile import ReconciliationCase
from concord.storage.models import (
    AuditEvent,
    Base,
    BusinessTerm,
    ConflictFinding,
    EvidenceItem,
    ReconciliationRun,
    SemanticProposal,
    utc_now,
)


@dataclass(slots=True)
class ReconciliationRepository:
    """Persist a verified casefile atomically in PostgreSQL."""

    engine: Engine
    _sessions: sessionmaker[Session] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._sessions = sessionmaker(self.engine, expire_on_commit=False)

    def initialize(self) -> None:
        Base.metadata.create_all(self.engine)

    def save(self, case: ReconciliationCase) -> UUID:
        if not case.verifier_report or not case.verifier_report.passed:
            raise ValueError("Only verifier-approved cases may be persisted as complete.")
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
        return case.run_id

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
