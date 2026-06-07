"""Microsoft Agent Framework workflows over Concord IQ deterministic tools."""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Literal, Never, cast

from agent_framework import Message, Workflow, WorkflowBuilder, WorkflowContext, executor
from pydantic import BaseModel, ConfigDict

from concord.config import Settings
from concord.llm import create_llm_provider
from concord.ms_agent.agents import SPECIALIST_AGENTS, SpecialistAgentNode
from concord.ms_agent.tools import (
    DEFAULT_PERIOD,
    ReconcileBusinessTerm,
    ReconcileRequest,
    ReconciliationStageTool,
    RunnerReconciliationTool,
    format_period,
    parse_period,
    reconcile_business_term,
    select_provider,
)
from concord.orchestration.casefile import ReconciliationCase, ReconciliationRequest
from concord.orchestration.runner import ReconciliationRunner
from concord.storage.db import create_database_engine
from concord.storage.repositories import ReconciliationRepository

AgentWorkflowMode = Literal["fast", "strict"]
WORKFLOW_PLAN = tuple(agent.name for agent in SPECIALIST_AGENTS)
STRICT_STAGE_METHODS = {
    "ConceptResolverAgent": "resolve_concept",
    "BindingInspectorAgent": "inspect_bindings",
    "ConflictHypothesisAgent": "hypothesize_conflicts",
    "DataExecutionAgent": "execute_definitions",
    "ImpactRankerAgent": "rank_impact",
    "AuthorityResolverAgent": "resolve_authority",
    "ReconciliationAgent": "reconcile_or_refuse",
    "SkepticalVerifierAgent": "verify",
}


def normalize_workflow_mode(mode: str) -> AgentWorkflowMode:
    """Validate the explicit fast/strict workflow selection."""
    normalized = mode.strip().lower()
    if normalized not in {"fast", "strict"}:
        raise ValueError("Agent workflow mode must be 'fast' or 'strict'.")
    return cast(AgentWorkflowMode, normalized)


class AgentWorkflowRequest(BaseModel):
    """Typed input accepted directly or through a hosted framework message."""

    model_config = ConfigDict(frozen=True)

    term: str
    question: str | None = None
    period: str = DEFAULT_PERIOD
    provider: str = "local"


class AgentWorkflowCasefile(BaseModel):
    """Typed blackboard passed between specialist workflow nodes."""

    model_config = ConfigDict(frozen=True)

    case: ReconciliationCase
    workflow_mode: AgentWorkflowMode
    workflow_plan: tuple[str, ...] = WORKFLOW_PLAN
    agent_trace: tuple[str, ...] = ()

    def visited(
        self,
        name: str,
        *,
        case: ReconciliationCase | None = None,
    ) -> AgentWorkflowCasefile:
        return self.model_copy(
            update={
                "case": case or self.case,
                "agent_trace": (*self.agent_trace, name),
            }
        )


class AgentWorkflowResult(BaseModel):
    """Terminal workflow output with a hosted-agent text representation."""

    model_config = ConfigDict(frozen=True)

    case: ReconciliationCase
    workflow_mode: AgentWorkflowMode
    workflow_plan: tuple[str, ...]
    agent_trace: tuple[str, ...]

    def __str__(self) -> str:
        return self.case.model_dump_json()


def _request_from_messages(messages: list[Message]) -> AgentWorkflowRequest:
    text = next((message.text for message in reversed(messages) if message.text), "")
    if not text:
        raise ValueError("Hosted requests must contain a business term or JSON payload.")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return AgentWorkflowRequest(term=text)
    if not isinstance(payload, dict):
        raise ValueError("Hosted JSON input must be an object.")
    return AgentWorkflowRequest.model_validate(payload)


def _normalize_request(
    request: AgentWorkflowRequest | list[Message],
) -> AgentWorkflowRequest:
    if isinstance(request, AgentWorkflowRequest):
        return request
    return _request_from_messages(request)


def _domain_request(request: AgentWorkflowRequest) -> ReconciliationRequest:
    return ReconciliationRequest(
        question=request.question or f"Why do our {request.term} definitions disagree?",
        term=request.term,
        period=parse_period(request.period),
    )


def _result(casefile: AgentWorkflowCasefile) -> AgentWorkflowResult:
    return AgentWorkflowResult(
        case=casefile.case,
        workflow_mode=casefile.workflow_mode,
        workflow_plan=casefile.workflow_plan,
        agent_trace=casefile.agent_trace,
    )


