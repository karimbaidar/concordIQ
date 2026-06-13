"""T2.3 — deterministic eval scorecard acceptance tests."""

from concord.config import ScenarioPack, Settings
from concord.evals import eval_runner, format_scorecard, run_scorecard
from concord.providers import LocalProvider
from concord.providers.base import ProviderMode


def test_scorecard_is_deterministic_and_all_checks_pass(
    p2_local_provider: LocalProvider,
) -> None:
    with eval_runner(provider=p2_local_provider) as runner:
        card = run_scorecard(runner)

    assert card.total >= 10
    assert card.passed == card.total
    assert card.precision == 1.0

    categories = card.categories()
    for required in (
        "conflict",
        "decoy",
        "refusal",
        "no_fabrication",
        "no_llm_verdict",
        "provider_label",
        "red_team",
    ):
        assert required in categories

    # Every red-team prompt fails closed.
    assert all(result.passed for result in card.results if result.category == "red_team")

    text = format_scorecard(card)
    assert "Precision:" in text
    assert "fake_verified_capture_rejected" in text


def test_eval_runner_ignores_cloud_presenter_configuration() -> None:
    presenter_settings = Settings(
        _env_file=None,
        scenario_pack=ScenarioPack.LEARNING,
        provider="fabric_iq",
        allow_cloud=True,
        max_cloud_calls=6,
        llm_provider="azure_openai",
    )

    with eval_runner(settings=presenter_settings) as runner:
        assert runner.settings.scenario_pack is ScenarioPack.BUSINESS
        assert runner.settings.provider == ProviderMode.LOCAL
        assert runner.settings.allow_cloud is False
        assert runner.settings.max_cloud_calls == 0
        assert runner.settings.llm_provider == "disabled"
        assert runner.provider.mode is ProviderMode.LOCAL
