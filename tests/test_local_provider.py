"""P1 contract tests for deterministic local semantic grounding."""

from datetime import date
from pathlib import Path

import pytest
from concord.providers import EvaluationPeriod, GroundingProvider, LocalProvider
from concord.providers.base import ConceptNotFound
from concord.seed.seed_duckdb import seed_duckdb

DEMO_PERIOD = EvaluationPeriod(
    start_date=date(2026, 3, 4),
    end_date=date(2026, 6, 1),
)


@pytest.fixture
def local_provider(tmp_path: Path) -> LocalProvider:
    database_path = tmp_path / "concord-iq.duckdb"
    seed_duckdb(database_path=database_path, data_dir=tmp_path / "synthetic")
    return LocalProvider(duckdb_path=database_path)


def test_local_provider_satisfies_grounding_contract(local_provider: LocalProvider) -> None:
    assert isinstance(local_provider, GroundingProvider)
    assert local_provider.uses_cloud is False


def test_local_provider_resolves_active_customer(local_provider: LocalProvider) -> None:
    resolution = local_provider.resolve_concept("Active Enterprise Customers")

    assert resolution.concept_id == "active_customer"
    assert resolution.canonical_name == "Active Customer"
    assert resolution.definition_ids == (
        "active_customer_finance",
        "active_customer_sales",
        "active_customer_customer_success",
    )


def test_local_provider_rejects_unknown_concept(local_provider: LocalProvider) -> None:
    with pytest.raises(ConceptNotFound):
        local_provider.resolve_concept("Gross Logo Velocity")


def test_local_provider_returns_normalized_active_customer_bindings(
    local_provider: LocalProvider,
) -> None:
    bindings = local_provider.get_binding_semantics("active_customer")

    assert [binding.owner for binding in bindings] == [
        "Finance",
        "Sales",
        "Customer Success",
    ]
    assert {binding.time_window_days for binding in bindings} == {30, 90, 180}
    assert all(binding.entity_key == "customer_id" for binding in bindings)
    assert all(binding.sql_template for binding in bindings)


def test_local_provider_evaluates_active_customer_definitions(
    local_provider: LocalProvider,
) -> None:
    evaluations = [
        local_provider.evaluate_definition(binding.binding_id, DEMO_PERIOD)
        for binding in local_provider.get_binding_semantics("active_customer")
    ]

    assert [evaluation.entity_count for evaluation in evaluations] == [1600, 1500, 1334]
    assert len({evaluation.entity_ids for evaluation in evaluations}) == 3
    assert all(evaluation.metric_total > 0 for evaluation in evaluations)
    assert all("SELECT" in evaluation.executed_sql for evaluation in evaluations)


def test_seeded_net_revenue_bindings_are_behaviorally_equal(
    local_provider: LocalProvider,
) -> None:
    evaluations = [
        local_provider.evaluate_definition(binding.binding_id, DEMO_PERIOD)
        for binding in local_provider.get_binding_semantics("net_revenue")
    ]

    assert evaluations[0].entity_ids == evaluations[1].entity_ids
    assert evaluations[0].rows == evaluations[1].rows
    assert evaluations[0].metric_total == evaluations[1].metric_total


def test_seeded_churn_bindings_return_divergent_customer_sets(
    local_provider: LocalProvider,
) -> None:
    evaluations = [
        local_provider.evaluate_definition(binding.binding_id, DEMO_PERIOD)
        for binding in local_provider.get_binding_semantics("churned_customer")
    ]

    assert evaluations[0].entity_count == 333
    assert evaluations[1].entity_count == 666
    assert evaluations[0].entity_ids != evaluations[1].entity_ids


def test_local_provider_returns_subgraph_and_configured_authority(
    local_provider: LocalProvider,
) -> None:
    subgraph = local_provider.get_subgraph("active_customer")
    active_rules = local_provider.get_authority_rules("active_customer")
    churn_rules = local_provider.get_authority_rules("churned_customer")

    assert {node.node_id for node in subgraph.nodes} >= {
        "active_customer",
        "customer",
        "revenue_event",
    }
    assert all(rule.status == "clear" for rule in active_rules)
    assert {rule.status for rule in churn_rules} == {"shared", "ambiguous"}
    assert all(rule.owner is None for rule in churn_rules)
