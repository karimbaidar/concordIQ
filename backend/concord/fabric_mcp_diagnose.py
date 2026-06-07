"""Diagnose what the Fabric IQ ontology MCP actually returns.

Run this before `make capture`. It makes one guarded MCP round trip using the
current `.env` and reports one of three states:

1. Full snapshot JSON: FOUND        -> capture in full-snapshot mode
2. Semantic proof: FOUND            -> capture in Fabric semantic-proof mode
3. No useful Fabric content found   -> do not capture

It prints the discovered tools, the matched concept (if any), and the response
shape, writes a sanitized copy of the raw response to
`artifacts/replay/raw/diagnostic.json` (gitignored), never prints tokens, and
never writes `sanitized/latest.json`.
"""

import json
from pathlib import Path
from typing import Any

from concord.capture import _secret_values, sanitize_value
from concord.config import CloudAccessDisabled, Settings
from concord.providers import FabricIQProvider
from concord.providers.base import ProviderNotConfigured
from concord.providers.cloud import CloudCallBudgetExceeded, CloudTransportError
from concord.providers.replay_schema import SnapshotNotFound, response_shape

DEFAULT_DIAGNOSTIC_TERM = "Active Customer"


def diagnose(
    settings: Settings,
    *,
    term: str = DEFAULT_DIAGNOSTIC_TERM,
    provider: FabricIQProvider | None = None,
) -> dict[str, Any]:
    """Probe the Fabric MCP once and return a non-secret diagnostic summary."""
    provider = provider or FabricIQProvider(settings)
    state = "none"
    matched_concept: str | None = None
    error: str | None = None
    try:
        provider.resolve_concept(term)
        if term in provider.semantic_proofs:
            state = "semantic_proof"
            matched_concept = provider.semantic_proofs[term]["matched_entity_type"]
        else:
            state = "full_snapshot"
    except SnapshotNotFound as exc:
        error = str(exc)
    except (ProviderNotConfigured, CloudTransportError, CloudCallBudgetExceeded) as exc:
        error = f"{type(exc).__name__}: {exc}"

    raw_responses = provider.raw_responses
    last_shape = response_shape(raw_responses[-1]) if raw_responses else "no response captured"

    sanitized_raw = sanitize_value(list(raw_responses), secret_values=_secret_values(settings))
    raw_dir = Path(settings.capture_raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    diagnostic_path = raw_dir / "diagnostic.json"
    diagnostic_path.write_text(json.dumps(sanitized_raw, indent=2), encoding="utf-8")

    return {
        "term": term,
        "tools": [str(tool.get("name", "?")) for tool in provider._tools],
        "response_shape": last_shape,
        "state": state,
        "matched_concept": matched_concept,
        "error": error,
        "diagnostic_path": str(diagnostic_path),
        "cloud_calls": provider.cloud_call_count,
    }


def main() -> None:
    settings = Settings()
    try:
        report = diagnose(settings)
    except CloudAccessDisabled as error:
        raise SystemExit(
            f"Diagnose refused: {error}\n"
            "Run with: PROVIDER=fabric_iq ALLOW_CLOUD=true MAX_CLOUD_CALLS=6 "
            "make fabric-mcp-diagnose"
        ) from error

    print(f"Term probed:       {report['term']}")
    print(f"MCP tools:         {', '.join(report['tools']) or 'none discovered'}")
    print(f"Matched concept:   {report['matched_concept'] or 'none'}")
    print(f"Response shape:    {report['response_shape']}")
    print(f"Cloud calls used:  {report['cloud_calls']}")
    print(f"Sanitized raw ->   {report['diagnostic_path']} (gitignored; no tokens)")
    state = report["state"]
    if state == "full_snapshot":
        print("Full snapshot JSON: FOUND")
        print("Capture can proceed in full-snapshot mode (`make capture`).")
    elif state == "semantic_proof":
        print("Semantic proof: FOUND")
        print("Full snapshot JSON: NOT FOUND")
        print("Capture can proceed using Fabric semantic proof mode (`make capture`).")
    else:
        print("No useful Fabric content found.")
        print(f"  Reason: {report['error']}")
        print("  Do NOT run `make capture`. See docs/iq-integration.md.")


if __name__ == "__main__":
    main()
