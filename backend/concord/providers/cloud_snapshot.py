"""Shared snapshot-backed implementation for configured IQ adapters."""

from abc import ABC, abstractmethod

from concord.config import Settings
from concord.providers.base import (
    AuthorityRule,
    BindingNotFound,
    ConceptNotFound,
    ConceptResolution,
    DefinitionBinding,
    DefinitionEvaluation,
    EvaluationPeriod,
    OntologySubgraph,
    ProviderMode,
)
from concord.providers.cloud import GuardedCloudClient, JsonTransport
from concord.providers.replay_schema import ReplayScenarioSnapshot


class CloudSnapshotProvider(ABC):
    """Cache one typed IQ response and expose it through GroundingProvider."""

    name = "CloudSnapshotProvider"
    mode = ProviderMode.LOCAL
    uses_cloud = True
    data_type = "synthetic"

    def __init__(self, settings: Settings, *, transport: JsonTransport | None = None) -> None:
        self.settings = settings
        self.client = GuardedCloudClient(
            settings,
            provider_name=self.name,
            transport=transport,
        )
        self._by_term: dict[str, ReplayScenarioSnapshot] = {}
        self._by_concept: dict[str, ReplayScenarioSnapshot] = {}
        self._by_binding: dict[str, tuple[ReplayScenarioSnapshot, int]] = {}

    @property
    def cloud_call_count(self) -> int:
        return self.client.cloud_call_count

    @property
    def raw_responses(self) -> tuple[dict[str, object], ...]:
        return tuple(self.client.raw_responses)

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.casefold().replace("-", " ").split())

    def _cache(self, snapshot: ReplayScenarioSnapshot) -> ReplayScenarioSnapshot:
        terms = (snapshot.term, snapshot.concept.canonical_name, *snapshot.concept.aliases)
        for term in terms:
            self._by_term[self._normalize(term)] = snapshot
        self._by_concept[snapshot.concept.concept_id] = snapshot
        for index, binding in enumerate(snapshot.bindings):
            self._by_binding[binding.binding_id] = (snapshot, index)
        return snapshot

    @abstractmethod
    def _retrieve_snapshot(self, term: str) -> ReplayScenarioSnapshot:
        """Retrieve and validate one scenario through the configured IQ surface."""

    def resolve_concept(self, term: str) -> ConceptResolution:
        key = self._normalize(term)
        snapshot = self._by_term.get(key)
        if snapshot is None:
            snapshot = self._cache(self._retrieve_snapshot(term))
        return snapshot.concept

    def get_binding_semantics(self, concept_id: str) -> list[DefinitionBinding]:
        snapshot = self._by_concept.get(concept_id)
        if snapshot is None:
            raise ConceptNotFound(f"Resolve the cloud concept before reading: {concept_id}")
        return list(snapshot.bindings)

    def evaluate_definition(
        self,
        binding_id: str,
        period: EvaluationPeriod,
    ) -> DefinitionEvaluation:
        located = self._by_binding.get(binding_id)
        if located is None:
            raise BindingNotFound(f"No cloud binding registered with id: {binding_id}")
        snapshot, index = located
        evaluation = snapshot.evaluations[index]
        if evaluation.period != period:
            raise ConceptNotFound(
                f"Cloud snapshot period for {binding_id} does not match the requested period."
            )
        return evaluation

    def get_subgraph(self, concept_id: str) -> OntologySubgraph:
        snapshot = self._by_concept.get(concept_id)
        if snapshot is None:
            raise ConceptNotFound(f"Resolve the cloud concept before reading: {concept_id}")
        return snapshot.subgraph

    def get_authority_rules(self, concept_id: str) -> list[AuthorityRule]:
        snapshot = self._by_concept.get(concept_id)
        if snapshot is None:
            raise ConceptNotFound(f"Resolve the cloud concept before reading: {concept_id}")
        return list(snapshot.authority_rules)
