"""Autonomous portfolio scan and Concord Score over the whole ontology.

This is the proactive, read-only "agent that watches" surface: it sweeps every
business concept, executes each definition deterministically, and ranks where
the organization silently disagrees — including the concepts it checked and
found consistent. It performs NO persistence and NO cloud calls, so it is safe
to run on page load. Every verdict is decided by SQL set-equality and authority
configuration, exactly like a single reconciliation; the LLM is not involved.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict

from concord.agents.authority_resolver import AuthorityResolverAgent
from concord.agents.data_execution import DataExecutionAgent
from concord.agents.impact_ranker import ImpactRankerAgent
from concord.orchestration.casefile import ReconciliationRequest
from concord.providers import ConceptResolution, EvaluationPeriod, GroundingProvider

# Score penalties per unresolved conflict, by impact severity, plus an extra
# penalty when authority is too ambiguous to even propose a fix (a refusal).
_SEVERITY_PENALTY = {"low": 2, "medium": 6, "high": 12}
_REFUSAL_PENALTY = 4
_MAX_SCORE = 100

RecommendedAction = Literal["propose", "refuse", "monitor"]


class ConceptListingProvider(Protocol):
    """A grounding provider that can enumerate its registered concepts."""

    def list_concepts(self) -> list[ConceptResolution]: ...


class PortfolioConceptResult(BaseModel):
    """One concept's verdict in the portfolio sweep."""

    model_config = ConfigDict(frozen=True)

    rank: int
    concept_id: str
    term: str
    verdict: Literal["conflict", "consistent"]
    definition_count: int
    counts: tuple[int, ...]
    owners: tuple[str, ...]
    customer_count_delta: int
    arr_delta: float
    severity: Literal["low", "medium", "high"]
    authority_status: Literal["clear", "shared", "ambiguous", "missing"]
    authority_owner: str | None
    recommended_action: RecommendedAction


class BusinessUnitScore(BaseModel):
    """Per-team semantic-health breakdown for the leaderboard."""

    model_config = ConfigDict(frozen=True)

    business_unit: str
    score: int
    open_conflicts: int


class ConcordScore(BaseModel):
    """A single semantic-health number the whole org can rally around."""

    model_config = ConfigDict(frozen=True)

    overall: int
    grade: Literal["A", "B", "C", "D", "F"]
    concepts_scanned: int
    conflicts: int
    consistent: int
    refusals: int
    by_business_unit: tuple[BusinessUnitScore, ...]


class PortfolioScan(BaseModel):
    """The full autonomous-scan payload surfaced to the dashboard."""

    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    provider: str
    period: EvaluationPeriod
    score: ConcordScore
    concepts: tuple[PortfolioConceptResult, ...]


def _grade(score: int) -> Literal["A", "B", "C", "D", "F"]:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def _recommended_action(
    verdict: str,
    authority_status: str,
    authority_owner: str | None,
) -> RecommendedAction:
    if verdict != "conflict":
        return "monitor"
    if authority_status == "clear" and authority_owner:
        return "propose"
    return "refuse"


def _scan_concept(
    provider: GroundingProvider,
    concept: ConceptResolution,
    period: EvaluationPeriod,
) -> PortfolioConceptResult:
    bindings = tuple(provider.get_binding_semantics(concept.concept_id))
    execution = DataExecutionAgent(provider).run(f"scan:{concept.concept_id}", bindings, period)
    impact = ImpactRankerAgent().run(bindings, execution.evaluations)
    authority = AuthorityResolverAgent(provider).run(concept.concept_id)
    return PortfolioConceptResult(
        rank=0,
        concept_id=concept.concept_id,
        term=concept.canonical_name,
        verdict="conflict" if execution.verdict == "conflict" else "consistent",
        definition_count=len(bindings),
        counts=tuple(result.entity_count for result in execution.evaluations),
        owners=tuple(dict.fromkeys(binding.owner for binding in bindings)),
        customer_count_delta=impact.customer_count_delta,
        arr_delta=impact.arr_delta,
        severity=impact.severity,
        authority_status=authority.status,
        authority_owner=authority.owner,
        recommended_action=_recommended_action(
            execution.verdict, authority.status, authority.owner
        ),
    )


def _compute_score(results: tuple[PortfolioConceptResult, ...]) -> ConcordScore:
    conflicts = tuple(item for item in results if item.verdict == "conflict")
    refusals = tuple(item for item in conflicts if item.recommended_action == "refuse")

    penalty = sum(_SEVERITY_PENALTY[item.severity] for item in conflicts)
    penalty += _REFUSAL_PENALTY * len(refusals)
    overall = max(0, _MAX_SCORE - penalty)

    unit_penalty: dict[str, int] = {}
    unit_conflicts: dict[str, int] = {}
    for item in results:
        for owner in item.owners:
            unit_penalty.setdefault(owner, 0)
            unit_conflicts.setdefault(owner, 0)
            if item.verdict == "conflict":
                owner_penalty = _SEVERITY_PENALTY[item.severity]
                if item.recommended_action == "refuse":
                    owner_penalty += _REFUSAL_PENALTY
                unit_penalty[owner] += owner_penalty
                unit_conflicts[owner] += 1

    by_business_unit = tuple(
        BusinessUnitScore(
            business_unit=owner,
            score=max(0, _MAX_SCORE - unit_penalty[owner]),
            open_conflicts=unit_conflicts[owner],
        )
        for owner in sorted(unit_penalty, key=lambda name: (unit_penalty[name], name), reverse=True)
    )
    return ConcordScore(
        overall=overall,
        grade=_grade(overall),
        concepts_scanned=len(results),
        conflicts=len(conflicts),
        consistent=len(results) - len(conflicts),
        refusals=len(refusals),
        by_business_unit=by_business_unit,
    )


def scan_portfolio(
    provider: GroundingProvider,
    *,
    period: EvaluationPeriod | None = None,
) -> PortfolioScan:
    """Sweep every registered concept and rank conflicts by business impact."""
    if not hasattr(provider, "list_concepts"):
        raise TypeError(
            f"{type(provider).__name__} cannot enumerate concepts for a portfolio scan."
        )
    active_period = period or ReconciliationRequest(question="portfolio scan").period
    concepts = provider.list_concepts()  # type: ignore[attr-defined]
    scanned = [_scan_concept(provider, concept, active_period) for concept in concepts]

    # Conflicts ranked by business impact (ARR delta, then population delta);
    # consistent concepts keep rank 0 and sort to the end.
    conflicts = sorted(
        (item for item in scanned if item.verdict == "conflict"),
        key=lambda item: (item.arr_delta, item.customer_count_delta),
        reverse=True,
    )
    consistent = [item for item in scanned if item.verdict != "conflict"]
    ranked: list[PortfolioConceptResult] = []
    for position, item in enumerate(conflicts, start=1):
        ranked.append(item.model_copy(update={"rank": position}))
    ranked.extend(consistent)

    ordered = tuple(ranked)
    return PortfolioScan(
        generated_at=datetime.now(UTC),
        provider=getattr(provider, "name", type(provider).__name__),
        period=active_period,
        score=_compute_score(ordered),
        concepts=ordered,
    )


def default_scan_period() -> EvaluationPeriod:
    """The same default period the single-run reconciliation uses."""
    return ReconciliationRequest(question="portfolio scan").period


__all__ = [
    "BusinessUnitScore",
    "ConcordScore",
    "PortfolioConceptResult",
    "PortfolioScan",
    "default_scan_period",
    "scan_portfolio",
]


def _isodate(value: date) -> str:  # pragma: no cover - convenience for CLIs
    return value.isoformat()
