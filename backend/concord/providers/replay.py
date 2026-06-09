"""Sanitized Microsoft IQ response replay mode."""

from pathlib import Path

from concord.providers.base import (
    AuthorityGrounding,
    AuthorityRule,
    BindingNotFound,
    ConceptNotFound,
    ConceptResolution,
    DefinitionBinding,
    DefinitionEvaluation,
    EvaluationPeriod,
    OntologySubgraph,
    ProviderMode,
    ProviderNotConfigured,
    QueryResult,
    authority_grounding_from_rules,
    build_query_result,
    unmatched_query_result,
)
from concord.providers.replay_schema import ReplayArtifact, ReplayScenarioSnapshot


class ReplayProvider:
    """Replay a reviewed, synthetic-only capture through the provider contract."""

    mode: ProviderMode = ProviderMode.REPLAY
    uses_cloud: bool = False
    data_type: str = "synthetic-replay"

    def __init__(
        self,
        artifact_path: Path,
        *,
        require_verified_capture: bool = True,
    ) -> None:
        try:
            self.artifact = ReplayArtifact.read(artifact_path)
        except FileNotFoundError as error:
            raise ProviderNotConfigured(
                f"Replay artifact does not exist: {artifact_path}"
            ) from error
        if require_verified_capture and not self.artifact.capture.verified_real_iq:
            raise ProviderNotConfigured(
                "Replay artifact is not marked as a verified real Microsoft IQ capture."
            )
        self.name = self.artifact.capture.provider_name
        self._by_term: dict[str, ReplayScenarioSnapshot] = {}
        self._by_concept: dict[str, ReplayScenarioSnapshot] = {}
        self._by_binding: dict[str, tuple[ReplayScenarioSnapshot, int]] = {}
        for snapshot in self.artifact.scenarios:
            terms = (snapshot.term, snapshot.concept.canonical_name, *snapshot.concept.aliases)
            for term in terms:
                self._by_term[self._normalize(term)] = snapshot
            self._by_concept[snapshot.concept.concept_id] = snapshot
            for index, binding in enumerate(snapshot.bindings):
                self._by_binding[binding.binding_id] = (snapshot, index)

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.casefold().replace("-", " ").split())

    def list_concepts(self) -> list[ConceptResolution]:
        """Enumerate every captured concept (used by the portfolio scan)."""
        return [snapshot.concept for snapshot in self.artifact.scenarios]

    def nl_query(self, question: str) -> QueryResult:
        """Resolve a question against the captured concepts, grounded identically."""
        normalized = self._normalize(question)
        best: ReplayScenarioSnapshot | None = None
        best_length = 0
        for snapshot in self.artifact.scenarios:
            names = (snapshot.term, snapshot.concept.canonical_name, *snapshot.concept.aliases)
            for name in names:
                candidate = self._normalize(name)
                if candidate and candidate in normalized and len(candidate) > best_length:
                    best = snapshot
                    best_length = len(candidate)
        if best is None:
            return unmatched_query_result(question, provider_name=self.name)
        return build_query_result(
            question,
            provider_name=self.name,
            concept=best.concept,
            bindings=best.bindings,
        )

    def resolve_concept(self, term: str) -> ConceptResolution:
        snapshot = self._by_term.get(self._normalize(term))
        if snapshot is None:
            raise ConceptNotFound(f"No replay scenario registered for term: {term}")
        return snapshot.concept

    def get_binding_semantics(self, concept_id: str) -> list[DefinitionBinding]:
        snapshot = self._by_concept.get(concept_id)
        if snapshot is None:
            raise ConceptNotFound(f"No replay scenario registered for concept: {concept_id}")
        return list(snapshot.bindings)

    def evaluate_definition(
        self,
        binding_id: str,
        period: EvaluationPeriod,
    ) -> DefinitionEvaluation:
        located = self._by_binding.get(binding_id)
        if located is None:
            raise BindingNotFound(f"No replay evaluation registered for binding: {binding_id}")
        snapshot, index = located
        evaluation = snapshot.evaluations[index]
        if evaluation.period != period:
            raise ProviderNotConfigured(
                f"Replay evaluation for {binding_id} covers {evaluation.period}, not {period}."
            )
        return evaluation

    def get_subgraph(self, concept_id: str) -> OntologySubgraph:
        snapshot = self._by_concept.get(concept_id)
        if snapshot is None:
            raise ConceptNotFound(f"No replay subgraph registered for concept: {concept_id}")
        return snapshot.subgraph

    def get_authority_rules(self, concept_id: str) -> list[AuthorityRule]:
        snapshot = self._by_concept.get(concept_id)
        if snapshot is None:
            raise ConceptNotFound(f"No replay authority registered for concept: {concept_id}")
        return list(snapshot.authority_rules)

    def retrieve_authority_grounding(self, concept_id: str) -> AuthorityGrounding | None:
        """Advisory governance clue from the sanitized capture replay — never decides."""
        snapshot = self._by_concept.get(concept_id)
        if snapshot is None:
            return None
        return authority_grounding_from_rules(
            snapshot.authority_rules,
            source=f"{self.name} (sanitized capture replay)",
            citation=f"replay:{snapshot.scenario_id}",
        )
