"""Headless deterministic demo for the three synthetic reconciliation cases."""

from collections.abc import Callable
from dataclasses import dataclass

from concord.config import ScenarioPack, Settings
from concord.llm import create_llm_provider
from concord.orchestration.casefile import ReconciliationCase, ReconciliationRequest
from concord.orchestration.runner import ReconciliationRunner
from concord.providers import create_provider
from concord.storage.db import create_database_engine
from concord.storage.repositories import ReconciliationRepository


@dataclass(frozen=True, slots=True)
class DemoScenario:
    """Public metadata and request text for one reviewed demo case."""

    scenario_id: str
    term: str
    question: str

    def request(self) -> ReconciliationRequest:
        return ReconciliationRequest(question=self.question, term=self.term)

    def as_dict(self) -> dict[str, str]:
        return {
            "scenario_id": self.scenario_id,
            "term": self.term,
            "question": self.question,
        }


BUSINESS_DEMO_SCENARIOS = (
    DemoScenario(
        scenario_id="active-customer",
        term="Active Customer",
        question="Why do our Active Customer dashboards disagree?",
    ),
    DemoScenario(
        scenario_id="net-revenue",
        term="Net Revenue",
        question="Are our Net Revenue definitions operationally equivalent?",
    ),
    DemoScenario(
        scenario_id="churned-customer",
        term="Churned Customer",
        question="Can we choose one enterprise Churned Customer definition?",
    ),
)

LEARNING_DEMO_SCENARIOS = (
    DemoScenario(
        scenario_id="certification-ready",
        term="Certification Ready",
        question=(
            "Do HR, Learning and Development, and managers agree on who is Certification Ready?"
        ),
    ),
    DemoScenario(
        scenario_id="required-training-complete",
        term="Required Training Complete",
        question="Are our Required Training Complete definitions operationally equivalent?",
    ),
    DemoScenario(
        scenario_id="exam-eligible",
        term="Exam Eligible",
        question="Can we choose one enterprise Exam Eligible definition?",
    ),
)

# Existing Fabric/replay proof tooling captures the reviewed business scenarios.
DEMO_SCENARIOS = BUSINESS_DEMO_SCENARIOS


def demo_scenarios_for_pack(scenario_pack: ScenarioPack) -> tuple[DemoScenario, ...]:
    """Return the stable scenarios exposed by one configured pack."""
    if scenario_pack is ScenarioPack.LEARNING:
        return LEARNING_DEMO_SCENARIOS
    return BUSINESS_DEMO_SCENARIOS


def demo_scenarios_for_provider(provider: object) -> tuple[DemoScenario, ...]:
    """Infer the active pack, defaulting legacy/replay providers to business."""
    scenario_pack = getattr(provider, "scenario_pack", ScenarioPack.BUSINESS)
    return demo_scenarios_for_pack(ScenarioPack(scenario_pack))


def get_demo_scenario(
    scenario_id: str,
    scenarios: tuple[DemoScenario, ...] = DEMO_SCENARIOS,
) -> DemoScenario:
    """Return a scenario by its stable public identifier."""
    scenario = next(
        (item for item in scenarios if item.scenario_id == scenario_id),
        None,
    )
    if scenario is None:
        raise KeyError(scenario_id)
    return scenario


def _decision_label(case: ReconciliationCase) -> str:
    if case.reconciliation_proposal:
        return "proposal drafted; human approval required"
    if case.refusal_reason:
        return "automatic reconciliation refused; human approval required"
    return "decoy ruled out; no reconciliation needed"


def run_demo(
    runner: ReconciliationRunner,
    *,
    emit: Callable[[str], None] = print,
) -> tuple[ReconciliationCase, ...]:
    """Run all demo scenarios and print one evidence-backed verdict per case."""
    cases: list[ReconciliationCase] = []
    for scenario in demo_scenarios_for_provider(runner.provider):
        case = runner.run(scenario.request())
        counts = "/".join(str(result.entity_count) for result in case.execution_results)
        emit(f"{scenario.term}: {case.verdict.upper()} | counts={counts} | {_decision_label(case)}")
        cases.append(case)
    return tuple(cases)


def main() -> None:
    """Build local dependencies and run the headless demo."""
    settings = Settings()
    engine = create_database_engine(settings)
    repository = ReconciliationRepository(engine)
    repository.initialize()
    runner = ReconciliationRunner(
        provider=create_provider(settings),
        repository=repository,
        settings=settings,
        llm_provider=create_llm_provider(settings),
    )
    try:
        run_demo(runner)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
