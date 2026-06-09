"""Deterministic local semantic grounding and DuckDB execution."""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb

from concord.providers.base import (
    AuthorityRule,
    BindingNotFound,
    ConceptNotFound,
    ConceptResolution,
    DefinitionBinding,
    DefinitionEvaluation,
    EvaluationPeriod,
    EvaluationRow,
    OntologyNode,
    OntologyRelationship,
    OntologySubgraph,
    ProviderMode,
    ProviderNotConfigured,
    QueryResult,
    build_query_result,
    unmatched_query_result,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ONTOLOGY_PATH = REPOSITORY_ROOT / "ontology" / "ontology.yaml"
DEFAULT_DEFINITIONS_PATH = REPOSITORY_ROOT / "ontology" / "metric_definitions.yaml"
DEFAULT_AUTHORITY_RULES_PATH = REPOSITORY_ROOT / "ontology" / "authority_rules.yaml"
DEFAULT_DUCKDB_PATH = REPOSITORY_ROOT / "data" / "concord_iq.duckdb"
TRAILING_WINDOW_PATTERN = re.compile(r"INTERVAL \d+ DAY")


def _load_yaml_document(path: Path) -> dict[str, Any]:
    """Load a JSON-compatible YAML document without an additional parser dependency."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ProviderNotConfigured(f"Missing LocalProvider registry: {path}") from error
    except json.JSONDecodeError as error:
        raise ProviderNotConfigured(f"{path} must remain JSON-compatible YAML: {error}") from error


def _normalized_term(value: str) -> str:
    return " ".join(value.casefold().replace("-", " ").split())


@dataclass(slots=True)
class LocalProvider:
    """Cost-safe reproducibility mode over local registries and synthetic data."""

    name: str = "LocalProvider"
    mode: ProviderMode = ProviderMode.LOCAL
    uses_cloud: bool = False
    ontology_path: Path = DEFAULT_ONTOLOGY_PATH
    definitions_path: Path = DEFAULT_DEFINITIONS_PATH
    authority_rules_path: Path = DEFAULT_AUTHORITY_RULES_PATH
    duckdb_path: Path = DEFAULT_DUCKDB_PATH

    def _ontology(self) -> dict[str, Any]:
        return _load_yaml_document(self.ontology_path)

    def _definitions(self) -> tuple[dict[str, Any], ...]:
        document = _load_yaml_document(self.definitions_path)
        return tuple(document["definitions"])

    def _authority_rules(self) -> tuple[dict[str, Any], ...]:
        document = _load_yaml_document(self.authority_rules_path)
        return tuple(document["rules"])

    def list_concepts(self) -> list[ConceptResolution]:
        """Enumerate every registered concept (used by the portfolio scan)."""
        definitions = self._definitions()
        resolutions: list[ConceptResolution] = []
        for concept in self._ontology()["concepts"]:
            definition_ids = tuple(
                definition["definition_id"]
                for definition in definitions
                if definition["concept_id"] == concept["concept_id"]
            )
            resolutions.append(
                ConceptResolution(
                    concept_id=concept["concept_id"],
                    canonical_name=concept["canonical_name"],
                    description=concept["description"],
                    aliases=tuple(concept.get("aliases", ())),
                    definition_ids=definition_ids,
                )
            )
        return resolutions

    def nl_query(self, question: str) -> QueryResult:
        """Resolve a business question to its governed concept and definitions."""
        normalized = _normalized_term(question)
        best_concept: dict[str, Any] | None = None
        best_length = 0
        for concept in self._ontology()["concepts"]:
            for name in (concept["canonical_name"], *concept.get("aliases", ())):
                candidate = _normalized_term(name)
                if candidate and candidate in normalized and len(candidate) > best_length:
                    best_concept = concept
                    best_length = len(candidate)
        if best_concept is None:
            return unmatched_query_result(question, provider_name=self.name)
        resolution = self.resolve_concept(best_concept["canonical_name"])
        bindings = tuple(self.get_binding_semantics(resolution.concept_id))
        return build_query_result(
            question,
            provider_name=self.name,
            concept=resolution,
            bindings=bindings,
        )

    def resolve_concept(self, term: str) -> ConceptResolution:
        sought = _normalized_term(term)
        for concept in self._ontology()["concepts"]:
            names = (concept["canonical_name"], *concept.get("aliases", ()))
            if sought in {_normalized_term(name) for name in names}:
                definition_ids = tuple(
                    definition["definition_id"]
                    for definition in self._definitions()
                    if definition["concept_id"] == concept["concept_id"]
                )
                return ConceptResolution(
                    concept_id=concept["concept_id"],
                    canonical_name=concept["canonical_name"],
                    description=concept["description"],
                    aliases=tuple(concept.get("aliases", ())),
                    definition_ids=definition_ids,
                )
        raise ConceptNotFound(f"No concept registered for term: {term}")

    def get_binding_semantics(self, concept_id: str) -> list[DefinitionBinding]:
        bindings = [
            self._to_binding(definition)
            for definition in self._definitions()
            if definition["concept_id"] == concept_id
        ]
        if not bindings:
            raise ConceptNotFound(f"No concept or definitions registered for: {concept_id}")
        return bindings

    def get_canonical_binding(
        self,
        concept_id: str,
        *,
        source_definition_id: str,
        rule_text: str,
        version: str,
        approved_by: str,
    ) -> tuple[DefinitionBinding, tuple[DefinitionBinding, ...]]:
        """Overlay one approved registry meaning without mutating the YAML views."""
        domain_views = tuple(self.get_binding_semantics(concept_id))
        source = next(
            (binding for binding in domain_views if binding.definition_id == source_definition_id),
            None,
        )
        if source is None:
            raise BindingNotFound(
                f"Canonical source definition {source_definition_id!r} is not registered."
            )
        canonical = source.model_copy(
            update={
                "name": f"Canonical v{version} — approved by {approved_by}",
                "owner": approved_by,
                "rule_text": rule_text,
            }
        )
        return canonical, domain_views

    def evaluate_definition(
        self,
        binding_id: str,
        period: EvaluationPeriod,
    ) -> DefinitionEvaluation:
        definition = next(
            (item for item in self._definitions() if item["binding"]["binding_id"] == binding_id),
            None,
        )
        if definition is None:
            raise BindingNotFound(f"No binding registered with id: {binding_id}")
        return self.evaluate_binding(self._to_binding(definition), period)

    def evaluate_binding(
        self,
        binding: DefinitionBinding,
        period: EvaluationPeriod,
    ) -> DefinitionEvaluation:
        """Execute a trusted binding, including an ephemeral copied binding."""
        if not self.duckdb_path.exists():
            raise ProviderNotConfigured(
                f"DuckDB data is missing at {self.duckdb_path}. Run `make seed` first."
            )

        sql_template = binding.sql_template
        if binding.time_window_days is not None:
            if binding.time_window_days < 1:
                raise ValueError("time_window_days must be positive.")
            sql_template, replacements = TRAILING_WINDOW_PATTERN.subn(
                f"INTERVAL {binding.time_window_days - 1} DAY",
                sql_template,
            )
            if replacements != 1:
                raise ProviderNotConfigured(
                    f"Binding {binding.binding_id} must have exactly one trusted "
                    "trailing-window SQL clause."
                )

        rendered_sql = sql_template.format(
            period_start=period.start_date.isoformat(),
            period_end=period.end_date.isoformat(),
            as_of_date=period.end_date.isoformat(),
        )
        with duckdb.connect(str(self.duckdb_path), read_only=True) as connection:
            result_rows = connection.execute(rendered_sql).fetchall()

        rows = tuple(
            EvaluationRow(entity_id=str(entity_id), metric_value=float(metric_value))
            for entity_id, metric_value in result_rows
        )
        return DefinitionEvaluation(
            binding_id=binding.binding_id,
            definition_id=binding.definition_id,
            concept_id=binding.concept_id,
            period=period,
            entity_ids=tuple(row.entity_id for row in rows),
            rows=rows,
            entity_count=len(rows),
            metric_total=round(sum(row.metric_value for row in rows), 2),
            executed_sql=rendered_sql,
        )

    def get_subgraph(self, concept_id: str) -> OntologySubgraph:
        document = self._ontology()
        relationships = tuple(
            OntologyRelationship(
                source=item["source"],
                target=item["target"],
                relationship_type=item["relationship_type"],
            )
            for item in document["relationships"]
            if item["source"] == concept_id or item["target"] == concept_id
        )
        relevant_ids = {
            concept_id,
            *(relationship.source for relationship in relationships),
            *(relationship.target for relationship in relationships),
        }
        nodes = tuple(
            OntologyNode(
                node_id=item["node_id"],
                node_type=item["node_type"],
                label=item["label"],
                properties=item.get("properties", {}),
            )
            for item in document["nodes"]
            if item["node_id"] in relevant_ids
        )
        if not any(node.node_id == concept_id for node in nodes):
            raise ConceptNotFound(f"No ontology node registered for: {concept_id}")
        return OntologySubgraph(
            concept_id=concept_id,
            nodes=nodes,
            relationships=relationships,
        )

    def get_authority_rules(self, concept_id: str) -> list[AuthorityRule]:
        return [
            AuthorityRule(
                concept_id=item["concept_id"],
                semantic_dimension=item["semantic_dimension"],
                status=item["status"],
                owner=item.get("owner"),
                rationale=item["rationale"],
            )
            for item in self._authority_rules()
            if item["concept_id"] == concept_id
        ]

    @staticmethod
    def _to_binding(definition: dict[str, Any]) -> DefinitionBinding:
        binding = definition["binding"]
        return DefinitionBinding(
            binding_id=binding["binding_id"],
            definition_id=definition["definition_id"],
            concept_id=definition["concept_id"],
            name=definition["name"],
            owner=definition["owner"],
            rule_text=definition["rule_text"],
            semantic_dimensions=tuple(definition["semantic_dimensions"]),
            source_tables=tuple(binding["source_tables"]),
            entity_key=binding["entity_key"],
            grain=binding["grain"],
            population=binding["population"],
            time_window_days=binding.get("time_window_days"),
            filters=tuple(binding.get("filters", ())),
            exclusions=tuple(binding.get("exclusions", ())),
            sql_template=binding["sql_template"],
        )
