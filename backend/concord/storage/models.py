"""SQLAlchemy models for the Concord IQ PostgreSQL registry."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    """Return an aware UTC timestamp for model defaults."""
    return datetime.now(UTC)


NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class with stable PostgreSQL constraint names."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class BusinessUnit(Base):
    __tablename__ = "business_units"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class BusinessTerm(Base):
    __tablename__ = "business_terms"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    canonical_name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class MetricDefinition(Base):
    __tablename__ = "metric_definitions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    term_id: Mapped[UUID] = mapped_column(ForeignKey("business_terms.id", ondelete="CASCADE"))
    business_unit_id: Mapped[UUID] = mapped_column(
        ForeignKey("business_units.id", ondelete="RESTRICT")
    )
    name: Mapped[str] = mapped_column(String(200))
    version: Mapped[str] = mapped_column(String(40), default="1.0")
    status: Mapped[str] = mapped_column(String(40), default="candidate")
    rule_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DefinitionBinding(Base):
    __tablename__ = "definition_bindings"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("metric_definitions.id", ondelete="CASCADE"), index=True
    )
    source_table: Mapped[str] = mapped_column(String(120))
    entity_key: Mapped[str] = mapped_column(String(120))
    sql_template: Mapped[str] = mapped_column(Text)
    time_window_days: Mapped[int | None]
    filters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class OntologyEntity(Base):
    __tablename__ = "ontology_entities"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    entity_type: Mapped[str] = mapped_column(String(100), index=True)
    external_key: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(200))
    properties: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class OntologyRelationship(Base):
    __tablename__ = "ontology_relationships"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    source_entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("ontology_entities.id", ondelete="CASCADE"), index=True
    )
    target_entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("ontology_entities.id", ondelete="CASCADE"), index=True
    )
    relationship_type: Mapped[str] = mapped_column(String(120), index=True)
    properties: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class AuthorityRule(Base):
    __tablename__ = "authority_rules"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    term_id: Mapped[UUID] = mapped_column(ForeignKey("business_terms.id", ondelete="CASCADE"))
    semantic_dimension: Mapped[str] = mapped_column(String(160), index=True)
    business_unit_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("business_units.id", ondelete="SET NULL")
    )
    authority_status: Mapped[str] = mapped_column(String(40))
    rationale: Mapped[str] = mapped_column(Text)


class ReconciliationRun(Base):
    __tablename__ = "reconciliation_runs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    request_text: Mapped[str] = mapped_column(Text)
    provider_name: Mapped[str] = mapped_column(String(80), default="LocalProvider")
    status: Mapped[str] = mapped_column(String(40), default="pending", index=True)
    context_packet: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ConflictFinding(Base):
    __tablename__ = "conflict_findings"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("reconciliation_runs.id", ondelete="CASCADE"), index=True
    )
    term_id: Mapped[UUID] = mapped_column(ForeignKey("business_terms.id", ondelete="RESTRICT"))
    verdict: Mapped[str] = mapped_column(String(40), index=True)
    impact_score: Mapped[float] = mapped_column(Float, default=0.0)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("reconciliation_runs.id", ondelete="CASCADE"), index=True
    )
    finding_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("conflict_findings.id", ondelete="CASCADE")
    )
    evidence_type: Mapped[str] = mapped_column(String(80))
    source_ref: Mapped[str] = mapped_column(String(300))
    sql_text: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SemanticProposal(Base):
    __tablename__ = "semantic_proposals"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("reconciliation_runs.id", ondelete="CASCADE"), index=True
    )
    finding_id: Mapped[UUID] = mapped_column(ForeignKey("conflict_findings.id", ondelete="CASCADE"))
    canonical_definition_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("metric_definitions.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(40), default="draft")
    proposal_text: Mapped[str] = mapped_column(Text)
    requires_human_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("reconciliation_runs.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    actor: Mapped[str] = mapped_column(String(120), default="system")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AgentTraceEvent(Base):
    __tablename__ = "agent_trace_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("reconciliation_runs.id", ondelete="CASCADE"), index=True
    )
    step_number: Mapped[int] = mapped_column(Integer)
    agent_name: Mapped[str] = mapped_column(String(120), index=True)
    input_summary: Mapped[str] = mapped_column(Text)
    output_summary: Mapped[str] = mapped_column(Text)
    evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    provider_mode: Mapped[str] = mapped_column(String(40))
    verifier_status: Mapped[str | None] = mapped_column(String(40))
    duration_ms: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
