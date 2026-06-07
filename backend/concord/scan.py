"""Headless autonomous portfolio scan — the proof without the UI.

Prints the Concord Score and a ranked board of every concept it swept, so a
reviewer can see the "agent that watches" surface from the terminal even if the
frontend is not running. Deterministic, local, and cloud-free.
"""

from collections.abc import Callable

from concord.config import Settings
from concord.orchestration.portfolio import PortfolioScan, scan_portfolio
from concord.providers import create_provider


def render_scan(scan: PortfolioScan, *, emit: Callable[[str], None] = print) -> None:
    """Print the score header and one ranked line per concept."""
    score = scan.score
    emit(
        f"Concord Score: {score.overall}/100 (grade {score.grade}) | "
        f"{score.conflicts} conflicts, {score.consistent} consistent, "
        f"{score.refusals} refusal(s) across {score.concepts_scanned} concepts | "
        f"provider={scan.provider}"
    )
    for item in scan.concepts:
        position = f"#{item.rank}" if item.rank else "ok"
        emit(
            f"  [{position:>3}] {item.term:<18} {item.verdict.upper():<10} "
            f"counts={'/'.join(map(str, item.counts))} "
            f"Δcustomers={item.customer_count_delta} "
            f"Δvalue={item.arr_delta:,.0f} "
            f"action={item.recommended_action} "
            f"authority={item.authority_status}"
        )
    emit("Team semantic health:")
    for unit in score.by_business_unit:
        emit(f"  {unit.business_unit:<20} {unit.score}/100 ({unit.open_conflicts} open)")


def main() -> None:
    settings = Settings()
    provider = create_provider(settings)
    render_scan(scan_portfolio(provider))


if __name__ == "__main__":
    main()
