"""Validate that a sanitized artifact proves semantic IQ retrieval."""

from __future__ import annotations

import re
from pathlib import Path

from concord.config import ScenarioPack, Settings
from concord.providers.base import ProviderMode
from concord.providers.replay import ReplayProvider
from concord.providers.replay_schema import (
    ReplayArtifact,
    ReplayScenarioSnapshot,
    expected_entity_type,
)

# Each reviewed pack proves the same governance behaviours; replay validation requires the
# pack's lead scenarios. Business is the committed/generalization proof; learning
# (Certification Ready) is the challenge-facing default once a learning artifact is captured.
PACK_REQUIRED_SCENARIOS: dict[ScenarioPack, dict[str, str]] = {
    ScenarioPack.BUSINESS: {
        "active-customer": "Active Customer",
        "net-revenue": "Net Revenue",
        "churned-customer": "Churned Customer",
    },
    ScenarioPack.LEARNING: {
        "certification-ready": "Certification Ready",
    },
}
# The lead conflict scenario and the owners that prove a real multi-team disagreement.
PACK_LEAD_SCENARIO: dict[ScenarioPack, tuple[str, str, frozenset[str]]] = {
    ScenarioPack.BUSINESS: (
        "active-customer",
        "Active Customer",
        frozenset({"Finance", "Sales", "Customer Success"}),
    ),
    ScenarioPack.LEARNING: (
        "certification-ready",
        "Certification Ready",
        frozenset({"HR", "Learning & Development", "Managers"}),
    ),
}
ALLOWED_PROVIDERS = {
    ("FabricIQProvider", ProviderMode.FABRIC_IQ),
    ("FoundryIQProvider", ProviderMode.FOUNDRY_IQ),
}
SECRET_PATTERNS = (
    re.compile(r"\bBearer\b", re.IGNORECASE),
    re.compile(r"\baccess[_-]?token\b|\baccessToken\b", re.IGNORECASE),
    re.compile(r"\bapi[_-]?key\b|\bapiKey\b", re.IGNORECASE),
    re.compile(r"\bclient[_-]?secret\b|\bclientSecret\b", re.IGNORECASE),
    re.compile(r"\bpassword\b", re.IGNORECASE),
    re.compile(r"\bAuthorization\b", re.IGNORECASE),
)


class ReplayCheckError(RuntimeError):
    """Raised when a replay artifact is unsafe or semantically incomplete."""


def _require_semantic_evidence(snapshot: ReplayScenarioSnapshot) -> None:
    if not snapshot.bindings:
        raise ReplayCheckError(f"{snapshot.term} has no metric definitions or bindings.")
    if not snapshot.evaluations:
        raise ReplayCheckError(f"{snapshot.term} has no executed evaluations.")
    if not snapshot.subgraph.nodes or not snapshot.subgraph.relationships:
        raise ReplayCheckError(f"{snapshot.term} has no ontology subgraph evidence.")
    if not snapshot.authority_rules:
        raise ReplayCheckError(f"{snapshot.term} has no authority rules.")
    if len(snapshot.bindings) != len(snapshot.evaluations):
        raise ReplayCheckError(f"{snapshot.term} has mismatched binding and evaluation evidence.")
    for binding, evaluation in zip(
        snapshot.bindings,
        snapshot.evaluations,
        strict=True,
    ):
        if not (
            binding.rule_text
            and binding.semantic_dimensions
            and binding.source_tables
            and binding.sql_template
        ):
            raise ReplayCheckError(
                f"{snapshot.term} binding {binding.binding_id} lacks semantic detail."
            )
        if not evaluation.rows or evaluation.entity_count < 1 or not evaluation.executed_sql:
            raise ReplayCheckError(
                f"{snapshot.term} evaluation {evaluation.binding_id} lacks data evidence."
            )


def _detect_scenario_pack(by_id: dict[str, ReplayScenarioSnapshot]) -> ScenarioPack:
    """Infer the reviewed pack from the scenarios present in the artifact."""
    present = set(by_id)
    for pack, required in PACK_REQUIRED_SCENARIOS.items():
        if set(required) <= present:
            return pack
    raise ReplayCheckError(
        "Replay artifact does not contain a complete reviewed scenario set "
        f"(have: {', '.join(sorted(present)) or 'none'})."
    )


