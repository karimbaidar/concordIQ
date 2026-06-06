"""HTTP routes for deterministic local reconciliation."""

from fastapi import APIRouter, HTTPException, Request, status

from concord.agents.coordinator import UnsupportedScenario
from concord.demo import DEMO_SCENARIOS, get_demo_scenario
from concord.orchestration.casefile import ReconciliationCase, ReconciliationRequest
from concord.orchestration.runner import ReconciliationRunner

router = APIRouter()


def _runner(request: Request) -> ReconciliationRunner:
    return request.app.state.reconciliation_runner


@router.get("/health")
def health(request: Request) -> dict[str, object]:
    runner = _runner(request)
    return {
        "status": "ok",
        "provider": runner.provider.name,
        "cloud_enabled": runner.settings.allow_cloud,
        "data_type": "synthetic",
    }


@router.post("/reconcile", response_model=ReconciliationCase)
def reconcile(
    payload: ReconciliationRequest,
    request: Request,
) -> ReconciliationCase:
    try:
        return _runner(request).run(payload)
    except UnsupportedScenario as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error


@router.get("/demo/scenarios")
def demo_scenarios() -> list[dict[str, str]]:
    return [scenario.as_dict() for scenario in DEMO_SCENARIOS]


@router.post("/demo/run/{scenario_id}", response_model=ReconciliationCase)
def run_demo_scenario(
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
    return _runner(request).run(scenario.request())
