"""Diagnose what the Fabric IQ ontology MCP actually returns.

Run this when `make capture` fails with "did not contain a valid Concord IQ
scenario snapshot". It makes one guarded MCP round trip using the current `.env`,
prints the discovered tools and the response shape, says whether retrievable
snapshot JSON was found, and writes a sanitized copy of the raw response to
`artifacts/replay/raw/diagnostic.json` (gitignored). It never prints tokens and
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
from concord.providers.replay_schema import SnapshotNotFound, find_snapshot

DEFAULT_DIAGNOSTIC_TERM = "Active Customer"


def _shape(value: Any, depth: int = 0) -> str:
    """Summarize the structure of a JSON value without revealing its contents."""
    if isinstance(value, dict):
        if depth >= 3:
            return "{...}"
        return "{" + ", ".join(f"{k}: {_shape(v, depth + 1)}" for k, v in value.items()) + "}"
    if isinstance(value, list):
        if not value:
            return "[]"
        return f"[{_shape(value[0], depth + 1)} x{len(value)}]"
    if isinstance(value, str):
        return f"str(len={len(value)})"
    return type(value).__name__


def diagnose(
    settings: Settings,
    *,
    term: str = DEFAULT_DIAGNOSTIC_TERM,
    provider: FabricIQProvider | None = None,
) -> dict[str, Any]:
    """Probe the Fabric MCP once and return a non-secret diagnostic summary."""
    provider = provider or FabricIQProvider(settings)
    snapshot_found = False
    snapshot_error: str | None = None
    try:
        provider.resolve_concept(term)
        snapshot_found = True
    except SnapshotNotFound as error:
        snapshot_error = str(error)
    except (ProviderNotConfigured, CloudTransportError, CloudCallBudgetExceeded) as error:
        snapshot_error = f"{type(error).__name__}: {error}"

    tools = [str(tool.get("name", "?")) for tool in provider._tools]
    raw_responses = provider.raw_responses
    last_shape = _shape(raw_responses[-1]) if raw_responses else "no response captured"

    # Independently re-test snapshot extraction against the last tool-call payload.
    if not snapshot_found and raw_responses:
        try:
            find_snapshot(raw_responses[-1])
            snapshot_found = True
            snapshot_error = None
        except SnapshotNotFound as error:
            snapshot_error = str(error)

    sanitized_raw = sanitize_value(list(raw_responses), secret_values=_secret_values(settings))
    raw_dir = Path(settings.capture_raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    diagnostic_path = raw_dir / "diagnostic.json"
    diagnostic_path.write_text(json.dumps(sanitized_raw, indent=2), encoding="utf-8")

    return {
        "term": term,
        "tools": tools,
        "response_shape": last_shape,
        "snapshot_found": snapshot_found,
        "snapshot_error": snapshot_error,
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
    print(f"Response shape:    {report['response_shape']}")
    print(f"Cloud calls used:  {report['cloud_calls']}")
    print(f"Sanitized raw ->   {report['diagnostic_path']} (gitignored; no tokens)")
    if report["snapshot_found"]:
        print("Valid Concord IQ snapshot JSON: FOUND. You can run `make capture`.")
    else:
        print("Valid Concord IQ snapshot JSON: NOT FOUND.")
        print(f"  Reason: {report['snapshot_error']}")
        print(
            "  Fix: ensure the `concord_iq_scenarios` content is uploaded and retrievable "
            "(see docs/iq-integration.md). Do NOT run `make capture` until this reports FOUND."
        )


if __name__ == "__main__":
    main()