def _build_fast_coordinator(
    tool: ReconcileBusinessTerm,
    request_tool: ReconcileRequest | None,
):
    @executor(
        id="CoordinatorAgent",
        input=AgentWorkflowRequest | list[Message],
        output=AgentWorkflowCasefile,
    )
    async def coordinate(
        request: AgentWorkflowRequest | list[Message],
        ctx: WorkflowContext[AgentWorkflowCasefile],
    ) -> None:
        normalized = _normalize_request(request)
        if request_tool is None:
            case = await asyncio.to_thread(
                tool,
                normalized.term,
                normalized.period,
                normalized.provider,
            )
        else:
            case = await asyncio.to_thread(
                request_tool,
                _domain_request(normalized),
                normalized.provider,
            )
        SPECIALIST_AGENTS[0].inspect(case)
        await ctx.send_message(
            AgentWorkflowCasefile(
                case=case,
                workflow_mode="fast",
                agent_trace=(SPECIALIST_AGENTS[0].name,),
            )
        )

    return coordinate


def _build_fast_specialist(spec: SpecialistAgentNode):
    @executor(
        id=spec.name,
        input=AgentWorkflowCasefile,
        output=AgentWorkflowCasefile,
    )
    async def inspect_case(
        casefile: AgentWorkflowCasefile,
        ctx: WorkflowContext[AgentWorkflowCasefile],
    ) -> None:
        spec.inspect(casefile.case)
        await ctx.send_message(casefile.visited(spec.name))

    return inspect_case


def _build_fast_audit(spec: SpecialistAgentNode):
    @executor(
        id=spec.name,
        input=AgentWorkflowCasefile,
        workflow_output=AgentWorkflowResult,
    )
    async def audit_case(
        casefile: AgentWorkflowCasefile,
        ctx: WorkflowContext[Never, AgentWorkflowResult],
    ) -> None:
        spec.inspect(casefile.case)
        await ctx.yield_output(_result(casefile.visited(spec.name)))

    return audit_case


def _build_strict_coordinator(stage_tool: ReconciliationStageTool):
    @executor(
        id="CoordinatorAgent",
        input=AgentWorkflowRequest | list[Message],
        output=AgentWorkflowCasefile,
    )
    async def coordinate(
        request: AgentWorkflowRequest | list[Message],
        ctx: WorkflowContext[AgentWorkflowCasefile],
    ) -> None:
        normalized = _normalize_request(request)
        case = await asyncio.to_thread(
            stage_tool.create_case,
            _domain_request(normalized),
            normalized.provider,
        )
        SPECIALIST_AGENTS[0].inspect(case)
        await ctx.send_message(
            AgentWorkflowCasefile(
                case=case,
                workflow_mode="strict",
                agent_trace=(SPECIALIST_AGENTS[0].name,),
            )
        )

    return coordinate


def _build_strict_specialist(
    spec: SpecialistAgentNode,
    stage_tool: ReconciliationStageTool,
):
    method_name = STRICT_STAGE_METHODS[spec.name]
    stage = getattr(stage_tool, method_name)

    @executor(
        id=spec.name,
        input=AgentWorkflowCasefile,
        output=AgentWorkflowCasefile,
    )
    async def execute_stage(
        casefile: AgentWorkflowCasefile,
        ctx: WorkflowContext[AgentWorkflowCasefile],
    ) -> None:
        case = await asyncio.to_thread(stage, casefile.case)
        spec.inspect(case)
        await ctx.send_message(casefile.visited(spec.name, case=case))

    return execute_stage


def _build_strict_audit(
    spec: SpecialistAgentNode,
    stage_tool: ReconciliationStageTool,
):
    @executor(
        id=spec.name,
        input=AgentWorkflowCasefile,
        workflow_output=AgentWorkflowResult,
    )
    async def audit_case(
        casefile: AgentWorkflowCasefile,
        ctx: WorkflowContext[Never, AgentWorkflowResult],
    ) -> None:
        case = await asyncio.to_thread(stage_tool.audit, casefile.case)
        spec.inspect(case)
        await ctx.yield_output(_result(casefile.visited(spec.name, case=case)))

    return audit_case


def _assemble_workflow(coordinator, specialists: list, audit) -> Workflow:
    builder = WorkflowBuilder(
        start_executor=coordinator,
        name="ConcordIQReconciliationWorkflow",
        description="Governed semantic reconciliation over a typed casefile.",
        output_from=[audit],
    )
    previous = coordinator
    for specialist in specialists:
        builder.add_edge(previous, specialist)
        previous = specialist
    builder.add_edge(previous, audit)
    return builder.build()


