"""Challenge A MVS acceptance tests for the Certification Ready scenario."""

import pytest
from concord.api.main import create_app
from concord.config import ScenarioPack, Settings
from concord.orchestration.casefile import ReconciliationCase, ReconciliationRequest
from concord.orchestration.runner import ReconciliationRunner
from concord.orchestration.state_machine import ReconciliationState
from concord.providers import LocalProvider
from concord.seed.seed_duckdb import seed_duckdb
from concord.semantic_pr_export import export_semantic_pr
from concord.storage.repositories import (
    ReconciliationRepository,
    UnauthorizedApprover,
)
from fastapi.testclient import TestClient
from sqlalchemy import Engine


@pytest.fixture(scope="session")
def learning_provider(tmp_path_factory: pytest.TempPathFactory) -> LocalProvider:
    data_dir = tmp_path_factory.mktemp("learning-synthetic")
    database_path = data_dir / "concord-iq.duckdb"
    seed_duckdb(database_path=database_path, data_dir=data_dir / "csv")
    return LocalProvider.for_scenario_pack(
        ScenarioPack.LEARNING,
        duckdb_path=database_path,
    )


@pytest.fixture
def learning_runner(
    postgres_engine: Engine,
    learning_provider: LocalProvider,
) -> ReconciliationRunner:
    return ReconciliationRunner(
        provider=learning_provider,
        repository=ReconciliationRepository(postgres_engine),
        settings=Settings(_env_file=None, scenario_pack=ScenarioPack.LEARNING),
    )


def _run_certification_ready(runner: ReconciliationRunner) -> ReconciliationCase:
    return runner.run(
        ReconciliationRequest(
            question=(
                "Do HR, Learning and Development, and managers agree on who is Certification Ready?"
            ),
            term="Certification Ready",
        )
    )


def test_learning_registry_executes_three_divergent_definitions(
    learning_provider: LocalProvider,
) -> None:
    concept = learning_provider.resolve_concept("Certification Ready")
    bindings = learning_provider.get_binding_semantics(concept.concept_id)
    period = ReconciliationRequest(question="Certification Ready proof").period
    evaluations = [
        learning_provider.evaluate_definition(binding.binding_id, period) for binding in bindings
    ]

    assert concept.concept_id == "certification_ready"
    assert [binding.owner for binding in bindings] == [
        "HR",
        "Learning & Development",
        "Managers",
    ]
    assert [evaluation.entity_count for evaluation in evaluations] == [80, 56, 56]
    assert len({evaluation.entity_ids for evaluation in evaluations}) == 3
    assert all("SELECT" in evaluation.executed_sql for evaluation in evaluations)


def test_certification_ready_runs_through_the_real_workflow(
    learning_runner: ReconciliationRunner,
) -> None:
    case = _run_certification_ready(learning_runner)
    impact = case.impact_assessment
    proposal = case.reconciliation_proposal

    assert case.state == ReconciliationState.COMPLETE
    assert case.verdict == "conflict"
    assert case.verification_status == "passed"
    assert case.verifier_report and case.verifier_report.passed
    assert len(case.agent_trace) == 10
    assert [result.entity_count for result in case.execution_results] == [80, 56, 56]
    assert impact
    assert impact.entity_label == "learners"
    assert impact.false_positive_count == 24
    assert impact.false_positive_entity_ids == tuple(f"L{index:03d}" for index in range(57, 81))
    assert impact.arr_delta == 10_800
    assert impact.value_label == "exam spend at risk"
    assert impact.affected_entity_ids
    assert case.authority_assessment
    assert case.authority_assessment.owner == "Learning Governance Council"
    assert proposal
    assert proposal.canonical_source_definition_id == "certification_ready_learning"
    assert proposal.requires_human_approval
    assert set(proposal.evidence_refs) == {item.evidence_id for item in case.evidence}
    assert all(item.entity_ids for item in case.evidence)
    assert all(item.sql_text for item in case.evidence)


def test_certification_ready_semantic_pr_is_owner_gated(
    learning_runner: ReconciliationRunner,
    isolated_canonical_registry: None,
) -> None:
    case = _run_certification_ready(learning_runner)

    with pytest.raises(UnauthorizedApprover):
        learning_runner.repository.decide_proposal(
            case.run_id,
            decision="approved",
            approver="HR",
        )

    decision = learning_runner.repository.decide_proposal(
        case.run_id,
        decision="approved",
        approver="Learning Governance Council",
    )
    assert decision.status == "approved"
    assert decision.term == "Certification Ready"
    assert decision.canonical_source_definition_id == "certification_ready_learning"
    assert decision.registry_scope == "concord_iq"

    governed = _run_certification_ready(learning_runner)
    assert governed.governed_canonical
    assert governed.verdict == "consistent"
    assert [result.entity_count for result in governed.execution_results] == [56]
    assert governed.reconciliation_proposal is None


def test_learning_pack_is_the_api_default(
    postgres_engine: Engine,
    learning_provider: LocalProvider,
) -> None:
    app = create_app(
        Settings(_env_file=None),
        provider=learning_provider,
        engine=postgres_engine,
    )
    with TestClient(app) as client:
        health = client.get("/health")
        scenarios = client.get("/demo/scenarios")
        result = client.post("/demo/run/certification-ready")

    assert health.status_code == 200
    assert health.json()["scenario_pack"] == "learning"
    assert scenarios.status_code == 200
    assert scenarios.json()[0]["term"] == "Certification Ready"
    assert result.status_code == 200
    assert result.json()["verdict"] == "conflict"


def test_certification_ready_semantic_pr_can_be_exported(
    learning_runner: ReconciliationRunner,
    isolated_canonical_registry: None,
    tmp_path,
) -> None:
    document = export_semantic_pr(
        settings=learning_runner.settings,
        term="Certification Ready",
        question="Prove the Certification Ready disagreement.",
        artifact_path=tmp_path / "certification-ready.json",
        report_path=tmp_path / "certification-ready.md",
    )

    assert document["term"] == "Certification Ready"
    assert document["verdict"] == "conflict"
    assert document["impact"]["false_positive_count"] == 24
    assert document["impact"]["false_positive_entity_ids"][0] == "L057"
    assert document["impact"]["value_label"] == "exam spend at risk"
    assert document["governance"]["owner"] == "Learning Governance Council"
