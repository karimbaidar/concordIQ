"""Phase 3 acceptance tests for the NL chat surface (nl_query + /ask).

The grounded answer is deterministic and resolves a question to its governed
concept and competing definitions; the reconciliation engine still owns conflict
quantification. No LLM is required.
"""

from concord.api.main import create_app
from concord.config import Settings
from concord.providers import LocalProvider
from fastapi.testclient import TestClient
from sqlalchemy import Engine


def test_nl_query_local_grounded(p2_local_provider: LocalProvider) -> None:
    result = p2_local_provider.nl_query("Why do our active customer numbers disagree?")

    assert result.matched is True
    assert result.concept_id == "active_customer"
    assert result.canonical_name == "Active Customer"
    assert result.grounding_provider == "LocalProvider"
    # Grounded in the ontology: cites exactly the three competing definitions.
    assert set(result.citations) == {
        "active_customer_finance",
        "active_customer_sales",
        "active_customer_customer_success",
    }
    owners = {definition.owner for definition in result.definitions}
    assert owners == {"Finance", "Sales", "Customer Success"}
    assert "Active Customer has 3 competing definitions" in result.answer


def test_nl_query_resolves_aliases(p2_local_provider: LocalProvider) -> None:
    result = p2_local_provider.nl_query("are our booked revenue figures the same?")
    assert result.matched is True
    assert result.concept_id == "net_revenue"


def test_nl_query_returns_unmatched_without_inventing(
    p2_local_provider: LocalProvider,
) -> None:
    result = p2_local_provider.nl_query("what is the weather in Berlin today?")
    assert result.matched is False
    assert result.concept_id is None
    assert result.definitions == ()
    assert "No governed concept" in result.answer


def test_ask_endpoint_grounds_and_reconciles(
    postgres_engine: Engine,
    p2_local_provider: LocalProvider,
) -> None:
    app = create_app(Settings(), provider=p2_local_provider, engine=postgres_engine)
    with TestClient(app) as client:
        response = client.post(
            "/ask",
            json={"question": "Why do our active customer dashboards disagree?"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"]["matched"] is True
    assert payload["query"]["concept_id"] == "active_customer"
    assert payload["case"] is not None
    assert payload["case"]["verdict"] == "conflict"
    assert payload["case"]["reconciliation_proposal"] is not None


def test_ask_endpoint_unmatched_question_has_no_case(
    postgres_engine: Engine,
    p2_local_provider: LocalProvider,
) -> None:
    app = create_app(Settings(), provider=p2_local_provider, engine=postgres_engine)
    with TestClient(app) as client:
        response = client.post("/ask", json={"question": "tell me a joke"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"]["matched"] is False
    assert payload["case"] is None
