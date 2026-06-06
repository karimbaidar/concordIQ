"""HTTP routes for the P2 Active Customer slice."""

from fastapi import APIRouter, HTTPException, Request, status

from concord.agents.coordinator import UnsupportedScenario
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