def _validate_fabric_semantic_proof(
    artifact: ReplayArtifact,
    required_terms: tuple[str, ...],
) -> None:
    """Require honest Fabric semantic-proof provenance (not connectivity-only / fake)."""
    capture = artifact.capture
    if (capture.provider_name, capture.provider_mode) != (
        "FabricIQProvider",
        ProviderMode.FABRIC_IQ,
    ):
        raise ReplayCheckError("Semantic-proof artifacts must be FabricIQProvider / FABRIC_IQ.")
    if not capture.fabric_tools_used:
        raise ReplayCheckError("Fabric semantic proof must record the MCP tools used.")
    if capture.snapshot_source != "LocalProvider synthetic snapshot":
        raise ReplayCheckError(
            "Semantic-proof artifacts must declare the deterministic snapshot source."
        )
    for term in required_terms:
        expected = expected_entity_type(term)
        matched = capture.fabric_matched_concepts.get(term)
        if matched != expected:
            raise ReplayCheckError(
                f"Fabric did not prove the {term!r} concept "
                f"(expected entity type {expected!r}, got {matched!r})."
            )
        if term not in capture.semantic_proof_terms:
            raise ReplayCheckError(f"{term!r} is missing from semantic_proof_terms.")


def validate_replay_artifact(path: Path) -> ReplayArtifact:
    """Validate provenance, scenarios, semantics, secret hygiene, and replayability."""
    if not path.exists():
        raise ReplayCheckError(f"Replay artifact does not exist: {path}")
    raw = path.read_text(encoding="utf-8")
    for pattern in SECRET_PATTERNS:
        if pattern.search(raw):
            raise ReplayCheckError(
                f"Replay artifact contains forbidden secret-shaped text: {pattern.pattern}"
            )
    try:
        artifact = ReplayArtifact.model_validate_json(raw)
    except ValueError as error:
        raise ReplayCheckError(f"Replay artifact is not valid typed JSON: {error}") from error
    if not artifact.capture.verified_real_iq:
        raise ReplayCheckError("Replay artifact is not marked verified_real_iq=true.")
    provenance = (artifact.capture.provider_name, artifact.capture.provider_mode)
    if provenance not in ALLOWED_PROVIDERS:
        raise ReplayCheckError(
            "Replay provider must be FabricIQProvider or FoundryIQProvider with matching mode."
        )
    by_id = {snapshot.scenario_id: snapshot for snapshot in artifact.scenarios}
    scenario_pack = _detect_scenario_pack(by_id)
    required_scenarios = PACK_REQUIRED_SCENARIOS[scenario_pack]
    for scenario_id, expected_term in required_scenarios.items():
        snapshot = by_id[scenario_id]
        if snapshot.term != expected_term:
            raise ReplayCheckError(
                f"{scenario_id} must contain term {expected_term!r}, not {snapshot.term!r}."
            )
        _require_semantic_evidence(snapshot)
    lead_id, lead_term, required_owners = PACK_LEAD_SCENARIO[scenario_pack]
    lead = by_id[lead_id]
    owners = {binding.owner for binding in lead.bindings}
    if not required_owners <= owners:
        raise ReplayCheckError(
            f"{lead_term} must include the {', '.join(sorted(required_owners))} definitions."
        )
    if "semantic_proof" in (artifact.capture.iq_proof_mode or ""):
        _validate_fabric_semantic_proof(artifact, tuple(required_scenarios.values()))
    ReplayProvider(path).resolve_concept(lead_term)
    return artifact


def main() -> None:
    settings = Settings()
    try:
        artifact = validate_replay_artifact(settings.replay_artifact_path)
    except ReplayCheckError as error:
        raise SystemExit(f"Replay check failed: {error}") from error
    print(
        "Replay artifact passed: "
        f"{artifact.capture.provider_name}, {len(artifact.scenarios)} semantic scenarios."
    )
    print("No obvious secrets were found. Cloud-free demo replay follows.")


if __name__ == "__main__":
    main()
