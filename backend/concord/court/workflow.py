"""A genuine Microsoft Agent Framework workflow over one frozen reconciliation case."""

from __future__ import annotations

import hashlib
import json
from typing import Literal, Never

from agent_framework import Workflow, WorkflowBuilder, WorkflowContext, executor
from pydantic import BaseModel, ConfigDict

from concord.court.roles import (
    CourtClerk,
    authority_turn,
    challengeable_bindings,
    evidence_review_turn,
    investigator_plan_turn,
    investigator_replan_turn,
    needs_targeted_replan,
    orchestrator_closing,
    orchestrator_opening,
    reflection_turn,
    skeptic_consensus_turn,
    skeptic_cross_examination_turns,
    steward_response_turns,
    steward_turns,
)
from concord.court.transcript import (
    DeliberationTranscript,
    DeliberationTurn,
    TranscriptMode,
    content_digest,
    now_utc,
)
from concord.llm import LLMProvider
from concord.orchestration.casefile import ReconciliationCase

CourtOutcome = Literal["proposal", "refusal", "no_action"]


def earned_outcome(case: ReconciliationCase) -> CourtOutcome:
    """Read the outcome already earned by deterministic execution and authority."""
    if case.verdict == "consistent":
        return "no_action"
    if case.reconciliation_proposal is not None:
        return "proposal"
    if case.refusal_reason:
        return "refusal"
    return "no_action"


