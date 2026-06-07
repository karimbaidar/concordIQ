"""Validate that a sanitized artifact proves semantic IQ retrieval."""

from __future__ import annotations

import re
from pathlib import Path

from concord.config import Settings
from concord.providers.base import ProviderMode
from concord.providers.replay import ReplayProvider
from concord.providers.replay_schema import (
    ReplayArtifact,
    ReplayScenarioSnapshot,
    expected_entity_type,
)

REQUIRED_SCENARIOS = {
    "active-customer": "Active Customer",
    "net-revenue": "Net Revenue",
    "churned-customer": "Churned Customer",
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


def _validate_fabric_semantic_proof(artifact: ReplayArtifact) -> None:
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
    for term in REQUIRED_SCENARIOS.values():
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
    missing = set(REQUIRED_SCENARIOS) - set(by_id)
    if missing:
        raise ReplayCheckError(
            f"Replay artifact is missing scenarios: {', '.join(sorted(missing))}."
        )
    for scenario_id, expected_term in REQUIRED_SCENARIOS.items():
        snapshot = by_id[scenario_id]
        if snapshot.term != expected_term:
            raise ReplayCheckError(
                f"{scenario_id} must contain term {expected_term!r}, not {snapshot.term!r}."
            )
        _require_semantic_evidence(snapshot)
    active = by_id["active-customer"]
    owners = {binding.owner for binding in active.bindings}
    required_owners = {"Finance", "Sales", "Customer Success"}
    if not required_owners <= owners:
        raise ReplayCheckError(
            "Active Customer must include Finance, Sales, and Customer Success definitions."
        )
    if "semantic_proof" in (artifact.capture.iq_proof_mode or ""):
        _validate_fabric_semantic_proof(artifact)
    ReplayProvider(path).resolve_concept("Active Customer")
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
