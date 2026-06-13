"""Typed contracts shared by every semantic grounding provider."""

from collections.abc import Sequence
from datetime import date
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProviderMode(StrEnum):
    """Supported semantic grounding modes."""

    LOCAL = "local"
    REPLAY = "replay"
    FOUNDRY_IQ = "foundry_iq"
    FABRIC_IQ = "fabric_iq"
    WORK_IQ = "work_iq"
    FOUNDRY_HOSTED = "foundry_hosted"


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


class AuthorityGrounding(ContractModel):
    """Advisory governance grounding — a cited clue that NEVER decides authority.

    The deterministic authority rule owns the decision. This corroborates or flags it
    with a labelled, cited source (for example a Foundry IQ retrieval), and is always
    advisory: it can change nothing about the resolved owner or status.
    """

    source: str
    retrieved_owner: str | None = None
    citation: str
    note: str
    agrees_with_rule: bool = False
    advisory_only: bool = True


class QueryDefinitionSummary(ContractModel):
    """A compact, ontology-grounded view of one competing definition."""

    definition_id: str
    name: str
    owner: str
    rule_text: str


class QueryResult(ContractModel):
    """An NL2Ontology-style grounded answer to a business question.

    The answer is grounded in the ontology — the resolved concept and its
    competing definitions — never free-text retrieval. The deterministic
    reconciliation engine still owns conflict quantification; this only resolves
    the question to governed meaning.
    """

    question: str
    matched: bool
    grounding_provider: str
    concept_id: str | None = None
    canonical_name: str | None = None
    answer: str
    definitions: tuple[QueryDefinitionSummary, ...] = ()
    citations: tuple[str, ...] = ()


def build_query_result(
    question: str,
    *,
    provider_name: str,
    concept: ConceptResolution,
    bindings: tuple[DefinitionBinding, ...],
) -> QueryResult:
    """Compose a deterministic, ontology-grounded answer (no LLM, no retrieval)."""
    definitions = tuple(
        QueryDefinitionSummary(
            definition_id=binding.definition_id,
            name=binding.name,
            owner=binding.owner,
            rule_text=binding.rule_text,
        )
        for binding in bindings
    )
    owners = sorted({definition.owner for definition in definitions})
    detail = " ".join(
        f"{definition.owner} defines it as: {definition.rule_text}" for definition in definitions
    )
    answer = (
        f"{concept.canonical_name} has {len(definitions)} competing definitions across "
        f"{', '.join(owners)}. {detail} Run a reconciliation to quantify whether these "
        "definitions select different populations."
    )
    return QueryResult(
        question=question,
        matched=True,
        grounding_provider=provider_name,
        concept_id=concept.concept_id,
        canonical_name=concept.canonical_name,
        answer=answer,
        definitions=definitions,
        citations=tuple(definition.definition_id for definition in definitions),
    )


def unmatched_query_result(question: str, *, provider_name: str) -> QueryResult:
    """Return a grounded 'no match' answer when no concept resolves."""
    return QueryResult(
        question=question,
        matched=False,
        grounding_provider=provider_name,
        answer="No governed concept in the ontology matched this question.",
    )


def _governing_owner(rules: Sequence[AuthorityRule]) -> str | None:
    """The single governing owner named by the rules, or None when not unambiguous.

    Mirrors the deterministic resolver's precedence so the advisory clue surfaces the
    real governance owner (e.g. the Data Governance Council), not a domain owner.
    """
    canonical = next(
        (rule for rule in rules if rule.semantic_dimension.startswith("canonical-")),
        None,
    )
    if canonical and canonical.status == "clear" and canonical.owner:
        return canonical.owner
    clear_owners = {rule.owner for rule in rules if rule.status == "clear" and rule.owner}
    if rules and all(rule.status == "clear" for rule in rules) and len(clear_owners) == 1:
        return next(iter(clear_owners))
    return None


def authority_grounding_from_rules(
    rules: Sequence[AuthorityRule],
    *,
    source: str,
    citation: str,
) -> AuthorityGrounding | None:
    """Build an advisory governance clue from retrieved authority rules.

    Never decides: the caller compares this clue against the independently computed
    deterministic owner. An empty rule set yields no clue.
    """
    if not rules:
        return None
    owner = _governing_owner(rules)
    if owner is None:
        note = (
            f"{source} found no single governing owner for this concept; the "
            "deterministic authority rule independently routes it to human governance."
        )
    else:
        note = (
            f"{source} surfaced {owner} as the governing owner; the deterministic "
            "authority rule independently owns the decision."
        )
    return AuthorityGrounding(
        source=source,
        retrieved_owner=owner,
        citation=citation,
        note=note,
    )


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

    def nl_query(self, question: str) -> QueryResult:
        """Resolve a natural-language business question to grounded meaning."""


@runtime_checkable
class AuthorityGroundingProvider(Protocol):
    """Optional capability: contribute an advisory, cited governance clue.

    Providers MAY implement this to surface a retrievable governance grounding during
    authority resolution. It is advisory only and never changes the deterministic
    authority decision (owner or status).
    """

    def retrieve_authority_grounding(self, concept_id: str) -> AuthorityGrounding | None:
        """Return a cited advisory governance clue for a concept, or None."""
