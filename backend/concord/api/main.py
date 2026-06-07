"""FastAPI application factory with injectable deterministic dependencies."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import Engine

from concord.api.routes import router
from concord.config import Settings
from concord.llm import LLMProvider, create_llm_provider
from concord.ms_agent import ConcordAgentWorkflow
from concord.orchestration.runner import ReconciliationRunner
from concord.providers import (
    FoundryHostedProvider,
    GroundingProvider,
    ProviderMode,
    create_provider,
)
from concord.storage.db import create_database_engine
from concord.storage.repositories import ReconciliationRepository


def create_app(
    settings: Settings | None = None,
    *,
    provider: GroundingProvider | None = None,
    foundry_hosted_provider: FoundryHostedProvider | None = None,
    llm_provider: LLMProvider | None = None,
    engine: Engine | None = None,
) -> FastAPI:
    """Create an app using local, cloud-disabled defaults unless injected."""
    active_settings = settings or Settings()
    active_llm_provider = llm_provider or create_llm_provider(active_settings)
    hosted_mode = active_settings.provider.strip().lower() == ProviderMode.FOUNDRY_HOSTED

    runner: ReconciliationRunner | None = None
    agent_workflow: ConcordAgentWorkflow | None = None
    repository: ReconciliationRepository | None = None
    hosted_runtime: FoundryHostedProvider | None = None
    if hosted_mode:
        if provider is not None:
            raise ValueError("Inject foundry_hosted_provider when PROVIDER=foundry_hosted.")
        hosted_runtime = foundry_hosted_provider or FoundryHostedProvider(active_settings)
    else:
        active_provider = provider or create_provider(active_settings)
        active_engine = engine or create_database_engine(active_settings)
        repository = ReconciliationRepository(active_engine)
        runner = ReconciliationRunner(
            provider=active_provider,
            repository=repository,
            settings=active_settings,
            llm_provider=active_llm_provider,
        )
        agent_workflow = ConcordAgentWorkflow.from_runner(runner)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if repository is not None:
            repository.initialize()
        yield

    app = FastAPI(
        title="Concord IQ",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = active_settings
    app.state.llm_provider = active_llm_provider
    app.state.reconciliation_runner = runner
    app.state.agent_workflow = agent_workflow
    app.state.foundry_hosted_provider = hosted_runtime
    app.include_router(router)
    return app


app = create_app()
