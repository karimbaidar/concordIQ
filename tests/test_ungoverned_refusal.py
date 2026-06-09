"""T1.3 acceptance: arbitrary-term entry refuses gracefully, never fabricates."""

from collections.abc import Iterable

from concord.api.main import create_app
from concord.config import Settings
from concord.providers import LocalProvider
from concord.storage.models import (
    AuditEvent,
    EvidenceItem,
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
)


def _row_counts(engine: Engine, models: Iterable[type[object]]) -> tuple[int, ...]:
    with Session(engine) as session:
        return tuple(
            session.scalar(select(func.count()).select_from(model)) or 0 for model in models
        )


def _analyze(client: TestClient, term: str):
    return client.post(
        "/analyze",
        json={"term": term, "question": f"Why do our {term} definitions disagree?"},
    )


def test_ungoverned_term_refuses_gracefully_without_fabrication(
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
        response = _analyze(client, "Gross Margin")

    after = _row_counts(postgres_engine, PERSISTED_MODELS)
    assert response.status_code == 200
    payload = response.json()
    assert payload["refused"] is True
    assert payload["term"] == "Gross Margin"
    assert "will not guess" in payload["reason"]
    # Points to the real governed terms — and only those.
    assert set(payload["known_terms"]) == {
        "Active Customer",
        "Net Revenue",
        "Churned Customer",
        "Qualified Lead",
    }
    # No fabricated definition is ever returned.
    assert "verdict" not in payload
    assert "binding_semantics" not in payload
    assert "reconciliation_proposal" not in payload
    # Refusal touches no governed state.
    assert after == before


def test_governed_term_still_reconciles_as_before(
    postgres_engine: Engine,
    p2_local_provider: LocalProvider,
) -> None:
    app = create_app(
        Settings(_env_file=None),
        provider=p2_local_provider,
        engine=postgres_engine,
    )

    with TestClient(app) as client:
        response = _analyze(client, "Active Customer")

    assert response.status_code == 200
    payload = response.json()
    assert "refused" not in payload
    assert payload["verdict"] == "conflict"
    assert payload["resolved_concept"]["canonical_name"] == "Active Customer"
