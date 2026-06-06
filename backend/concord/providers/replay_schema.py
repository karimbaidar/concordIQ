"""Typed, synthetic-only artifact schema shared by capture and replay."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import Field, model_validator

from concord.providers.base import (
    AuthorityRule,
    ConceptResolution,
    ContractModel,
    DefinitionBinding,
    DefinitionEvaluation,
    GroundingProvider,
    OntologySubgraph,
    ProviderMode,
)

if TYPE_CHECKING:
    from concord.demo import DemoScenario


class ReplayScenarioSnapshot(ContractModel):
    """One complete provider-contract snapshot for a demo scenario."""

    scenario_id: str
    term: str
    data_classification: str = "synthetic"
    concept: ConceptResolution
    bindings: tuple[DefinitionBinding, ...]
    evaluations: tuple[DefinitionEvaluation, ...]
    subgraph: OntologySubgraph
    authority_rules: tuple[AuthorityRule, ...]

    @model_validator(mode="after")
    def validate_contract_alignment(self) -> "ReplayScenarioSnapshot":
        """Reject incomplete or cross-scenario capture content."""
        if self.data_classification != "synthetic":
            raise ValueError("Replay scenarios must be classified as synthetic")
        binding_ids = tuple(binding.binding_id for binding in self.bindings)
        evaluation_ids = tuple(evaluation.binding_id for evaluation in self.evaluations)
        if binding_ids != evaluation_ids:
            raise ValueError("Replay bindings and evaluations must align by binding_id")
        if any(binding.concept_id != self.concept.concept_id for binding in self.bindings):
            raise ValueError("Replay bindings must belong to the resolved concept")
        if self.subgraph.concept_id != self.concept.concept_id:
            raise ValueError("Replay subgraph must belong to the resolved concept")
        return self


class ReplayCaptureMetadata(ContractModel):
    """Non-secret provenance for a replay artifact."""

    provider_name: str
    provider_mode: ProviderMode
    captured_at: datetime
    verified_real_iq: bool
    data_classification: str = "synthetic"
    api_version: str | None = None

    @model_validator(mode="after")
    def validate_provenance(self) -> "ReplayCaptureMetadata":
        if self.data_classification != "synthetic":
            raise ValueError("Replay captures must be classified as synthetic")
        cloud_modes = {ProviderMode.FOUNDRY_IQ, ProviderMode.FABRIC_IQ}
        if self.verified_real_iq and self.provider_mode not in cloud_modes:
            raise ValueError("Only a cloud IQ provider can mark a capture as verified")
        return self


class ReplayArtifact(ContractModel):
    """Versioned collection of captured provider-contract snapshots."""

    schema_version: str = "1.0"
    capture: ReplayCaptureMetadata
    scenarios: tuple[ReplayScenarioSnapshot, ...] = Field(min_length=1)

    @classmethod
    def read(cls, path: Path) -> "ReplayArtifact":
        return cls.model_validate_json(path.read_text(encoding="utf-8"))

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            self.model_dump_json(indent=2),
            encoding="utf-8",
        )


def snapshot_provider_scenario(
    provider: GroundingProvider,
    scenario: "DemoScenario",
) -> ReplayScenarioSnapshot:
    """Materialize the complete typed contract for one scenario."""
    request = scenario.request()
    concept = provider.resolve_concept(scenario.term)
    bindings = tuple(provider.get_binding_semantics(concept.concept_id))
    evaluations = tuple(
        provider.evaluate_definition(binding.binding_id, request.period) for binding in bindings
    )
    return ReplayScenarioSnapshot(
        scenario_id=scenario.scenario_id,
        term=scenario.term,
        concept=concept,
        bindings=bindings,
        evaluations=evaluations,
        subgraph=provider.get_subgraph(concept.concept_id),
        authority_rules=tuple(provider.get_authority_rules(concept.concept_id)),
    )


def build_replay_artifact(
    *,
    provider_name: str,
    provider_mode: ProviderMode,
    scenarios: tuple[ReplayScenarioSnapshot, ...],
    verified_real_iq: bool,
    api_version: str | None = None,
    captured_at: datetime | None = None,
) -> ReplayArtifact:
    """Build a versioned artifact after snapshots pass typed validation."""
    return ReplayArtifact(
        capture=ReplayCaptureMetadata(
            provider_name=provider_name,
            provider_mode=provider_mode,
            captured_at=captured_at or datetime.now(UTC),
            verified_real_iq=verified_real_iq,
            api_version=api_version,
        ),
        scenarios=scenarios,
    )


def find_snapshot(value: Any) -> ReplayScenarioSnapshot:
    """Find a snapshot in direct JSON, nested provider output, or text content."""
    if isinstance(value, dict):
        required = {"scenario_id", "term", "concept", "bindings", "evaluations", "subgraph"}
        if required.issubset(value):
            return ReplayScenarioSnapshot.model_validate(value)
        for nested in value.values():
            try:
                return find_snapshot(nested)
            except (TypeError, ValueError):
                continue
    elif isinstance(value, list):
        for nested in value:
            try:
                return find_snapshot(nested)
            except (TypeError, ValueError):
                continue
    elif isinstance(value, str):
        candidate = value.strip()
        if candidate.startswith("```") and candidate.endswith("```"):
            candidate = candidate.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        try:
            return find_snapshot(json.loads(candidate))
        except json.JSONDecodeError:
            pass
    raise ValueError("Provider response did not contain a valid Concord IQ scenario snapshot")
