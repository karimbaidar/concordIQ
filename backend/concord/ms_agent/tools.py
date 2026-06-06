"""Domain tools exposed to Microsoft Agent Framework."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from sqlalchemy import Engine

from concord.config import Settings
from concord.llm import create_llm_provider
from concord.orchestration.casefile import ReconciliationCase, ReconciliationRequest
from concord.orchestration.runner import ReconciliationRunner
from concord.providers import (
    GroundingProvider,
    create_preferred_cloud_provider,
    create_provider,
)
from concord.providers.base import EvaluationPeriod, ProviderMode, ProviderNotConfigured
from concord.storage.db import create_database_engine
from concord.storage.repositories import ReconciliationRepository

DEFAULT_PERIOD = "2026-03-04/2026-06-01"
ReconcileBusinessTerm = Callable[[str, str, str], ReconciliationCase]
ReconcileRequest = Callable[[ReconciliationRequest, str], ReconciliationCase]


def parse_period(period: str) -> EvaluationPeriod:
    """Parse an inclusive ISO date range accepted by the public tool."""
    separator = "/" if "/" in period else ".." if ".." in period else None
    if separator is None:
        raise ValueError("period must use YYYY-MM-DD/YYYY-MM-DD")
    start_text, end_text = (part.strip() for part in period.split(separator, maxsplit=1))
    return EvaluationPeriod(
        start_date=date.fromisoformat(start_text),
        end_date=date.fromisoformat(end_text),
    )


def format_period(period: EvaluationPeriod) -> str:
    """Render a typed period for the Agent Framework tool contract."""
    return f"{period.start_date.isoformat()}/{period.end_date.isoformat()}"


def select_provider(settings: Settings, requested: str) -> GroundingProvider:
    """Resolve an explicit provider or the Fabric-first cloud preference."""
    normalized = requested.strip().lower()
    if normalized in {"auto", "cloud"}:
        return create_preferred_cloud_provider(settings)
    try:
        mode = ProviderMode(normalized)
    except ValueError as error:
        raise ProviderNotConfigured(f"Unknown provider mode: {requested}") from error
    return create_provider(settings.model_copy(update={"provider": mode.value}))


@dataclass(slots=True)
class RunnerReconciliationTool:
    """Adapt one configured deterministic runner to the public tool signature."""

    runner: ReconciliationRunner

    def reconcile_business_term(
        self,
        term: str,
        period: str,
        provider: str,
    ) -> ReconciliationCase:
        """Run the existing domain engine without changing its decisions."""
        return self.reconcile_request(
            ReconciliationRequest(
                question=f"Why do our {term} definitions disagree?",
                term=term,
                period=parse_period(period),
            ),
            provider,
        )

    def reconcile_request(
        self,
        request: ReconciliationRequest,
        provider: str,
    ) -> ReconciliationCase:
        """Run an existing typed request while enforcing the configured provider."""
        requested = provider.strip().lower()
        configured = self.runner.provider.mode.value
        if requested not in {configured, self.runner.provider.name.lower()}:
            raise ProviderNotConfigured(
                f"This workflow is configured for {configured}, not {provider}."
            )
        return self.runner.run(request)


def _run_with_new_dependencies(
    *,
    term: str,
    period: str,
    provider: str,
    settings: Settings,
    engine: Engine,
) -> ReconciliationCase:
    selected_provider = select_provider(settings, provider)
    active_settings = settings.model_copy(update={"provider": selected_provider.mode.value})
    repository = ReconciliationRepository(engine)
    repository.initialize()
    runner = ReconciliationRunner(
        provider=selected_provider,
        repository=repository,
        settings=active_settings,
        llm_provider=create_llm_provider(active_settings),
    )
    return RunnerReconciliationTool(runner).reconcile_business_term(
        term,
        period,
        selected_provider.mode.value,
    )


def reconcile_business_term(
    term: str,
    period: str,
    provider: str,
) -> ReconciliationCase:
    """Callable Agent Framework tool backed by the deterministic runner."""
    settings = Settings()
    engine = create_database_engine(settings)
    try:
        return _run_with_new_dependencies(
            term=term,
            period=period,
            provider=provider,
            settings=settings,
            engine=engine,
        )
    finally:
        engine.dispose()
