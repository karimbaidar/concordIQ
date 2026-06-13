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


def _run_required_training_complete(runner: ReconciliationRunner) -> ReconciliationCase:
    return runner.run(
        ReconciliationRequest(
            question="Are our Required Training Complete definitions operationally equivalent?",
            term="Required Training Complete",
        )
    )


def _run_exam_eligible(runner: ReconciliationRunner) -> ReconciliationCase:
    return runner.run(
        ReconciliationRequest(
            question="Can we choose one enterprise Exam Eligible definition?",
            term="Exam Eligible",
        )
    )


def test_required_training_complete_decoy_ruled_out(
    learning_runner: ReconciliationRunner,
) -> None:
    case = _run_required_training_complete(learning_runner)
    evaluations = case.execution_results

    assert case.state == ReconciliationState.COMPLETE
    assert case.verdict == "consistent"
    assert [result.entity_count for result in evaluations] == [80, 80]
    assert evaluations[0].entity_ids == evaluations[1].entity_ids
    assert evaluations[0].rows == evaluations[1].rows
    assert evaluations[0].metric_total == evaluations[1].metric_total
    assert case.reconciliation_proposal is None
    assert case.refusal_reason is None
    assert case.requires_human_approval is False
    assert case.impact_assessment
    assert case.impact_assessment.severity == "low"
    assert case.impact_assessment.customer_count_delta == 0
    assert case.verifier_report and case.verifier_report.passed
    assert len(case.agent_trace) == 10


def test_exam_eligible_refusal_routes_to_human(
    learning_runner: ReconciliationRunner,
) -> None:
    case = _run_exam_eligible(learning_runner)
    authority = case.authority_assessment

    assert case.state == ReconciliationState.COMPLETE
    assert case.verdict == "conflict"
    assert [result.entity_count for result in case.execution_results] == [80, 56]
    assert authority
    assert authority.status == "ambiguous"
    assert authority.owner is None
    assert {rule.status for rule in authority.rules} == {"shared", "ambiguous"}
    assert case.reconciliation_proposal is None
    assert case.requires_human_approval is True
    assert case.refusal_reason
    assert "human approval is required" in case.refusal_reason.lower()
    assert case.verifier_report and case.verifier_report.passed
    assert len(case.agent_trace) == 10


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


def test_court_endpoint_returns_a_debate_transcript(
    postgres_engine: Engine,
    learning_provider: LocalProvider,
) -> None:
    app = create_app(
        Settings(_env_file=None),
        provider=learning_provider,
        engine=postgres_engine,
    )
    with TestClient(app) as client:
        response = client.post("/court/run/certification-ready")

    assert response.status_code == 200
    transcript = response.json()
    assert transcript["term"] == "Certification Ready"
    assert transcript["verdict"] == "conflict"
    assert transcript["outcome"] == "proposal"
    assert transcript["mode"] == "deterministic_fallback"
    roles = {turn["role"] for turn in transcript["turns"]}
    assert roles == {"orchestrator", "steward", "investigator", "skeptic", "authority"}


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