def truth_digest(case: ReconciliationCase) -> str:
    """Hash every engine-owned fact the Court is forbidden to change."""
    payload = {
        "run_id": str(case.run_id),
        "verdict": case.verdict,
        "verification_status": case.verification_status,
        "authority": (
            case.authority_assessment.model_dump(mode="json") if case.authority_assessment else None
        ),
        "proposal": (
            case.reconciliation_proposal.model_dump(mode="json")
            if case.reconciliation_proposal
            else None
        ),
        "refusal_reason": case.refusal_reason,
        "evidence": [record.model_dump(mode="json") for record in case.evidence],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class CourtWorkflowState(BaseModel):
    """Typed blackboard passed between Court executors."""

    model_config = ConfigDict(frozen=True)

    case: ReconciliationCase
    outcome: CourtOutcome
    engine_truth_digest: str
    turns: tuple[DeliberationTurn, ...] = ()
    workflow_trace: tuple[str, ...] = ()
    needs_replan: bool = False
    challenge_binding_ids: tuple[str, ...] = ()

    def advanced(
        self,
        agent_name: str,
        *,
        turns: tuple[DeliberationTurn, ...] = (),
        needs_replan: bool | None = None,
        challenge_binding_ids: tuple[str, ...] | None = None,
    ) -> CourtWorkflowState:
        updates: dict[str, object] = {
            "turns": (*self.turns, *turns),
            "workflow_trace": (*self.workflow_trace, agent_name),
        }
        if needs_replan is not None:
            updates["needs_replan"] = needs_replan
        if challenge_binding_ids is not None:
            updates["challenge_binding_ids"] = challenge_binding_ids
        return self.model_copy(update=updates)


def _clerk(llm: LLMProvider, state: CourtWorkflowState) -> CourtClerk:
    return CourtClerk(llm, start_turn_no=len(state.turns))


def build_semantic_court_workflow(llm: LLMProvider) -> Workflow:
    """Build the conditional Agent Framework graph for one Court invocation."""

    @executor(
        id="CourtCoordinatorAgent",
        input=ReconciliationCase,
        output=CourtWorkflowState,
    )
    async def coordinate(
        case: ReconciliationCase,
        ctx: WorkflowContext[CourtWorkflowState],
    ) -> None:
        opening = orchestrator_opening(CourtClerk(llm), case)
        await ctx.send_message(
            CourtWorkflowState(
                case=case,
                outcome=earned_outcome(case),
                engine_truth_digest=truth_digest(case),
                turns=(opening,),
                workflow_trace=("CourtCoordinatorAgent",),
            )
        )

    @executor(
        id="StewardPanelAgent",
        input=CourtWorkflowState,
        output=CourtWorkflowState,
    )
    async def hear_stewards(
        state: CourtWorkflowState,
        ctx: WorkflowContext[CourtWorkflowState],
    ) -> None:
        turns = steward_turns(_clerk(llm, state), state.case)
        await ctx.send_message(state.advanced("StewardPanelAgent", turns=turns))

    @executor(
        id="InvestigatorPlanAgent",
        input=CourtWorkflowState,
        output=CourtWorkflowState,
    )
    async def plan(
        state: CourtWorkflowState,
        ctx: WorkflowContext[CourtWorkflowState],
    ) -> None:
        turn = investigator_plan_turn(_clerk(llm, state), state.case)
        await ctx.send_message(state.advanced("InvestigatorPlanAgent", turns=(turn,)))

    @executor(
        id="EvidenceReviewAgent",
        input=CourtWorkflowState,
        output=CourtWorkflowState,
    )
    async def review(
        state: CourtWorkflowState,
        ctx: WorkflowContext[CourtWorkflowState],
    ) -> None:
        turn = evidence_review_turn(_clerk(llm, state), state.case)
        await ctx.send_message(
            state.advanced(
                "EvidenceReviewAgent",
                turns=(turn,),
                needs_replan=needs_targeted_replan(state.case),
            )
        )

    @executor(
        id="InvestigatorReplanAgent",
        input=CourtWorkflowState,
        output=CourtWorkflowState,
    )
    async def replan(
        state: CourtWorkflowState,
        ctx: WorkflowContext[CourtWorkflowState],
    ) -> None:
        turn = investigator_replan_turn(_clerk(llm, state), state.case)
        await ctx.send_message(
            state.advanced(
                "InvestigatorReplanAgent",
                turns=(turn,),
                needs_replan=False,
            )
        )

    @executor(
        id="CourtBranchAgent",
        input=CourtWorkflowState,
        output=CourtWorkflowState,
    )
    async def route_verdict(
        state: CourtWorkflowState,
        ctx: WorkflowContext[CourtWorkflowState],
    ) -> None:
        await ctx.send_message(state.advanced("CourtBranchAgent"))

    @executor(
        id="SkepticAgent",
        input=CourtWorkflowState,
        output=CourtWorkflowState,
    )
    async def cross_examine(
        state: CourtWorkflowState,
        ctx: WorkflowContext[CourtWorkflowState],
    ) -> None:
        challenged = challengeable_bindings(state.case)
        turns = skeptic_cross_examination_turns(_clerk(llm, state), state.case, challenged)
        await ctx.send_message(
            state.advanced(
                "SkepticAgent",
                turns=turns,
                challenge_binding_ids=tuple(binding.binding_id for binding in challenged),
            )
        )

    @executor(
        id="StewardResponseAgent",
        input=CourtWorkflowState,
        output=CourtWorkflowState,
    )
    async def hear_responses(
        state: CourtWorkflowState,
        ctx: WorkflowContext[CourtWorkflowState],
    ) -> None:
        challenged = tuple(
            binding
            for binding in state.case.binding_semantics
            if binding.binding_id in state.challenge_binding_ids
        )
        turns = steward_response_turns(_clerk(llm, state), state.case, challenged)
        await ctx.send_message(state.advanced("StewardResponseAgent", turns=turns))

    @executor(
        id="ReflectionAgent",
        input=CourtWorkflowState,
        output=CourtWorkflowState,
    )
    async def reflect(
        state: CourtWorkflowState,
        ctx: WorkflowContext[CourtWorkflowState],
    ) -> None:
        responses = tuple(
            turn
            for turn in state.turns
            if turn.agent_id.startswith("StewardAgent.") and turn.round_no > 1
        )
        turn = reflection_turn(_clerk(llm, state), state.case, responses)
        await ctx.send_message(state.advanced("ReflectionAgent", turns=(turn,)))

    @executor(
        id="SkepticConsensusAgent",
        input=CourtWorkflowState,
        output=CourtWorkflowState,
    )
    async def confirm_consensus(
        state: CourtWorkflowState,
        ctx: WorkflowContext[CourtWorkflowState],
    ) -> None:
        turn = skeptic_consensus_turn(_clerk(llm, state), state.case)
        await ctx.send_message(state.advanced("SkepticConsensusAgent", turns=(turn,)))

    @executor(
        id="AuthorityAgent",
        input=CourtWorkflowState,
        output=CourtWorkflowState,
    )
    async def resolve_authority(
        state: CourtWorkflowState,
        ctx: WorkflowContext[CourtWorkflowState],
    ) -> None:
        turn = authority_turn(_clerk(llm, state), state.case)
        await ctx.send_message(state.advanced("AuthorityAgent", turns=(turn,)))

    @executor(
        id="CourtAuditAgent",
        input=CourtWorkflowState,
        workflow_output=DeliberationTranscript,
    )
    async def audit(
        state: CourtWorkflowState,
        ctx: WorkflowContext[Never, DeliberationTranscript],
    ) -> None:
        closing = orchestrator_closing(_clerk(llm, state), state.case, state.outcome)
        final = state.advanced("CourtAuditAgent", turns=(closing,))
        if truth_digest(final.case) != final.engine_truth_digest:
            raise RuntimeError("Semantic Court attempted to alter engine-owned case facts.")
        if earned_outcome(final.case) != final.outcome:
            raise RuntimeError("Semantic Court outcome no longer matches the deterministic case.")
        evidence_ids = {record.evidence_id for record in final.case.evidence}
        cited_ids = {evidence_id for turn in final.turns for evidence_id in turn.cited_evidence_ids}
        if cited_ids != evidence_ids:
            raise RuntimeError(
                "Semantic Court citations do not exactly match the frozen case evidence."
            )
        authority = final.case.authority_assessment
        if authority is None:
            raise RuntimeError("Semantic Court lost the frozen authority assessment.")
        authority_turns = [turn for turn in final.turns if turn.agent_id == "AuthorityAgent"]
        if len(authority_turns) != 1:
            raise RuntimeError("Semantic Court did not produce exactly one authority ruling.")
        expected_disposition = "confirmed" if authority.owner is not None else "refused"
        if authority_turns[0].disposition.value != expected_disposition:
            raise RuntimeError("Semantic Court authority disposition contradicts the frozen case.")
        mode = (
            TranscriptMode.LIVE_CAPTURED
            if any(turn.provenance.generated for turn in final.turns)
            else TranscriptMode.DETERMINISTIC_FALLBACK
        )
        concept = final.case.resolved_concept
        concept_id = concept.concept_id if concept else ""
        digest = content_digest(
            source_run_id=final.case.run_id,
            term=final.case.request.term,
            concept_id=concept_id,
            verdict=final.case.verdict,
            outcome=final.outcome,
            authority_status=authority.status,
            authority_owner=authority.owner,
            source_evidence_ids=tuple(record.evidence_id for record in final.case.evidence),
            turns=final.turns,
            workflow_trace=final.workflow_trace,
        )
        await ctx.yield_output(
            DeliberationTranscript(
                source_run_id=final.case.run_id,
                term=final.case.request.term,
                concept_id=concept_id,
                verdict=final.case.verdict,
                outcome=final.outcome,
                authority_status=authority.status,
                authority_owner=authority.owner,
                source_evidence_ids=tuple(record.evidence_id for record in final.case.evidence),
                rounds=max(turn.round_no for turn in final.turns) + 1,
                turns=final.turns,
                mode=mode,
                captured_at=now_utc(),
                content_digest=digest,
                workflow_trace=final.workflow_trace,
            )
        )

    builder = WorkflowBuilder(
        start_executor=coordinate,
        max_iterations=20,
        name="ConcordIQSemanticCourtWorkflow",
        description="Adversarial deliberation over one frozen, verifier-approved case.",
        output_from=[audit],
    )
    builder.add_edge(coordinate, hear_stewards)
    builder.add_edge(hear_stewards, plan)
    builder.add_edge(plan, review)
    builder.add_edge(review, replan, condition=lambda state: state.needs_replan)
    builder.add_edge(review, route_verdict, condition=lambda state: not state.needs_replan)
    builder.add_edge(replan, route_verdict)
    builder.add_edge(
        route_verdict,
        cross_examine,
        condition=lambda state: state.case.verdict == "conflict",
    )
    builder.add_edge(
        route_verdict,
        confirm_consensus,
        condition=lambda state: state.case.verdict == "consistent",
    )
    builder.add_edge(cross_examine, hear_responses)
    builder.add_edge(hear_responses, reflect)
    builder.add_edge(reflect, resolve_authority)
    builder.add_edge(confirm_consensus, resolve_authority)
    builder.add_edge(resolve_authority, audit)
    return builder.build()
