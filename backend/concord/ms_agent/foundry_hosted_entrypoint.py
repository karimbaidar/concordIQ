"""Fail-closed Foundry Agent Service host and cloud-free smoke commands."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Engine

from concord.config import Settings
from concord.llm import create_llm_provider
from concord.ms_agent.tools import DEFAULT_PERIOD, select_provider
from concord.ms_agent.workflow import ConcordAgentWorkflow, normalize_workflow_mode
from concord.orchestration.casefile import ReconciliationCase
from concord.orchestration.runner import ReconciliationRunner
from concord.storage.db import create_database_engine
from concord.storage.repositories import ReconciliationRepository


class HostedSmokeResult(BaseModel):
    """Non-secret result emitted by the local Foundry protocol smoke test."""

    model_config = ConfigDict(frozen=True)

    provider_mode: str
    workflow_mode: str
    term: str
    verdict: str
    verification_status: str
    specialist_steps: int
    readiness_status: int
    response_status: int


@dataclass(slots=True)
class StatelessHostedWorkflowAgent:
    """Create a fresh Agent Framework workflow for each hosted response.

    Concord IQ reconciliations are independent casefiles. A fresh workflow avoids
    persisting application-specific Python objects in preview host checkpoints
    while preserving the complete Agent Framework execution for every request.
    """

    runner: ReconciliationRunner
    engine: Engine
    workflow_mode: str
    context_providers: tuple[object, ...] = ()

    def run(
        self,
        messages: Any = None,
        *,
        stream: bool = False,
        **kwargs: Any,
    ) -> Any:
        """Delegate one response to a newly built workflow agent."""
        kwargs.pop("options", None)
        if kwargs:
            unexpected = ", ".join(sorted(kwargs))
            raise TypeError(f"Unsupported hosted run options: {unexpected}")
        workflow_agent = (
            ConcordAgentWorkflow.from_runner(
                self.runner,
                mode=self.workflow_mode,
            )
            .build()
            .as_agent(
                name="Concord IQ",
                description=(
                    "Reconciles conflicting business definitions using governed "
                    "grounding and deterministic evidence."
                ),
            )
        )
        return workflow_agent.run(messages, stream=stream)

    async def __aenter__(self) -> StatelessHostedWorkflowAgent:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        self.engine.dispose()

    def close(self) -> None:
        """Release the database engine when no server lifecycle was started."""
        self.engine.dispose()


def build_hosted_agent(
    settings: Settings | None = None,
    *,
    provider: str = "auto",
    workflow_mode: str | None = None,
    initialize_storage: bool = False,
) -> StatelessHostedWorkflowAgent:
    """Build the hosted workflow for an explicit local, replay, or cloud mode."""
    active_settings = settings or Settings()
    if provider.strip().lower() not in {"local", "replay"}:
        active_settings.require_cloud_access("Foundry Agent Service")
    selected_provider = select_provider(active_settings, provider)
    selected_settings = active_settings.model_copy(
        update={
            "provider": selected_provider.mode.value,
            "agent_workflow_mode": normalize_workflow_mode(
                workflow_mode or active_settings.agent_workflow_mode
            ),
        }
    )
    engine = create_database_engine(selected_settings)
    repository = ReconciliationRepository(engine)
    if initialize_storage:
        repository.initialize()
    runner = ReconciliationRunner(
        provider=selected_provider,
        repository=repository,
        settings=selected_settings,
        llm_provider=create_llm_provider(selected_settings),
    )
    return StatelessHostedWorkflowAgent(
        runner=runner,
        engine=engine,
        workflow_mode=selected_settings.agent_workflow_mode,
    )


def build_responses_host(agent: StatelessHostedWorkflowAgent):
    """Wrap Concord IQ in Microsoft's OpenAI-compatible Responses host."""
    from agent_framework_foundry_hosting import ResponsesHostServer

    if not agent.runner.provider.uses_cloud:
        return ResponsesHostServer(agent, configure_observability=None)
    return ResponsesHostServer(agent)


