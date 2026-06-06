"""FastAPI application factory with injectable deterministic dependencies."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import Engine

from concord.api.routes import router
from concord.config import Settings
from concord.llm import LLMProvider, create_llm_provider
from concord.orchestration.runner import ReconciliationRunner
from concord.providers import GroundingProvider, create_provider
from concord.storage.db import create_database_engine
from concord.storage.repositories import ReconciliationRepository


def create_app(
    settings: Settings | None = None,
    *,
    provider: GroundingProvider | None = None,
    llm_provider: LLMProvider | None = None,
    engine: Engine | None = None,
) -> FastAPI:
    """Create an app using local, cloud-disabled defaults unless injected."""
    active_settings = settings or Settings()
    active_provider = provider or create_provider(active_settings)
    active_llm_provider = llm_provider or create_llm_provider(active_settings)
    active_engine = engine or create_database_engine(active_settings)
    repository = ReconciliationRepository(active_engine)
    runner = ReconciliationRunner(
        provider=active_provider,
        repository=repository,
        settings=active_settings,
        llm_provider=active_llm_provider,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        repository.initialize()
        yield

    app = FastAPI(
        title="Concord IQ",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.reconciliation_runner = runner
    app.include_router(router)
    return app


app = create_app()
