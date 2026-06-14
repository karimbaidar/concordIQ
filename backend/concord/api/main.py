"""FastAPI application factory with injectable deterministic dependencies."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Engine

from concord.api.routes import router
from concord.config import Settings
from concord.llm import LLMProvider, create_llm_provider
from concord.providers import (
    FoundryHostedProvider,
    GroundingProvider,
)
from concord.runtime import RuntimeManager
from concord.storage.db import create_database_engine


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
    active_engine = engine or create_database_engine(active_settings)
    runtime_manager = RuntimeManager(
        active_settings,
        engine=active_engine,
        provider=provider,
        foundry_hosted_provider=foundry_hosted_provider,
        llm_provider=active_llm_provider,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        runtime_manager.initialize()
        yield

    app = FastAPI(
        title="Concord IQ",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = active_settings
    app.state.llm_provider = active_llm_provider
    app.state.runtime_manager = runtime_manager
    # Compatibility for callers that inspect the initial app state directly.
    app.state.reconciliation_runner = runtime_manager.context.runner
    app.state.agent_workflow = runtime_manager.context.workflow
    app.state.foundry_hosted_provider = runtime_manager.context.hosted
    app.include_router(router)
    app.include_router(router, prefix="/api", include_in_schema=False)
    frontend_dist = Path("frontend/dist")
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
    return app


app = create_app()
