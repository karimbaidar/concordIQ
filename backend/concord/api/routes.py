"""HTTP routes for deterministic local reconciliation."""

import asyncio
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from concord.agents.coordinator import CoordinatorAgent, UnsupportedScenario
from concord.config import CloudAccessDisabled, Settings
from concord.demo import DEMO_SCENARIOS, get_demo_scenario
from concord.ms_agent import ConcordAgentWorkflow
from concord.orchestration.casefile import (
    AgentTraceStep,
    ReconciliationCase,
    ReconciliationRequest,
)
from concord.orchestration.portfolio import ConcordScore, PortfolioScan, scan_portfolio
from concord.orchestration.runner import ReconciliationRunner
from concord.orchestration.whatif import (
    WhatIfNotSupported,
    WhatIfRequest,
    WhatIfResult,
    reconcile_what_if,
)
from concord.providers import (
    FoundryHostedProvider,
    FoundryHostedResponseError,
    LocalProvider,
    ProviderNotConfigured,
    QueryResult,
    provider_statuses,
)
from concord.providers.base import ConceptNotFound
from concord.providers.cloud import CloudCallBudgetExceeded, CloudTransportError
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


class UngovernedTermRefusal(BaseModel):
    """A graceful, typed refusal when a term has no governed definition.

    Concord IQ never fabricates a definition for an unknown term. It refuses,
    explains why, and points to the governed terms it can actually reconcile.
    """

    refused: bool = True
    term: str
    reason: str
    known_terms: list[str]


def _runner(request: Request) -> ReconciliationRunner:
    runner = request.app.state.reconciliation_runner
    if runner is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This endpoint requires the in-process reconciliation runtime.",
        )
    return runner


def _workflow(request: Request) -> ConcordAgentWorkflow:
    workflow = request.app.state.agent_workflow
    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This endpoint requires the in-process reconciliation runtime.",
        )
    return workflow


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _hosted_runtime(request: Request) -> FoundryHostedProvider | None:
    return request.app.state.foundry_hosted_provider


def _known_terms(request: Request) -> list[str]:
    """The governed terms Concord IQ can actually reconcile (never fabricated)."""
    runner = request.app.state.reconciliation_runner
    provider = getattr(runner, "provider", None)
    if isinstance(provider, LocalProvider):
        return [
            concept.canonical_name
            for concept in provider.list_concepts()
            if concept.concept_id in CoordinatorAgent.supported_concepts
        ]
    return []


def _ungoverned_refusal(request: Request, term: str) -> UngovernedTermRefusal:
    """Build the typed refusal for a term with no governed definition."""
    return UngovernedTermRefusal(
        term=term,
        reason=(
            f"No governed definition for '{term}'. Concord IQ will not guess. "
            "Add it to the ontology to reconcile it."
        ),
        known_terms=_known_terms(request),
    )


@router.get("/health")
def health(request: Request) -> dict[str, object]:
    hosted = _hosted_runtime(request)
    if hosted is not None:
        llm_provider = request.app.state.llm_provider
        return {
            "status": "ok",
            "orchestration": "Microsoft Agent Framework",
            "workflow_mode": "strict",
            "provider": hosted.name,
            "provider_mode": hosted.mode.value,
            "runtime": hosted.name,
            "cloud_enabled": hosted.settings.allow_cloud,
            "data_type": hosted.data_type,
            "llm_provider": llm_provider.name,
            "llm_enabled": llm_provider.enabled,
            "llm_model": llm_provider.model,
        }
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
    return provider_statuses(_settings(request))


async def _run_case(payload: ReconciliationRequest, request: Request) -> ReconciliationCase:
    """Dispatch one reconciliation to the hosted runtime or in-process workflow.

    Raises ``UnsupportedScenario`` / ``ConceptNotFound`` for ungoverned terms; the
    public ``/analyze`` route turns those into a graceful, typed refusal. Hosted
    cloud failures are mapped to HTTP errors here so every caller is consistent.
    """
    hosted = _hosted_runtime(request)
    if hosted is not None:
        try:
            return await asyncio.to_thread(hosted.analyze, payload)
        except CloudAccessDisabled as error:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
        except (ProviderNotConfigured, CloudCallBudgetExceeded) as error:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
        except (FoundryHostedResponseError, CloudTransportError) as error:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    return await _workflow(request).run(payload)


@router.post("/analyze", response_model=ReconciliationCase | UngovernedTermRefusal)
@router.post("/reconcile", response_model=ReconciliationCase | UngovernedTermRefusal)
async def reconcile(
    payload: ReconciliationRequest,
    request: Request,
) -> ReconciliationCase | UngovernedTermRefusal:
    """Reconcile a governed term, or refuse gracefully when it is ungoverned.

    An unknown term is never an error and never a fabricated definition: it returns
    a typed refusal (HTTP 200) that names the governed terms Concord IQ can settle.
    """
    try:
        return await _run_case(payload, request)
    except (UnsupportedScenario, ConceptNotFound):
        return _ungoverned_refusal(request, payload.term)


@router.post("/reconcile/whatif", response_model=WhatIfResult)
def reconcile_whatif(payload: WhatIfRequest, request: Request) -> WhatIfResult:
    """Re-derive one copied local binding without persistence or governance."""
    runner = _runner(request)
    if not isinstance(runner.provider, LocalProvider):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="What-if exploration is available only in deterministic LocalProvider mode.",
        )
    period = ReconciliationRequest(
        question=f"Explore {payload.term} without changing governed state.",
        term=payload.term,
    ).period
    try:
        return reconcile_what_if(runner.provider, payload, period)
    except (LookupError, WhatIfNotSupported, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error


@router.post("/ask", response_model=AskResponse)
async def ask(payload: AskRequest, request: Request) -> AskResponse:
    """Resolve a business question to grounded meaning, then reconcile it."""
    hosted = _hosted_runtime(request)
    if hosted is not None:
        result = hosted.nl_query(payload.question)
        if not result.matched or not result.canonical_name:
            return AskResponse(query=result)
        case = await _run_case(
            ReconciliationRequest(question=payload.question, term=result.canonical_name),
            request,
        )
        return AskResponse(query=result, case=case)
    runner = _runner(request)
    result = runner.provider.nl_query(payload.question)
    case: ReconciliationCase | None = None
    if result.matched and result.canonical_name:
        try:
            case = await _workflow(request).run(
                ReconciliationRequest(question=payload.question, term=result.canonical_name)
            )
        except (UnsupportedScenario, ConceptNotFound):
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


@router.get("/runs/{run_id}/agent-trace", response_model=list[AgentTraceStep])
def agent_trace(run_id: UUID, request: Request) -> tuple[AgentTraceStep, ...]:
    trace = _runner(request).repository.get_agent_trace(run_id)
    if trace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No completed reconciliation run {run_id}.",
        )
    return trace


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
    return await _run_case(scenario.request(), request)