def dry_run(
    settings: Settings | None = None,
    *,
    provider: str = "local",
    workflow_mode: str = "strict",
) -> dict[str, object]:
    """Construct the host and verify routes without opening a socket or database."""
    agent = build_hosted_agent(
        settings,
        provider=provider,
        workflow_mode=workflow_mode,
        initialize_storage=False,
    )
    try:
        host = build_responses_host(agent)
        routes = sorted(route.path for route in host.routes if getattr(route, "path", None))
        required_routes = {"/readiness", "/responses"}
        if not required_routes.issubset(routes):
            raise RuntimeError("Foundry Responses host is missing required protocol routes.")
        return {
            "status": "ready",
            "provider_mode": agent.runner.provider.mode.value,
            "workflow_mode": agent.workflow_mode,
            "cloud_enabled": agent.runner.settings.allow_cloud,
            "routes": routes,
        }
    finally:
        agent.close()


async def run_smoke(
    settings: Settings | None = None,
    *,
    provider: str = "local",
    workflow_mode: str = "strict",
    term: str = "Active Customer",
    period: str = DEFAULT_PERIOD,
) -> HostedSmokeResult:
    """Exercise readiness and `/responses` entirely in-process."""
    import httpx

    agent = build_hosted_agent(
        settings,
        provider=provider,
        workflow_mode=workflow_mode,
        initialize_storage=True,
    )
    host = build_responses_host(agent)
    transport = httpx.ASGITransport(app=host)
    message = json.dumps({"term": term, "period": period})
    async with (
        host.router.lifespan_context(host),
        httpx.AsyncClient(
            transport=transport,
            base_url="http://foundry-agent.local",
        ) as client,
    ):
        readiness = await client.get("/readiness")
        response = await client.post("/responses", json={"input": message})

    readiness.raise_for_status()
    response.raise_for_status()
    case = _case_from_response(response.json())
    if case.verification_status != "passed":
        raise RuntimeError(f"Hosted smoke verification ended {case.verification_status}.")
    if len(case.agent_trace) != 10:
        raise RuntimeError("Hosted smoke did not execute all ten specialist steps.")
    return HostedSmokeResult(
        provider_mode=agent.runner.provider.mode.value,
        workflow_mode=agent.workflow_mode,
        term=case.request.term,
        verdict=case.verdict,
        verification_status=case.verification_status,
        specialist_steps=len(case.agent_trace),
        readiness_status=readiness.status_code,
        response_status=response.status_code,
    )


def _case_from_response(payload: dict[str, Any]) -> ReconciliationCase:
    for output in payload.get("output", []):
        if output.get("type") != "message":
            continue
        for content in output.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                return ReconciliationCase.model_validate_json(content["text"])
    raise RuntimeError("Foundry Responses host returned no Concord IQ casefile.")


def main() -> None:
    """Run a dry-run, local protocol smoke, or the real fail-closed host."""
    parser = argparse.ArgumentParser(description="Run the Concord IQ Foundry Agent Service host.")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--dry-run", action="store_true")
    action.add_argument("--smoke", action="store_true")
    parser.add_argument("--provider", default="auto")
    parser.add_argument("--workflow-mode", choices=("fast", "strict"), default="strict")
    parser.add_argument("--term", default="Active Customer")
    parser.add_argument("--period", default=DEFAULT_PERIOD)
    parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8088")))
    args = parser.parse_args()

    if args.dry_run:
        print(
            json.dumps(
                dry_run(
                    provider=args.provider,
                    workflow_mode=args.workflow_mode,
                ),
                sort_keys=True,
            )
        )
        return
    if args.smoke:
        result = asyncio.run(
            run_smoke(
                provider=args.provider,
                workflow_mode=args.workflow_mode,
                term=args.term,
                period=args.period,
            )
        )
        print(result.model_dump_json())
        return

    agent = build_hosted_agent(
        provider=args.provider,
        workflow_mode=args.workflow_mode,
        initialize_storage=True,
    )
    build_responses_host(agent).run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