def build_concord_workflow(
    tool: ReconcileBusinessTerm,
    request_tool: ReconcileRequest | None = None,
    *,
    mode: str = "fast",
    stage_tool: ReconciliationStageTool | None = None,
) -> Workflow:
    """Build a fresh fast or strict workflow because state is run-scoped."""
    workflow_mode = normalize_workflow_mode(mode)
    if workflow_mode == "strict":
        if stage_tool is None:
            raise ValueError("Strict workflow mode requires a deterministic stage tool.")
        coordinator = _build_strict_coordinator(stage_tool)
        specialists = [
            _build_strict_specialist(spec, stage_tool) for spec in SPECIALIST_AGENTS[1:-1]
        ]
        audit = _build_strict_audit(SPECIALIST_AGENTS[-1], stage_tool)
        return _assemble_workflow(coordinator, specialists, audit)

    coordinator = _build_fast_coordinator(tool, request_tool)
    specialists = [_build_fast_specialist(spec) for spec in SPECIALIST_AGENTS[1:-1]]
    audit = _build_fast_audit(SPECIALIST_AGENTS[-1])
    return _assemble_workflow(coordinator, specialists, audit)


class ConcordAgentWorkflow:
    """Application wrapper supporting stable fast and stage-owned strict modes."""

    def __init__(
        self,
        tool: ReconcileBusinessTerm = reconcile_business_term,
        *,
        default_provider: str = "local",
        request_tool: ReconcileRequest | None = None,
        stage_tool: ReconciliationStageTool | None = None,
        mode: str = "fast",
    ) -> None:
        self.tool = tool
        self.default_provider = default_provider
        self.request_tool = request_tool
        self.stage_tool = stage_tool
        self.mode = normalize_workflow_mode(mode)

    @classmethod
    def from_runner(
        cls,
        runner: ReconciliationRunner,
        *,
        mode: str | None = None,
    ) -> ConcordAgentWorkflow:
        runner_tool = RunnerReconciliationTool(runner)
        return cls(
            runner_tool.reconcile_business_term,
            default_provider=runner.provider.mode.value,
            request_tool=runner_tool.reconcile_request,
            stage_tool=runner_tool,
            mode=mode or runner.settings.agent_workflow_mode,
        )

    def build(self) -> Workflow:
        return build_concord_workflow(
            self.tool,
            self.request_tool,
            mode=self.mode,
            stage_tool=self.stage_tool,
        )

    async def run_result(
        self,
        request: ReconciliationRequest,
        *,
        provider: str | None = None,
    ) -> AgentWorkflowResult:
        workflow_request = AgentWorkflowRequest(
            term=request.term,
            question=request.question,
            period=format_period(request.period),
            provider=provider or self.default_provider,
        )
        run_result = await self.build().run(workflow_request)
        outputs = [
            output for output in run_result.get_outputs() if isinstance(output, AgentWorkflowResult)
        ]
        if len(outputs) != 1:
            raise RuntimeError("Concord IQ workflow did not produce exactly one casefile.")
        return outputs[0]

    async def run(
        self,
        request: ReconciliationRequest,
        *,
        provider: str | None = None,
    ) -> ReconciliationCase:
        return (await self.run_result(request, provider=provider)).case


async def _smoke(args: argparse.Namespace) -> None:
    settings = Settings()
    mode = normalize_workflow_mode(args.workflow_mode or settings.agent_workflow_mode)
    selected_provider = select_provider(settings, args.provider)
    active_settings = settings.model_copy(
        update={
            "provider": selected_provider.mode.value,
            "agent_workflow_mode": mode,
        }
    )
    engine = create_database_engine(active_settings)
    repository = ReconciliationRepository(engine)
    repository.initialize()
    runner = ReconciliationRunner(
        provider=selected_provider,
        repository=repository,
        settings=active_settings,
        llm_provider=create_llm_provider(active_settings),
    )
    request = ReconciliationRequest(
        question=f"Why do our {args.term} definitions disagree?",
        term=args.term,
        period=parse_period(args.period),
    )
    try:
        result = await ConcordAgentWorkflow.from_runner(runner, mode=mode).run_result(
            request,
            provider=selected_provider.mode.value,
        )
    finally:
        engine.dispose()
    print(
        f"{result.case.resolved_concept.canonical_name}: "
        f"{result.case.verdict.upper()} | workflow={result.workflow_mode} "
        f"| provider={args.provider} | run_id={result.case.run_id}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Concord IQ Agent Framework smoke test.")
    parser.add_argument("--term", default="Active Customer")
    parser.add_argument("--period", default=DEFAULT_PERIOD)
    parser.add_argument("--provider", default="local")
    parser.add_argument("--workflow-mode", choices=("fast", "strict"))
    args = parser.parse_args()
    asyncio.run(_smoke(args))


if __name__ == "__main__":
    main()
