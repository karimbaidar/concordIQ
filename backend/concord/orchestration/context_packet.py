"""Compact context assembly for deterministic specialist agents."""

from concord.orchestration.casefile import ContextPacket
from concord.providers import (
    AuthorityRule,
    ConceptResolution,
    DefinitionBinding,
    GroundingProvider,
    OntologySubgraph,
    ProviderMode,
)

PROHIBITED_ASSUMPTIONS = (
    "Do not infer authority that is absent from configured authority rules.",
    "Do not treat wording differences as proof of a data conflict.",
    "Do not claim Microsoft IQ execution while running LocalProvider.",
    "Do not replace executed SQL or entity sets with generated narrative.",
)


def _provider_metadata(
    provider: GroundingProvider,
    concept: ConceptResolution,
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "name": provider.name,
        "mode": provider.mode.value,
        "uses_cloud": provider.uses_cloud,
        "data_type": getattr(provider, "data_type", "synthetic"),
    }
    if provider.mode is ProviderMode.LOCAL:
        metadata.update(
            {
                "grounding_kind": "local_registry",
                "execution_source": "deterministic_local_snapshot",
            }
        )
    elif provider.mode is ProviderMode.REPLAY:
        capture = getattr(getattr(provider, "artifact", None), "capture", None)
        metadata.update(
            {
                "grounding_kind": "sanitized_fabric_replay",
                "execution_source": "deterministic_replay_snapshot",
                "iq_proof_mode": getattr(capture, "iq_proof_mode", None),
                "snapshot_source": getattr(capture, "snapshot_source", None),
                "verified_real_iq": bool(getattr(capture, "verified_real_iq", False)),
            }
        )
    elif provider.mode is ProviderMode.FABRIC_IQ:
        proofs = getattr(provider, "semantic_proofs", {})
        proof = proofs.get(concept.canonical_name) if isinstance(proofs, dict) else None
        metadata.update(
            {
                "grounding_kind": ("fabric_ontology_match" if proof else "local_registry_fallback"),
                "execution_source": "deterministic_local_snapshot",
                "iq_proof_mode": (
                    "fabric_semantic_proof_with_deterministic_snapshot" if proof else None
                ),
                "fabric_semantic_proof": proof,
            }
        )
    return metadata


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
        provider_metadata=_provider_metadata(provider, concept),
        active_scenario=concept.concept_id,
        prohibited_assumptions=PROHIBITED_ASSUMPTIONS,
        uncertainty_notes=(),
    )
