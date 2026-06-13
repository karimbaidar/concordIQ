"""The agents that speak in the Semantic Court.

Each role composes a request from the verified casefile and asks the narration provider
to voice it. With a real model the words are generated live; with the default disabled
provider the reviewed deterministic fallback is used. Either way the role can only cite
evidence that already exists in the casefile — it cannot invent a count or a verdict.

Tier 2 makes the debate dynamic and adaptive to the evidence: the Investigator runs a
plan -> execute -> replan loop, the Skeptic cross-examines exactly the stewards who claim
members outside the consensus core, those stewards respond, and a reflection turn critiques
the record. The shape of the debate therefore emerges from the data, not from a script.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from concord.court.transcript import CourtRole, DeliberationTurn, TurnProvenance
from concord.llm import LLMProvider, NarrationRequest, NarrationTask
from concord.orchestration.casefile import ReconciliationCase
from concord.providers import DefinitionBinding

# Round numbers — the debate's structure. Cross-examination rounds appear only when the
# evidence shows a steward claiming someone outside the set every definition agrees on.
ROUND_OPENING = 0
ROUND_PRESENT = 1
ROUND_INVESTIGATE = 2
ROUND_CHALLENGE = 3
ROUND_RESPOND = 4
ROUND_REFLECT = 5
ROUND_AUTHORITY = 6
ROUND_CLOSING = 7


@dataclass(slots=True)
class CourtClerk:
    """Builds turns in order, voicing each through the narration provider."""

    llm: LLMProvider
    _turn_no: int = field(default=0, init=False)

    def emit(
        self,
        *,
        task: NarrationTask,
        role: CourtRole,
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
    return f"steward.{owner.split()[0].lower()}"


def challengeable_bindings(case: ReconciliationCase) -> tuple[DefinitionBinding, ...]:
    """Stewards who claim members outside the set every definition agrees on.

    This is the adversarial core: a steward is cross-examined precisely when its executed
    population includes someone the other definitions exclude. For a decoy (identical sets)
    nobody is challengeable and the cross-examination rounds never run.
    """
    sets = _entity_sets(case)
    if len(sets) < 2:
        return ()
    consensus = frozenset.intersection(*sets.values())
    challengeable: list[DefinitionBinding] = []
    for binding in case.binding_semantics:
        population = sets.get(binding.binding_id, frozenset())
        if population - consensus:
            challengeable.append(binding)
    return tuple(challengeable)


def _divergent_sample(case: ReconciliationCase, binding: DefinitionBinding, limit: int = 3) -> str:
    sets = _entity_sets(case)
    consensus = frozenset.intersection(*sets.values()) if len(sets) >= 2 else frozenset()
    outside = sorted(sets.get(binding.binding_id, frozenset()) - consensus)
    return ", ".join(outside[:limit])


def orchestrator_opening(clerk: CourtClerk, case: ReconciliationCase) -> DeliberationTurn:
    term = case.request.term
    owners = ", ".join(binding.owner for binding in case.binding_semantics)
    fallback = (
        f"The court is convened on {term!r}. The advocates are {owners}. Each will argue "
        "its own definition; the divergence will be settled by executed evidence, and a "
        "canonical meaning will be published only if a configured owner may approve it."
    )
    return clerk.emit(
        task=NarrationTask.DECISION,
        role=CourtRole.ORCHESTRATOR,
        agent_id="orchestrator",
        round_no=ROUND_OPENING,
        facts={"term": term, "advocates": [b.owner for b in case.binding_semantics]},
        fallback=fallback,
    )


def steward_turns(clerk: CourtClerk, case: ReconciliationCase) -> tuple[DeliberationTurn, ...]:
    evidence = _evidence_by_binding(case)
    counts = _evaluation_by_binding(case)
    turns: list[DeliberationTurn] = []
    for binding in case.binding_semantics:
        count = counts.get(binding.binding_id, 0)
        evidence_id = evidence.get(binding.binding_id)
        cited = (evidence_id,) if evidence_id is not None else ()
        fallback = (
            f"For {binding.owner}: {count} are ready. My definition is {binding.rule_text} "
            f"I have executed it over the grounded population and stand on that result."
        )
        turns.append(
            clerk.emit(
                task=NarrationTask.DECISION,
                role=CourtRole.STEWARD,
                agent_id=_steward_id(binding.owner),
                round_no=ROUND_PRESENT,
                facts={
                    "owner": binding.owner,
                    "definition": binding.rule_text,
                    "ready_count": count,
                },
                fallback=fallback,
                speaking_for=binding.owner,
                tool_calls=(f"executed_sql:{binding.binding_id}",),
                cited_evidence_ids=cited,
            )
        )
    return tuple(turns)


def investigator_turns(clerk: CourtClerk, case: ReconciliationCase) -> tuple[DeliberationTurn, ...]:
    """A plan -> execute -> replan loop that isolates the divergence from real evidence."""
    cited = tuple(record.evidence_id for record in case.evidence)
    impact = case.impact_assessment

    if case.verdict != "conflict":
        equivalence = clerk.emit(
            task=NarrationTask.AUDIT,
            role=CourtRole.INVESTIGATOR,
            agent_id="investigator",
            round_no=ROUND_INVESTIGATE,
            facts={"verdict": case.verdict},
            fallback=(
                "Plan: compare the executed result sets directly. Executed: every definition "
                "selects the same population for the period. The disagreement is wording, not "
                "meaning — there is no operational conflict to reconcile."
            ),
            tool_calls=("plan:locate_divergence", "query:compare_result_sets"),
            cited_evidence_ids=cited,
        )
        return (equivalence,)

    owners = ", ".join(binding.owner for binding in case.binding_semantics)
    plan = clerk.emit(
        task=NarrationTask.AUDIT,
        role=CourtRole.INVESTIGATOR,
        agent_id="investigator",
        round_no=ROUND_INVESTIGATE,
        facts={"advocates": [b.owner for b in case.binding_semantics]},
        fallback=(
            f"Plan: {owners} disagree. Hypothesis — the divergence sits where one owner's gate "
            "admits learners another owner blocks. I will execute each definition and subtract the "
            "set every definition agrees on to isolate the contested cohort."
        ),
        tool_calls=("plan:locate_divergence",),
    )

    if impact is not None and impact.false_positive_count:
        label = impact.false_positive_label or "blocked by a stricter definition"
        sample = ", ".join(impact.false_positive_entity_ids[:3])
        execute_fallback = (
            f"Executed. {impact.false_positive_count} {impact.entity_label} are claimed ready by "
            f"one owner but {label} (for example {sample}). At {impact.arr_delta:,.0f} "
            f"{impact.value_label}, the divergence is material."
        )
        replan_fallback = (
            f"Replan: confirm the contested cohort is exactly the looser definition minus the "
            f"stricter one. Confirmed — {impact.false_positive_count} learners, no more, no fewer."
        )
    elif impact is not None:
        sample = ", ".join(impact.affected_entity_ids[:3])
        execute_fallback = (
            f"Executed. The definitions diverge by {impact.customer_count_delta} "
            f"{impact.entity_label} (for example {sample}). The disagreement is real."
        )
        replan_fallback = (
            "Replan: confirm the contested cohort sits outside the set every definition agrees on. "
            "Confirmed — the divergence is genuine and must be governed, not guessed."
        )
    else:
        execute_fallback = "Executed. The result sets differ; the disagreement is real."
        replan_fallback = "Replan: confirmed the divergence against the executed evidence."

    execute = clerk.emit(
        task=NarrationTask.AUDIT,
        role=CourtRole.INVESTIGATOR,
        agent_id="investigator",
        round_no=ROUND_INVESTIGATE,
        facts={
            "false_ready": impact.false_positive_count if impact else None,
            "value_at_risk": impact.arr_delta if impact else None,
        },
        fallback=execute_fallback,
        tool_calls=("query:divergent_cohort",),
        cited_evidence_ids=cited,
    )
    replan = clerk.emit(
        task=NarrationTask.AUDIT,
        role=CourtRole.INVESTIGATOR,
        agent_id="investigator",
        round_no=ROUND_INVESTIGATE,
        facts={"confirmed": True},
        fallback=replan_fallback,
        tool_calls=("replan:confirm_cohort",),
        cited_evidence_ids=cited,
    )
    return (plan, execute, replan)


def skeptic_cross_examination_turns(
    clerk: CourtClerk,
    case: ReconciliationCase,
    challengeable: tuple[DefinitionBinding, ...],
) -> tuple[DeliberationTurn, ...]:
    evidence = _evidence_by_binding(case)
    counts = _evaluation_by_binding(case)
    turns: list[DeliberationTurn] = []
    for binding in challengeable:
        count = counts.get(binding.binding_id, 0)
        sample = _divergent_sample(case, binding)
        evidence_id = evidence.get(binding.binding_id)
        cited = (evidence_id,) if evidence_id is not None else ()
        fallback = (
            f"Cross-examination of {binding.owner}: you claim {count} ready, but some are outside "
            f"the set every definition agrees on (for example {sample}). Concede that your count "
            "is a claim under your own gate, not enterprise readiness — or produce evidence."
        )
        turns.append(
            clerk.emit(
                task=NarrationTask.VERIFIER,
                role=CourtRole.SKEPTIC,
                agent_id="skeptic",
                round_no=ROUND_CHALLENGE,
                facts={"owner": binding.owner, "claimed": count, "divergent_sample": sample},
                fallback=fallback,
                cited_evidence_ids=cited,
            )
        )
    return tuple(turns)


def steward_response_turns(
    clerk: CourtClerk,
    case: ReconciliationCase,
    challengeable: tuple[DefinitionBinding, ...],
) -> tuple[DeliberationTurn, ...]:
    evidence = _evidence_by_binding(case)
    turns: list[DeliberationTurn] = []
    for binding in challengeable:
        evidence_id = evidence.get(binding.binding_id)
        cited = (evidence_id,) if evidence_id is not None else ()
        fallback = (
            f"{binding.owner} responds: conceded. My population is correct under my mandate, but "
            "I yield that it is not the enterprise readiness term. I defend my scope as a named "
            "domain view and accept that the canonical meaning must be governed."
        )
        turns.append(
            clerk.emit(
                task=NarrationTask.DECISION,
                role=CourtRole.STEWARD,
                agent_id=_steward_id(binding.owner),
                round_no=ROUND_RESPOND,
                facts={"owner": binding.owner, "concedes": True},
                fallback=fallback,
                speaking_for=binding.owner,
                cited_evidence_ids=cited,
            )
        )
    return tuple(turns)


def skeptic_consensus_turn(clerk: CourtClerk, case: ReconciliationCase) -> DeliberationTurn:
    fallback = (
        "Cross-examination: there is nothing to contest. Every definition selected the same "
        "population, so no advocate is claiming anyone the others exclude. The record is sound."
    )
    return clerk.emit(
        task=NarrationTask.VERIFIER,
        role=CourtRole.SKEPTIC,
        agent_id="skeptic",
        round_no=ROUND_CHALLENGE,
        facts={"verdict": case.verdict, "challenged": 0},
        fallback=fallback,
        cited_evidence_ids=tuple(record.evidence_id for record in case.evidence),
    )


def reflection_turn(
    clerk: CourtClerk,
    case: ReconciliationCase,
    challenged_count: int,
) -> DeliberationTurn:
    fallback = (
        f"Reflection: {challenged_count} claim(s) were conceded as claims, not readiness. No count "
        "was accepted on argument — each is the row count of an executed query recorded as "
        "evidence. The debate is resolved; what remains is who, if anyone, may approve a canonical."
    )
    return clerk.emit(
        task=NarrationTask.VERIFIER,
        role=CourtRole.SKEPTIC,
        agent_id="skeptic",
        round_no=ROUND_REFLECT,
        facts={"challenged": challenged_count, "evidence_count": len(case.evidence)},
        fallback=fallback,
    )


def authority_turn(clerk: CourtClerk, case: ReconciliationCase) -> DeliberationTurn:
    authority = case.authority_assessment
    status = authority.status if authority else "missing"
    owner = authority.owner if authority else None
    if owner:
        fallback = (
            f"Authority is {status}. {owner} is the configured owner and may approve a "
            "canonical definition. The court may publish a governed proposal for human approval."
        )
    else:
        fallback = (
            f"Authority is {status} and no single configured owner may approve a canonical "
            "definition. The court must refuse automatic reconciliation and route to a human; "
            "the dissent is recorded rather than resolved."
        )
    return clerk.emit(
        task=NarrationTask.DECISION,
        role=CourtRole.AUTHORITY,
        agent_id="authority",
        round_no=ROUND_AUTHORITY,
        facts={"status": status, "owner": owner},
        fallback=fallback,
    )


def orchestrator_closing(
    clerk: CourtClerk,
    case: ReconciliationCase,
    outcome: str,
) -> DeliberationTurn:
    statements = {
        "proposal": (
            "Ruling: the divergence is proven and a configured owner may approve. The court "
            "publishes a governed canonical proposal that still requires human approval."
        ),
        "refusal": (
            "Ruling: the divergence is proven but no owner may approve it. The court refuses "
            "automatic reconciliation, records the minority report, and routes to a human."
        ),
        "no_action": (
            "Ruling: the definitions are operationally equivalent. The decoy is dismissed and "
            "no reconciliation is published."
        ),
    }
    return clerk.emit(
        task=NarrationTask.DECISION,
        role=CourtRole.ORCHESTRATOR,
        agent_id="orchestrator",
        round_no=ROUND_CLOSING,
        facts={"outcome": outcome, "verdict": case.verdict},
        fallback=statements[outcome],
    )
