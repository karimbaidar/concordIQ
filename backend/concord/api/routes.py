"""HTTP routes for deterministic local reconciliation."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from concord.agents.coordinator import UnsupportedScenario
from concord.demo import DEMO_SCENARIOS, get_demo_scenario
from concord.ms_agent import ConcordAgentWorkflow
from concord.orchestration.casefile import ReconciliationCase, ReconciliationRequest
from concord.orchestration.portfolio import ConcordScore, PortfolioScan, scan_portfolio
from concord.orchestration.runner import ReconciliationRunner
from concord.providers import QueryResult, provider_statuses
from concord.storage.repositories import (
    ProposalAlreadyDecided,
    ProposalDecisionResult,
    ProposalNotFound,
    UnauthorizedApprover,
)

router = APIRouter()


class ProposalDecisionRequest(BaseModel):
    """Who is approving or rejecting a governed Semantic-PR proposal."""

    approver: str


class AskRequest(BaseModel):
    """A natural-language business question for the chat surface."""

    question: str


class AskResponse(BaseModel):
    """An ontology-grounded answer plus the full reconciliation when available."""

    query: QueryResult
    case: ReconciliationCase | None = None


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
        "workflow_mode": _workflow(request).mode,
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


@router.post("/ask", response_model=AskResponse)
async def ask(payload: AskRequest, request: Request) -> AskResponse:
    """Resolve a business question to grounded meaning, then reconcile it."""
    runner = _runner(request)
    result = runner.provider.nl_query(payload.question)
    case: ReconciliationCase | None = None
    if result.matched and result.canonical_name:
        try:
            case = await _workflow(request).run(
                ReconciliationRequest(question=payload.question, term=result.canonical_name)
            )
        except UnsupportedScenario:
            case = None
    return AskResponse(query=result, case=case)


@router.get("/scan", response_model=PortfolioScan)
def scan(request: Request) -> PortfolioScan:
    """Autonomous portfolio sweep across every concept (read-only, cloud-free)."""
    runner = _runner(request)
    try:
        return scan_portfolio(runner.provider)
    except TypeError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error


@router.get("/score", response_model=ConcordScore)
def score(request: Request) -> ConcordScore:
    """The single Concord Score plus per-business-unit breakdown."""
    runner = _runner(request)
    try:
        return scan_portfolio(runner.provider).score
    except TypeError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error


@router.get("/proposals/{run_id}")
def proposal_state(run_id: UUID, request: Request) -> dict[str, object]:
    state = _runner(request).repository.get_proposal_state(run_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No governed proposal for run {run_id}.",
        )
    return state


@router.post("/proposals/{run_id}/approve", response_model=ProposalDecisionResult)
def approve_proposal(
    run_id: UUID,
    payload: ProposalDecisionRequest,
    request: Request,
) -> ProposalDecisionResult:
    return _decide(request, run_id, "approved", payload.approver)


@router.post("/proposals/{run_id}/reject", response_model=ProposalDecisionResult)
def reject_proposal(
    run_id: UUID,
    payload: ProposalDecisionRequest,
    request: Request,
) -> ProposalDecisionResult:
    return _decide(request, run_id, "rejected", payload.approver)


def _decide(
    request: Request,
    run_id: UUID,
    decision: str,
    approver: str,
) -> ProposalDecisionResult:
    repository = _runner(request).repository
    try:
        return repository.decide_proposal(run_id, decision=decision, approver=approver)  # type: ignore[arg-type]
    except ProposalNotFound as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ProposalAlreadyDecided as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(error)) from error
    except UnauthorizedApprover as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(error)) from error


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
