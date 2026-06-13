"""The agents that speak in the Semantic Court.

Each role composes a request from the verified casefile and asks the narration provider
to voice it. With a real model the words are generated live; with the default disabled
provider the reviewed deterministic fallback is used. Either way the role can only cite
evidence that already exists in the casefile — it cannot invent a count or a verdict.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from concord.court.transcript import CourtRole, DeliberationTurn, TurnProvenance
from concord.llm import LLMProvider, NarrationRequest, NarrationTask
from concord.orchestration.casefile import ReconciliationCase


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
        round_no=0,
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
                agent_id=f"steward.{binding.owner.split()[0].lower()}",
                round_no=1,
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


def investigator_turn(clerk: CourtClerk, case: ReconciliationCase) -> DeliberationTurn:
    cited = tuple(record.evidence_id for record in case.evidence)
    impact = case.impact_assessment
    if case.verdict != "conflict":
        fallback = (
            "I executed every definition and compared the result sets directly. They select "
            "the same population for the period, so the disagreement is wording, not meaning. "
            "There is no operational conflict to reconcile."
        )
    elif impact is not None and impact.false_positive_count:
        label = impact.false_positive_label or "blocked by a stricter definition"
        sample = ", ".join(impact.false_positive_entity_ids[:3])
        fallback = (
            f"The definitions diverge. {impact.false_positive_count} {impact.entity_label} are "
            f"claimed ready by one owner but {label} (for example {sample}). At "
            f"{impact.arr_delta:,.0f} {impact.value_label}, the divergence is material."
        )
    elif impact is not None:
        sample = ", ".join(impact.affected_entity_ids[:3])
        fallback = (
            f"The definitions diverge by {impact.customer_count_delta} {impact.entity_label} "
            f"(for example {sample}). The disagreement is real and must be governed, not guessed."
        )
    else:
        fallback = "The executed result sets differ; the disagreement is real."
    return clerk.emit(
        task=NarrationTask.AUDIT,
        role=CourtRole.INVESTIGATOR,
        agent_id="investigator",
        round_no=2,
        facts={
            "verdict": case.verdict,
            "false_ready": impact.false_positive_count if impact else None,
            "value_at_risk": impact.arr_delta if impact else None,
        },
        fallback=fallback,
        tool_calls=("query:divergent_cohort",),
        cited_evidence_ids=cited,
    )


def skeptic_turn(clerk: CourtClerk, case: ReconciliationCase) -> DeliberationTurn:
    cited = tuple(record.evidence_id for record in case.evidence)
    fallback = (
        "Cross-examination: no advocate's wording is accepted on assertion. Each count here "
        "is the row count of an executed query over grounded data, recorded as evidence. The "
        "verdict stands on that evidence alone — not on the most persuasive argument."
    )
    return clerk.emit(
        task=NarrationTask.VERIFIER,
        role=CourtRole.SKEPTIC,
        agent_id="skeptic",
        round_no=3,
        facts={"evidence_count": len(case.evidence), "verdict": case.verdict},
        fallback=fallback,
        cited_evidence_ids=cited,
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
        round_no=4,
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
        round_no=5,
        facts={"outcome": outcome, "verdict": case.verdict},
        fallback=statements[outcome],
    )
