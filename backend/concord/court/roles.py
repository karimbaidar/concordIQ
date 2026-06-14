"""Evidence-bound speaking roles for the Microsoft Agent Framework Court."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from concord.court.transcript import (
    CourtRole,
    DeliberationTurn,
    TurnDisposition,
    TurnProvenance,
)
from concord.llm import LLMProvider, NarrationRequest, NarrationTask
from concord.orchestration.casefile import ReconciliationCase
from concord.providers import DefinitionBinding

ROUND_OPENING = 0
ROUND_PRESENT = 1
ROUND_PLAN = 2
ROUND_EVIDENCE = 3
ROUND_REPLAN = 4
ROUND_CHALLENGE = 5
ROUND_RESPOND = 6
ROUND_REFLECT = 7
ROUND_AUTHORITY = 8
ROUND_CLOSING = 9


@dataclass(slots=True)
class CourtClerk:
    """Voice typed turns while preserving per-turn provenance."""

    llm: LLMProvider
    start_turn_no: int = 0
    _turn_no: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        self._turn_no = self.start_turn_no

    def emit(
        self,
        *,
        task: NarrationTask,
        role: CourtRole,
        disposition: TurnDisposition,
        agent_id: str,
        round_no: int,
        facts: dict[str, Any],
        fallback: str,
        speaking_for: str | None = None,
        tool_calls: tuple[str, ...] = (),
        cited_evidence_ids: tuple[UUID, ...] = (),
    ) -> DeliberationTurn:
        self._turn_no += 1
        result = self.llm.narrate(NarrationRequest(task=task, facts=facts, fallback_text=fallback))
        return DeliberationTurn(
            turn_no=self._turn_no,
            round_no=round_no,
            agent_id=agent_id,
            role=role,
            disposition=disposition,
            speaking_for=speaking_for,
            content=result.text,
            tool_calls=tool_calls,
            cited_evidence_ids=cited_evidence_ids,
            provenance=TurnProvenance(
                generated=result.generated,
                provider_name=result.provider_name,
                model=result.model,
                fallback_reason=result.fallback_reason,
            ),
        )


def _evidence_by_binding(case: ReconciliationCase) -> dict[str, UUID]:
    return {record.binding_id: record.evidence_id for record in case.evidence}


def _evaluation_by_binding(case: ReconciliationCase) -> dict[str, int]:
    return {result.binding_id: result.entity_count for result in case.execution_results}


def _entity_sets(case: ReconciliationCase) -> dict[str, frozenset[str]]:
    return {result.binding_id: frozenset(result.entity_ids) for result in case.execution_results}


def _steward_id(owner: str) -> str:
    return f"StewardAgent.{owner.split()[0].lower()}"


def canonical_candidate(case: ReconciliationCase) -> DefinitionBinding | None:
    """Return the engine-proposed source binding, never a Court-selected winner."""
    proposal = case.reconciliation_proposal
    if proposal is None or proposal.canonical_source_definition_id is None:
        return None
    return next(
        (
            binding
            for binding in case.binding_semantics
            if binding.definition_id == proposal.canonical_source_definition_id
        ),
        None,
    )


def challengeable_bindings(case: ReconciliationCase) -> tuple[DefinitionBinding, ...]:
    """Return bindings participating in at least one unequal pairwise result set."""
    sets = _entity_sets(case)
    challenged: list[DefinitionBinding] = []
    for binding in case.binding_semantics:
        population = sets.get(binding.binding_id, frozenset())
        if any(
            population != other_population
            for other_id, other_population in sets.items()
            if other_id != binding.binding_id
        ):
            challenged.append(binding)
    return tuple(challenged)


def needs_targeted_replan(case: ReconciliationCase) -> bool:
    """Detect equal-count comparisons whose identities still differ."""
    results = case.execution_results
    for index, left in enumerate(results):
        for right in results[index + 1 :]:
            if left.entity_count == right.entity_count and left.entity_ids != right.entity_ids:
                return True
    return False


def _comparison_population(
    case: ReconciliationCase,
    binding: DefinitionBinding,
) -> frozenset[str]:
    sets = _entity_sets(case)
    candidate = canonical_candidate(case)
    if candidate is not None and candidate.binding_id != binding.binding_id:
        return sets.get(candidate.binding_id, frozenset())
    for other in case.binding_semantics:
        if other.binding_id != binding.binding_id:
            return sets.get(other.binding_id, frozenset())
    return frozenset()


def _divergent_sample(
    case: ReconciliationCase,
    binding: DefinitionBinding,
    limit: int = 3,
) -> str:
    population = _entity_sets(case).get(binding.binding_id, frozenset())
    comparison = _comparison_population(case, binding)
    return ", ".join(sorted(population.symmetric_difference(comparison))[:limit])


def orchestrator_opening(clerk: CourtClerk, case: ReconciliationCase) -> DeliberationTurn:
    owners = ", ".join(binding.owner for binding in case.binding_semantics)
    return clerk.emit(
        task=NarrationTask.DECISION,
        role=CourtRole.ORCHESTRATOR,
        disposition=TurnDisposition.ASSERTED,
        agent_id="CourtCoordinatorAgent",
        round_no=ROUND_OPENING,
        facts={"term": case.request.term, "advocates": owners},
        fallback=(
            f"The court is convened over frozen run {case.run_id} for "
            f"{case.request.term!r}. {owners} may defend their operational views. "
            "No SQL will be rerun and no argument can change the verified verdict."
        ),
    )


def steward_turns(clerk: CourtClerk, case: ReconciliationCase) -> tuple[DeliberationTurn, ...]:
    evidence = _evidence_by_binding(case)
    counts = _evaluation_by_binding(case)
    turns: list[DeliberationTurn] = []
    for binding in case.binding_semantics:
        evidence_id = evidence.get(binding.binding_id)
        turns.append(
            clerk.emit(
                task=NarrationTask.DECISION,
                role=CourtRole.STEWARD,
                disposition=TurnDisposition.ASSERTED,
                agent_id=_steward_id(binding.owner),
                round_no=ROUND_PRESENT,
                facts={
                    "owner": binding.owner,
                    "definition": binding.rule_text,
                    "ready_count": counts.get(binding.binding_id, 0),
                },
                fallback=(
                    f"{binding.owner} asserts its operational view: "
                    f"{counts.get(binding.binding_id, 0)} learners satisfy "
                    f"{binding.rule_text}"
                ),
                speaking_for=binding.owner,
                tool_calls=(f"read_executed_sql:{binding.binding_id}",),
                cited_evidence_ids=(evidence_id,) if evidence_id else (),
            )
        )
    return tuple(turns)


def investigator_plan_turn(clerk: CourtClerk, case: ReconciliationCase) -> DeliberationTurn:
    return clerk.emit(
        task=NarrationTask.AUDIT,
        role=CourtRole.INVESTIGATOR,
        disposition=TurnDisposition.ASSERTED,
        agent_id="InvestigatorPlanAgent",
        round_no=ROUND_PLAN,
        facts={"verdict": case.verdict, "bindings": len(case.binding_semantics)},
        fallback=(
            "Plan: inspect the already executed entity sets pairwise, including identity-level "
            "differences that equal headline counts can hide. Then bind every claim to the "
            "stored SQL evidence."
        ),
        tool_calls=("plan:pairwise_entity_set_review",),
    )


def evidence_review_turn(clerk: CourtClerk, case: ReconciliationCase) -> DeliberationTurn:
    impact = case.impact_assessment
    if case.verdict == "consistent":
        text = (
            "Evidence review confirmed that every executed definition selected the same entity "
            "set. The wording differs, but the operational meaning does not."
        )
    elif impact is not None and impact.false_positive_count:
        sample = ", ".join(impact.false_positive_entity_ids[:3])
        text = (
            f"Evidence review isolated {impact.false_positive_count} false-ready "
            f"{impact.entity_label}, including {sample}, with {impact.arr_delta:,.0f} "
            f"{impact.value_label}. These are stored results, not Court estimates."
        )
    elif impact is not None:
        text = (
            f"Evidence review confirmed a {impact.customer_count_delta} "
            f"{impact.entity_label} spread and {impact.arr_delta:,.0f} "
            f"{impact.value_label}."
        )
    else:
        text = "Evidence review confirmed that at least one executed entity set differs."
    return clerk.emit(
        task=NarrationTask.AUDIT,
        role=CourtRole.INVESTIGATOR,
        disposition=TurnDisposition.CONFIRMED,
        agent_id="EvidenceReviewAgent",
        round_no=ROUND_EVIDENCE,
        facts={"verdict": case.verdict, "evidence_count": len(case.evidence)},
        fallback=text,
        tool_calls=("read:stored_evidence", "compare:entity_ids"),
        cited_evidence_ids=tuple(record.evidence_id for record in case.evidence),
    )


def investigator_replan_turn(clerk: CourtClerk, case: ReconciliationCase) -> DeliberationTurn:
    equal_count_pairs: list[str] = []
    owners = {binding.binding_id: binding.owner for binding in case.binding_semantics}
    results = case.execution_results
    for index, left in enumerate(results):
        for right in results[index + 1 :]:
            if left.entity_count == right.entity_count and left.entity_ids != right.entity_ids:
                equal_count_pairs.append(
                    f"{owners.get(left.binding_id, left.binding_id)} and "
                    f"{owners.get(right.binding_id, right.binding_id)} "
                    f"both report {left.entity_count}"
                )
    return clerk.emit(
        task=NarrationTask.AUDIT,
        role=CourtRole.INVESTIGATOR,
        disposition=TurnDisposition.CONFIRMED,
        agent_id="InvestigatorReplanAgent",
        round_no=ROUND_REPLAN,
        facts={"equal_count_unequal_sets": equal_count_pairs},
        fallback=(
            "Replan triggered: "
            + "; ".join(equal_count_pairs)
            + ", but their learner identities differ. The Court therefore compares exact IDs, "
            "not equal totals, before cross-examination."
        ),
        tool_calls=("replan:equal_count_identity_check",),
        cited_evidence_ids=tuple(record.evidence_id for record in case.evidence),
    )


def skeptic_cross_examination_turns(
    clerk: CourtClerk,
    case: ReconciliationCase,
    challengeable: tuple[DefinitionBinding, ...],
) -> tuple[DeliberationTurn, ...]:
    evidence = _evidence_by_binding(case)
    candidate = canonical_candidate(case)
    sets = _entity_sets(case)
    turns: list[DeliberationTurn] = []
    for binding in challengeable:
        evidence_id = evidence.get(binding.binding_id)
        sample = _divergent_sample(case, binding)
        if candidate is not None and binding.binding_id == candidate.binding_id:
            challenge = (
                f"{binding.owner}, the engine proposed your definition as the candidate source. "
                "Defend the evidence for that scope, but acknowledge that only the configured "
                "authority can make it canonical."
            )
        elif candidate is not None and sets.get(binding.binding_id, frozenset()) > sets.get(
            candidate.binding_id, frozenset()
        ):
            challenge = (
                f"{binding.owner}, your view admits learners the proposed candidate excludes "
                f"(for example {sample}). Narrow the enterprise claim or justify those identities."
            )
        else:
            challenge = (
                f"{binding.owner}, your population differs from the proposed candidate "
                f"(for example {sample}). Explain whether this is an enterprise definition or "
                "a legitimate operational domain view."
            )
        turns.append(
            clerk.emit(
                task=NarrationTask.VERIFIER,
                role=CourtRole.SKEPTIC,
                disposition=TurnDisposition.CHALLENGED,
                agent_id="SkepticAgent",
                round_no=ROUND_CHALLENGE,
                facts={"owner": binding.owner, "divergent_sample": sample},
                fallback=challenge,
                speaking_for=binding.owner,
                cited_evidence_ids=(evidence_id,) if evidence_id else (),
            )
        )
    return tuple(turns)


def steward_response_turns(
    clerk: CourtClerk,
    case: ReconciliationCase,
    challengeable: tuple[DefinitionBinding, ...],
) -> tuple[DeliberationTurn, ...]:
    evidence = _evidence_by_binding(case)
    candidate = canonical_candidate(case)
    sets = _entity_sets(case)
    turns: list[DeliberationTurn] = []
    ambiguous = case.authority_assessment is None or case.authority_assessment.owner is None
    for binding in challengeable:
        evidence_id = evidence.get(binding.binding_id)
        if ambiguous:
            disposition = TurnDisposition.REFRAMED
            response = (
                f"{binding.owner} preserves its result as a named domain view. With no single "
                "configured authority, it does not claim the enterprise definition."
            )
        elif candidate is not None and binding.binding_id == candidate.binding_id:
            disposition = TurnDisposition.DEFENDED
            response = (
                f"{binding.owner} defends the candidate because its executed evidence applies "
                "the required learning and assessment gates. It does not self-approve: the "
                f"{case.authority_assessment.owner} retains the publication decision."
            )
        elif candidate is not None and sets.get(binding.binding_id, frozenset()) > sets.get(
            candidate.binding_id, frozenset()
        ):
            disposition = TurnDisposition.NARROWED
            response = (
                f"{binding.owner} narrows its claim: its population is valid for its operational "
                "mandate, but the extra cohort is not asserted as enterprise readiness."
            )
        else:
            disposition = TurnDisposition.REFRAMED
            response = (
                f"{binding.owner} reframes its result as a named operational view. It remains "
                "useful for local decisions without competing for the canonical enterprise term."
            )
        turns.append(
            clerk.emit(
                task=NarrationTask.DECISION,
                role=CourtRole.STEWARD,
                disposition=disposition,
                agent_id=_steward_id(binding.owner),
                round_no=ROUND_RESPOND,
                facts={"owner": binding.owner, "disposition": disposition.value},
                fallback=response,
                speaking_for=binding.owner,
                cited_evidence_ids=(evidence_id,) if evidence_id else (),
            )
        )
    return tuple(turns)


def skeptic_consensus_turn(clerk: CourtClerk, case: ReconciliationCase) -> DeliberationTurn:
    return clerk.emit(
        task=NarrationTask.VERIFIER,
        role=CourtRole.SKEPTIC,
        disposition=TurnDisposition.CONFIRMED,
        agent_id="SkepticConsensusAgent",
        round_no=ROUND_CHALLENGE,
        facts={"verdict": case.verdict},
        fallback=(
            "Cross-examination closes without a dispute: the exact executed entity sets are "
            "equal. The apparent disagreement is a wording decoy."
        ),
        cited_evidence_ids=tuple(record.evidence_id for record in case.evidence),
    )


def reflection_turn(
    clerk: CourtClerk,
    case: ReconciliationCase,
    responses: tuple[DeliberationTurn, ...],
) -> DeliberationTurn:
    dispositions = [turn.disposition.value for turn in responses]
    return clerk.emit(
        task=NarrationTask.VERIFIER,
        role=CourtRole.SKEPTIC,
        disposition=TurnDisposition.CONFIRMED,
        agent_id="ReflectionAgent",
        round_no=ROUND_REFLECT,
        facts={"dispositions": dispositions, "evidence_count": len(case.evidence)},
        fallback=(
            "Reflection: the record now distinguishes an evidence-backed candidate from narrower "
            "or operational domain views. No steward changed the verdict; the remaining question "
            "is solely whether configured authority permits a proposal."
        ),
        cited_evidence_ids=tuple(record.evidence_id for record in case.evidence),
    )


def authority_turn(clerk: CourtClerk, case: ReconciliationCase) -> DeliberationTurn:
    authority = case.authority_assessment
    owner = authority.owner if authority else None
    status = authority.status if authority else "missing"
    if owner:
        disposition = TurnDisposition.CONFIRMED
        text = (
            f"Authority is {status}. {owner} alone may approve the proposed canonical meaning. "
            "The Court records the recommendation but cannot merge it."
        )
    else:
        disposition = TurnDisposition.REFUSED
        text = (
            f"Authority is {status}. No single configured owner may approve a canonical meaning. "
            "Automatic reconciliation remains refused and every steward stays a domain view."
        )
    return clerk.emit(
        task=NarrationTask.DECISION,
        role=CourtRole.AUTHORITY,
        disposition=disposition,
        agent_id="AuthorityAgent",
        round_no=ROUND_AUTHORITY,
        facts={"status": status, "owner": owner},
        fallback=text,
    )


def orchestrator_closing(
    clerk: CourtClerk,
    case: ReconciliationCase,
    outcome: str,
) -> DeliberationTurn:
    statements = {
        "proposal": (
            "Ruling: the engine-proven conflict supports a draft proposal. Human owner approval "
            "is still required; the Court changed no evidence and published no verdict."
        ),
        "refusal": (
            "Ruling: the conflict is proven, but governance authority is unresolved. The Court "
            "preserves the refusal and routes the decision to humans."
        ),
        "no_action": (
            "Ruling: exact entity-set equality dismisses the apparent disagreement. No proposal "
            "is created."
        ),
    }
    return clerk.emit(
        task=NarrationTask.DECISION,
        role=CourtRole.ORCHESTRATOR,
        disposition=(
            TurnDisposition.REFUSED if outcome == "refusal" else TurnDisposition.CONFIRMED
        ),
        agent_id="CourtAuditAgent",
        round_no=ROUND_CLOSING,
        facts={"outcome": outcome, "verdict": case.verdict},
        fallback=statements[outcome],
    )
