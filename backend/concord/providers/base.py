"""Typed contracts shared by every semantic grounding provider."""

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from concord.config import Settings


class ProviderMode(StrEnum):
    """Supported semantic grounding modes."""

    LOCAL = "local"
    REPLAY = "replay"
    FOUNDRY_IQ = "foundry_iq"
    FABRIC_IQ = "fabric_iq"


class ProviderNotConfigured(RuntimeError):
    """Raised when a provider scaffold has no verified external configuration."""


class ConceptNotFound(LookupError):
    """Raised when no registered concept matches a business term."""


class BindingNotFound(LookupError):
    """Raised when no registered operational binding matches an identifier."""


class ContractModel(BaseModel):
    """Immutable base for provider responses."""

    model_config = ConfigDict(frozen=True)


class EvaluationPeriod(ContractModel):
    """Inclusive analytical period used to render trusted SQL bindings."""

    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_order(self) -> "EvaluationPeriod":
        if self.start_date > self.end_date:
            raise ValueError("start_date must not be after end_date")
        return self


class ConceptResolution(ContractModel):
    """A canonical concept and the definitions that claim to implement it."""

    concept_id: str
    canonical_name: str
    description: str
    aliases: tuple[str, ...] = ()
    definition_ids: tuple[str, ...] = ()


class DefinitionBinding(ContractModel):
    """Normalized operational semantics for one domain-owned definition."""

    binding_id: str
    definition_id: str
    concept_id: str
    name: str
    owner: str
    rule_text: str
    semantic_dimensions: tuple[str, ...]
    source_tables: tuple[str, ...]
    entity_key: str
    grain: str
    population: str
    time_window_days: int | None = None
    filters: tuple[str, ...] = ()
    exclusions: tuple[str, ...] = ()
    sql_template: str = Field(repr=False)


class EvaluationRow(ContractModel):
    """One entity selected by an operational definition."""

    entity_id: str
    metric_value: float


class DefinitionEvaluation(ContractModel):
    """Deterministic result of executing one definition against DuckDB."""

    binding_id: str
    definition_id: str
    concept_id: str
    period: EvaluationPeriod
    entity_ids: tuple[str, ...]
    rows: tuple[EvaluationRow, ...]
    entity_count: int
    metric_total: float
    executed_sql: str


class OntologyNode(ContractModel):
    """A compact ontology node returned in a concept subgraph."""

    node_id: str
    node_type: str
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)


class OntologyRelationship(ContractModel):
    """A directed ontology relationship."""

    source: str
    target: str
    relationship_type: str


class OntologySubgraph(ContractModel):
    """The relevant ontology neighborhood for one concept."""

    concept_id: str
    nodes: tuple[OntologyNode, ...]
    relationships: tuple[OntologyRelationship, ...]


class AuthorityRule(ContractModel):
    """Configured ownership for a semantic dimension."""

    concept_id: str
    semantic_dimension: str
    status: str
    owner: str | None = None
    rationale: str


@runtime_checkable
class GroundingProvider(Protocol):
    """Backend-independent semantic grounding and execution contract."""

    name: str
    mode: ProviderMode
    uses_cloud: bool

    def resolve_concept(self, term: str) -> ConceptResolution:
        """Resolve an alias or canonical business term."""

    def get_binding_semantics(self, concept_id: str) -> list[DefinitionBinding]:
        """Return every operational definition registered for a concept."""

    def evaluate_definition(
        self,
        binding_id: str,
        period: EvaluationPeriod,
    ) -> DefinitionEvaluation:
        """Execute a trusted definition binding against its analytical data."""

    def get_subgraph(self, concept_id: str) -> OntologySubgraph:
        """Return the ontology neighborhood relevant to a concept."""

    def get_authority_rules(self, concept_id: str) -> list[AuthorityRule]:
        """Return configured authority rules without inferring missing ownership."""


@dataclass(slots=True)
class CloudProviderScaffold:
    """Fail-closed base for cloud adapters implemented in Phase P5."""

    settings: Settings = field(default_factory=Settings)
    name: str = "CloudProvider"
    mode: ProviderMode = ProviderMode.LOCAL

    def require_ready(self) -> None:
        """Verify cloud opt-in, then report that the adapter is not configured."""
        self.settings.require_cloud_access(self.name)
        raise ProviderNotConfigured(
            f"{self.name} is an architecture scaffold; no endpoint is configured."
        )
