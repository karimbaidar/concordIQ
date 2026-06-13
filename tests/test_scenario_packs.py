"""Scenario-pack selection keeps learning first without disturbing business proof."""

from pathlib import Path

import pytest
from concord.config import ScenarioPack, Settings
from concord.demo import BUSINESS_DEMO_SCENARIOS, LEARNING_DEMO_SCENARIOS
from concord.providers import LocalProvider, create_provider
from pydantic import ValidationError


@pytest.fixture(autouse=True)
def _clear_scenario_pack_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CONCORD_SCENARIO_PACK", raising=False)


def test_missing_scenario_pack_defaults_to_learning() -> None:
    settings = Settings(_env_file=None)

    assert settings.scenario_pack is ScenarioPack.LEARNING
    assert [scenario.term for scenario in LEARNING_DEMO_SCENARIOS] == [
        "Certification Ready",
        "Required Training Complete",
        "Exam Eligible",
    ]


def test_business_pack_preserves_existing_registry_and_scenarios(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        scenario_pack="business",
        duckdb_path=tmp_path / "data.duckdb",
    )
    provider = create_provider(settings)

    assert isinstance(provider, LocalProvider)
    assert provider.scenario_pack is ScenarioPack.BUSINESS
    assert [concept.canonical_name for concept in provider.list_concepts()] == [
        "Active Customer",
        "Net Revenue",
        "Churned Customer",
        "Qualified Lead",
    ]
    assert [scenario.term for scenario in BUSINESS_DEMO_SCENARIOS] == [
        "Active Customer",
        "Net Revenue",
        "Churned Customer",
    ]


def test_learning_pack_loads_the_learning_registry(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        duckdb_path=tmp_path / "data.duckdb",
    )
    provider = create_provider(settings)

    assert isinstance(provider, LocalProvider)
    assert provider.scenario_pack is ScenarioPack.LEARNING
    assert [concept.canonical_name for concept in provider.list_concepts()] == [
        "Certification Ready",
        "Required Training Complete",
        "Exam Eligible",
    ]


def test_invalid_scenario_pack_lists_valid_values() -> None:
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, scenario_pack="finance-only")

    message = str(error.value)
    assert "Invalid CONCORD_SCENARIO_PACK='finance-only'" in message
    assert "learning, business" in message
