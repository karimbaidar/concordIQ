"""HTTP routes for deterministic local reconciliation."""

from fastapi import APIRouter, HTTPException, Request, status

from concord.agents.coordinator import UnsupportedScenario
from concord.demo import DEMO_SCENARIOS, get_demo_scenario
from concord.ms_agent import ConcordAgentWorkflow
from concord.orchestration.casefile import ReconciliationCase, ReconciliationRequest
from concord.orchestration.runner import ReconciliationRunner
from concord.providers import provider_statuses

router = APIRouter()


def _runner(request: Request) -> ReconciliationRunner:
    return request.app.state.reconciliation_runner


def _workflow(request: Request) -> ConcordAgentWorkflow:
    return request.app.state.agent_workflow


@router.get("/health")
def health(request: Request) -> dict[str, object]:
    runner = _runner(request)
    return {
        "status": "ok",
        "orchestration": "Microsoft Agent Framework",
        "provider": runner.provider.name,
        "cloud_enabled": runner.settings.allow_cloud,
        "data_type": getattr(runner.provider, "data_type", "synthetic"),
        "llm_provider": runner.llm_provider.name,
        "llm_enabled": runner.llm_provider.enabled,
        "llm_model": runner.llm_provider.model,
    }


@router.get("/providers")
def providers(request: Request) -> list[dict[str, object]]:
    """Expose readiness without probing any cloud endpoint."""
    return provider_statuses(_runner(request).settings)


@router.post("/reconcile", response_model=ReconciliationCase)
async def reconcile(
    payload: ReconciliationRequest,
    request: Request,
) -> ReconciliationCase:
    try:
        return await _workflow(request).run(payload)
    except UnsupportedScenario as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error


@router.get("/demo/scenarios")
def demo_scenarios() -> list[dict[str, str]]:
    return [scenario.as_dict() for scenario in DEMO_SCENARIOS]


@router.post("/demo/run/{scenario_id}", response_model=ReconciliationCase)
async def run_demo_scenario(
    scenario_id: str,
    request: Request,
) -> ReconciliationCase:
    try:
        scenario = get_demo_scenario(scenario_id)
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown demo scenario: {scenario_id}",
        ) from error
    return await _workflow(request).run(scenario.request())
