"""Tier 1 glass-box re-derivation acceptance tests."""

from collections.abc import Iterable

from concord.api.main import create_app
from concord.config import Settings
from concord.providers import LocalProvider
from concord.storage.models import (
    AuditEvent,
    EvidenceItem,
    MetricDefinition,
    ReconciliationRun,
    SemanticProposal,
)
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

PERSISTED_MODELS = (
    ReconciliationRun,
    SemanticProposal,
    EvidenceItem,
    AuditEvent,
    MetricDefinition,
)


def _row_counts(engine: Engine, models: Iterable[type[object]]) -> tuple[int, ...]:
    with Session(engine) as session:
        return tuple(
            session.scalar(select(func.count()).select_from(model)) or 0 for model in models
        )


def _what_if(
    client: TestClient,
    *,
    days: int,
    overrides: dict[str, object] | None = None,
):
    return client.post(
        "/reconcile/whatif",
        json={
            "term": "Active Customer",
            "binding_id": "active_customer_finance",
            "overrides": overrides or {"time_window_days": days},
        },
    )


def test_larger_window_rederives_population_and_metric_without_persistence(
    postgres_engine: Engine,
    p2_local_provider: LocalProvider,
) -> None:
    app = create_app(
        Settings(_env_file=None),
        provider=p2_local_provider,
        engine=postgres_engine,
    )
    before = _row_counts(postgres_engine, PERSISTED_MODELS)

    with TestClient(app) as client:
        response = _what_if(client, days=120)

    after = _row_counts(postgres_engine, PERSISTED_MODELS)
    assert response.status_code == 200
    payload = response.json()
    assert payload["term"] == "Active Customer"
    assert payload["binding_id"] == "active_customer_finance_v1"
    assert payload["baseline"] == {
        "entity_count": 1600,
        "metric_value": 210096000.0,
    }
    assert payload["whatif"]["entity_count"] > payload["baseline"]["entity_count"]
    assert payload["whatif"]["metric_value"] > payload["baseline"]["metric_value"]
    assert payload["delta"]["entity_count"] > 0
    assert payload["delta"]["metric_value"] > 0
    assert payload["sql"] == (
        "SELECT DISTINCT c.customer_id AS entity_id, "
        "c.annual_recurring_revenue AS metric_value "
        "FROM customers c JOIN revenue_events r ON r.customer_id = c.customer_id "
        "WHERE r.event_type = 'recognized_revenue' AND "
        "CAST(r.event_date AS DATE) BETWEEN DATE '2026-06-01' - "
        "INTERVAL 119 DAY AND DATE '2026-06-01' ORDER BY entity_id"
    )
    assert payload["ephemeral"] is True
    assert payload["note"] == (
        "Exploration only — not governed, not persisted, no proposal, no audit."
    )
    assert after == before

    governed = p2_local_provider.get_binding_semantics("active_customer")[0]
    assert governed.time_window_days == 90


def test_governed_window_has_zero_delta(
    postgres_engine: Engine,
    p2_local_provider: LocalProvider,
) -> None:
    app = create_app(
        Settings(_env_file=None),
        provider=p2_local_provider,
        engine=postgres_engine,
    )

    with TestClient(app) as client:
        response = _what_if(client, days=90)

    assert response.status_code == 200
    payload = response.json()
    assert payload["whatif"] == payload["baseline"]
    assert payload["delta"] == {"entity_count": 0, "metric_value": 0.0}
    assert "INTERVAL 89 DAY" in payload["sql"]


def test_non_whitelisted_override_is_rejected(
    postgres_engine: Engine,
    p2_local_provider: LocalProvider,
) -> None:
    app = create_app(
        Settings(_env_file=None),
        provider=p2_local_provider,
        engine=postgres_engine,
    )

    with TestClient(app) as client:
        response = _what_if(
            client,
            days=90,
            overrides={
                "time_window_days": 90,
                "filters": ["qualifying = false"],
            },
        )

    assert response.status_code == 422
