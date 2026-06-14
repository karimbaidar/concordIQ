"""HTTP routes for deterministic local reconciliation."""

import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from concord.agents.coordinator import CoordinatorAgent, UnsupportedScenario
from concord.config import CloudAccessDisabled, ScenarioPack, Settings
from concord.court import (
    CourtNotReady,
    DeliberationTranscript,
    SemanticCourt,
)
from concord.demo import (
    demo_scenarios_for_pack,
    demo_scenarios_for_provider,
    get_demo_scenario,
)
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
from concord.runtime import (
    RuntimeManager,
    RuntimeProfile,
    RuntimeSelectionError,
    RuntimeState,
)
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


class RuntimeSelectionRequest(BaseModel):
    """Ephemeral reviewer selection of a semantic system and proof runtime."""

    scenario_pack: ScenarioPack
    runtime_profile: RuntimeProfile


class UngovernedTermRefusal(BaseModel):
    """A graceful, typed refusal when a term has no governed definition.

    Concord IQ never fabricates a definition for an unknown term. It refuses,
    explains why, and points to the governed terms it can actually reconcile.
    """

    refused: bool = True
    term: str
    reason: str
    known_terms: list[str]


class LearningScaleProof(BaseModel):
    """Committed Fabric-bound scale artifact, separate from the workbench run."""

    canonical_term: str
    entity_type: str
    learner_count: int
    certification_ready_count: int
    false_ready_blocked_count: int
    proof_kind: str = "fabric_bound_scale_artifact"
    execution_separation: str = "Separate from the 120-learner deterministic workbench execution."


def _runtime_manager(request: Request) -> RuntimeManager:
    return request.app.state.runtime_manager


def _runner(request: Request) -> ReconciliationRunner:
    runner = _runtime_manager(request).context.runner
    if runner is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This endpoint requires the in-process reconciliation runtime.",
        )
    return runner


def _workflow(request: Request) -> ConcordAgentWorkflow:
    workflow = _runtime_manager(request).context.workflow
    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This endpoint requires the in-process reconciliation runtime.",
        )
    return workflow


def _settings(request: Request) -> Settings:
    return _runtime_manager(request).context.settings


def _hosted_runtime(request: Request) -> FoundryHostedProvider | None:
    return _runtime_manager(request).context.hosted


def _active_scenario_pack(request: Request) -> ScenarioPack:
    return _runtime_manager(request).scenario_pack


def _active_demo_scenarios(request: Request):
    runner = _runtime_manager(request).context.runner
    if runner is not None:
        return demo_scenarios_for_provider(runner.provider)
    return demo_scenarios_for_pack(_active_scenario_pack(request))


def _portfolio_provider(request: Request) -> LocalProvider:
    """Build the read-only deterministic registry view for the active system."""
    return LocalProvider.for_scenario_pack(
        _active_scenario_pack(request),
        duckdb_path=_runtime_manager(request).base_settings.duckdb_path,
    )


def _known_terms(request: Request) -> list[str]:
    """The governed terms Concord IQ can actually reconcile (never fabricated)."""
    runner = _runtime_manager(request).context.runner
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
    runtime = _runtime_manager(request)
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
            "scenario_pack": _active_scenario_pack(request).value,
            "runtime_profile": runtime.runtime_profile.value,
        }
    runner = _runner(request)
    return {
        "status": "ok",
        "orchestration": "Microsoft Agent Framework",
        "workflow_mode": _workflow(request).mode,
        "provider": runner.provider.name,
        "provider_mode": runner.provider.mode.value,
        "cloud_enabled": runner.settings.allow_cloud,
        "data_type": getattr(runner.provider, "data_type", "synthetic"),
        "llm_provider": runner.llm_provider.name,
        "llm_enabled": runner.llm_provider.enabled,
        "llm_model": runner.llm_provider.model,
        "scenario_pack": _active_scenario_pack(request).value,
        "runtime_profile": runtime.runtime_profile.value,
    }


@router.get("/runtime", response_model=RuntimeState)
def runtime_state(request: Request) -> RuntimeState:
    """Return the current demo runtime and all honestly available choices."""
    return _runtime_manager(request).state()


@router.post("/runtime/select", response_model=RuntimeState)
def select_runtime(
    payload: RuntimeSelectionRequest,
    request: Request,
) -> RuntimeState:
    """Switch the single-user demo process without persisting governance state."""
    manager = _runtime_manager(request)
    try:
        selected = manager.activate(payload.runtime_profile, payload.scenario_pack)
    except RuntimeSelectionError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    context = manager.context
    request.app.state.settings = context.settings
    request.app.state.reconciliation_runner = context.runner
    request.app.state.agent_workflow = context.workflow
    request.app.state.foundry_hosted_provider = context.hosted
    return selected


