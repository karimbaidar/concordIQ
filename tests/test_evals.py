"""T2.3 — deterministic eval scorecard acceptance tests."""

from concord.evals import eval_runner, format_scorecard, run_scorecard
from concord.providers import LocalProvider


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
