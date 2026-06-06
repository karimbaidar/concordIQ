"""Microsoft Agent Framework workflow over the Concord IQ domain tool."""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Never

from agent_framework import Message, Workflow, WorkflowBuilder, WorkflowContext, executor
from pydantic import BaseModel, ConfigDict

from concord.ms_agent.agents import SPECIALIST_AGENTS, SpecialistAgentNode
from concord.ms_agent.tools import (
    DEFAULT_PERIOD,
    ReconcileBusinessTerm,
    ReconcileRequest,
    RunnerReconciliationTool,
    format_period,
    parse_period,
    reconcile_business_term,
)
from concord.orchestration.casefile import ReconciliationCase, ReconciliationRequest
from concord.orchestration.runner import ReconciliationRunner


class AgentWorkflowRequest(BaseModel):
    """Typed input accepted directly or through a hosted Agent Framework message."""

    model_config = ConfigDict(frozen=True)

    term: str
    question: str | None = None
    period: str = DEFAULT_PERIOD
    provider: str = "local"


class AgentWorkflowCasefile(BaseModel):
    """Typed casefile passed between specialist workflow nodes."""

    model_config = ConfigDict(frozen=True)

    case: ReconciliationCase
    agent_trace: tuple[str, ...] = ()

    def visited(self, name: str) -> AgentWorkflowCasefile:
        return self.model_copy(update={"agent_trace": (*self.agent_trace, name)})


class AgentWorkflowResult(BaseModel):
    """Terminal workflow output with a hosted-agent text representation."""

    model_config = ConfigDict(frozen=True)

    case: ReconciliationCase
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


def _build_coordinator(
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
                ReconciliationRequest(
                    question=normalized.question
                    or f"Why do our {normalized.term} definitions disagree?",
                    term=normalized.term,
                    period=parse_period(normalized.period),
                ),
                normalized.provider,
            )
        SPECIALIST_AGENTS[0].inspect(case)
        await ctx.send_message(
            AgentWorkflowCasefile(
                case=case,
                agent_trace=(SPECIALIST_AGENTS[0].name,),
            )
        )

    return coordinate


def _build_specialist(spec: SpecialistAgentNode):
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


def _build_audit(spec: SpecialistAgentNode):
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
        completed = casefile.visited(spec.name)
        await ctx.yield_output(
            AgentWorkflowResult(
                case=completed.case,
                agent_trace=completed.agent_trace,
            )
        )

    return audit_case


def build_concord_workflow(
    tool: ReconcileBusinessTerm,
    request_tool: ReconcileRequest | None = None,
) -> Workflow:
    """Build a fresh framework workflow because workflow state is run-scoped."""
    coordinator = _build_coordinator(tool, request_tool)
    specialists = [_build_specialist(spec) for spec in SPECIALIST_AGENTS[1:-1]]
    audit = _build_audit(SPECIALIST_AGENTS[-1])
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


class ConcordAgentWorkflow:
    """Application-facing wrapper around a Microsoft Agent Framework workflow."""

    def __init__(
        self,
        tool: ReconcileBusinessTerm = reconcile_business_term,
        *,
        default_provider: str = "local",
        request_tool: ReconcileRequest | None = None,
    ) -> None:
        self.tool = tool
        self.default_provider = default_provider
        self.request_tool = request_tool

    @classmethod
    def from_runner(cls, runner: ReconciliationRunner) -> ConcordAgentWorkflow:
        runner_tool = RunnerReconciliationTool(runner)
        return cls(
            runner_tool.reconcile_business_term,
            default_provider=runner.provider.mode.value,
            request_tool=runner_tool.reconcile_request,
        )

    def build(self) -> Workflow:
        return build_concord_workflow(self.tool, self.request_tool)

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
    request = ReconciliationRequest(
        question=f"Why do our {args.term} definitions disagree?",
        term=args.term,
        period=parse_period(args.period),
    )
    case = await ConcordAgentWorkflow(default_provider=args.provider).run(
        request,
        provider=args.provider,
    )
    print(
        f"{case.resolved_concept.canonical_name}: {case.verdict.upper()} "
        f"| provider={args.provider} | run_id={case.run_id}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Concord IQ Agent Framework smoke test.")
    parser.add_argument("--term", default="Active Customer")
    parser.add_argument("--period", default=DEFAULT_PERIOD)
    parser.add_argument("--provider", default="local")
    args = parser.parse_args()
    asyncio.run(_smoke(args))


if __name__ == "__main__":
    main()