@router.get("/providers")
def providers(request: Request) -> list[dict[str, object]]:
    """Expose readiness without probing any cloud endpoint."""
    return provider_statuses(_runtime_manager(request).base_settings)


async def _run_case(payload: ReconciliationRequest, request: Request) -> ReconciliationCase:
    """Dispatch one reconciliation to the hosted runtime or in-process workflow.

    Raises ``UnsupportedScenario`` / ``ConceptNotFound`` for ungoverned terms; the
    public ``/analyze`` route turns those into a graceful, typed refusal. Hosted
    cloud failures are mapped to HTTP errors here so every caller is consistent.
    """
    manager = _runtime_manager(request)
    hosted = _hosted_runtime(request)
    if hosted is not None:
        try:
            case = await asyncio.to_thread(hosted.analyze, payload)
        except CloudAccessDisabled as error:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
        except (ProviderNotConfigured, CloudCallBudgetExceeded) as error:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
        except (FoundryHostedResponseError, CloudTransportError) as error:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
        return manager.remember_case(case, import_to_registry=True)
    case = await _workflow(request).run(payload)
    return manager.remember_case(case)


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
            case = await _run_case(
                ReconciliationRequest(question=payload.question, term=result.canonical_name),
                request,
            )
        except (UnsupportedScenario, ConceptNotFound):
            case = None
    return AskResponse(query=result, case=case)


@router.get("/scan", response_model=PortfolioScan)
def scan(request: Request) -> PortfolioScan:
    """Autonomous portfolio sweep across every concept (read-only, cloud-free)."""
    try:
        return scan_portfolio(_portfolio_provider(request))
    except TypeError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error


@router.get("/score", response_model=ConcordScore)
def score(request: Request) -> ConcordScore:
    """The single Concord Score plus per-business-unit breakdown."""
    try:
        return scan_portfolio(_portfolio_provider(request)).score
    except TypeError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error


@router.get("/proposals/{run_id}")
def proposal_state(run_id: UUID, request: Request) -> dict[str, object]:
    state = _runtime_manager(request).repository.get_proposal_state(run_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No governed proposal for run {run_id}.",
        )
    return state


@router.get("/runs/{run_id}/agent-trace", response_model=list[AgentTraceStep])
def agent_trace(run_id: UUID, request: Request) -> tuple[AgentTraceStep, ...]:
    trace = _runtime_manager(request).repository.get_agent_trace(run_id)
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
    repository = _runtime_manager(request).repository
    try:
        return repository.decide_proposal(run_id, decision=decision, approver=approver)  # type: ignore[arg-type]
    except ProposalNotFound as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ProposalAlreadyDecided as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(error)) from error
    except UnauthorizedApprover as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(error)) from error


@router.get("/demo/scenarios")
def demo_scenarios(request: Request) -> list[dict[str, str]]:
    return [scenario.as_dict() for scenario in _active_demo_scenarios(request)]


@router.post("/demo/run/{scenario_id}", response_model=ReconciliationCase)
async def run_demo_scenario(
    scenario_id: str,
    request: Request,
) -> ReconciliationCase:
    try:
        scenario = get_demo_scenario(scenario_id, _active_demo_scenarios(request))
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown demo scenario: {scenario_id}",
        ) from error
    return await _run_case(scenario.request(), request)


@router.post("/runs/{run_id}/court", response_model=DeliberationTranscript)
async def run_court(run_id: UUID, request: Request) -> DeliberationTranscript:
    """Convene the Agent Framework Court over one frozen verified case."""
    cached = _runtime_manager(request).cached_case(run_id)
    if cached is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "This completed run is no longer available in the reviewer cache. "
                "Run the reconciliation again before convening the court."
            ),
        )
    try:
        return await SemanticCourt(request.app.state.llm_provider).deliberate_async(cached.case)
    except CourtNotReady as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


@router.post("/runs/{run_id}/governed-rerun", response_model=ReconciliationCase)
async def governed_rerun(run_id: UUID, request: Request) -> ReconciliationCase:
    """Re-run a cached term through the local governed registry only."""
    manager = _runtime_manager(request)
    cached = manager.cached_case(run_id)
    if cached is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "This completed run is no longer available for a governed re-run. "
                "Run the reconciliation again."
            ),
        )
    workflow = manager.local_workflow(cached.scenario_pack)
    case = await workflow.run(cached.case.request)
    return manager.remember_case(case)


@router.get("/proof/learning-scale", response_model=LearningScaleProof)
def learning_scale_proof(request: Request) -> LearningScaleProof:
    """Return the committed 10K Fabric scale proof with an explicit separation label."""
    path = _runtime_manager(request).base_settings.learning_scale_summary_path
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Learning scale proof is unavailable: {path}.",
        ) from error
    return LearningScaleProof.model_validate(document)
