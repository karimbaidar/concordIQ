"""Compact context assembly for deterministic specialist agents."""

from concord.orchestration.casefile import ContextPacket
from concord.providers import (
    AuthorityRule,
    ConceptResolution,
    DefinitionBinding,
    GroundingProvider,
    OntologySubgraph,
)

PROHIBITED_ASSUMPTIONS = (
    "Do not infer authority that is absent from configured authority rules.",
    "Do not treat wording differences as proof of a data conflict.",
    "Do not claim Microsoft IQ execution while running LocalProvider.",
    "Do not replace executed SQL or entity sets with generated narrative.",
)


def build_context_packet(
    question: str,
    provider: GroundingProvider,
    concept: ConceptResolution,
    bindings: list[DefinitionBinding],
    subgraph: OntologySubgraph,
    authority_rules: list[AuthorityRule],
) -> ContextPacket:
    """Include only the context required for the resolved scenario."""
    return ContextPacket(
        user_question=question,
        resolved_term=concept.canonical_name,
        ontology_node_ids=tuple(node.node_id for node in subgraph.nodes),
        candidate_definition_ids=tuple(binding.definition_id for binding in bindings),
        authority_rule_dimensions=tuple(rule.semantic_dimension for rule in authority_rules),
        business_units=tuple(dict.fromkeys(binding.owner for binding in bindings)),
        analytical_tables=tuple(
            dict.fromkeys(table for binding in bindings for table in binding.source_tables)
        ),
        provider_metadata={
            "name": provider.name,
            "mode": provider.mode.value,
            "uses_cloud": provider.uses_cloud,
            "data_type": "synthetic",
        },
        active_scenario=concept.concept_id,
        prohibited_assumptions=PROHIBITED_ASSUMPTIONS,
        uncertainty_notes=(),
    )
