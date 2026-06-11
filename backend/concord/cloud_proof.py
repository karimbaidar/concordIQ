"""One-command live cloud proof for Concord IQ (``make cloud-proof``).

Runs every *configured* real-cloud proof and reports each outcome honestly:
``passed``, ``skipped``, ``license_gated``, ``permission_blocked``, or ``failed``.
Missing optional cloud configuration is reported as ``skipped`` and never fails
the command. No tokens, Authorization headers, or tenant URLs are printed or
written. Mandatory local proof is owned by ``make judge-proof``; this command is
the cloud-only companion.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from concord.config import Settings
from concord.judge_proof import JudgeProof

REPORT_PATH = Path("docs/proofs/cloud-proof-report.md")
JSON_PATH = Path("artifacts/proof/cloud-latest.json")


def run_cloud_proof(settings: Settings | None = None) -> dict[str, Any]:
    """Run the optional cloud proofs and return a sanitized status document."""
    proof = JudgeProof(settings=settings or Settings())
    proof.run_foundry()
    proof.run_fabric()
    proof.run_work_iq()
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "timestamp_utc": timestamp,
        "foundry_agent_service": proof.foundry,
        "fabric_iq": proof.fabric,
        "work_iq": proof.work_iq,
    }


def _write_reports(document: dict[str, Any]) -> None:
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    foundry = document["foundry_agent_service"]
    fabric = document["fabric_iq"]
    work_iq = document["work_iq"]
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        f"""# Concord IQ — live cloud proof report

- **Generated (UTC):** {document["timestamp_utc"]}

| Integration | Status | Mode |
|---|---|---|
| Foundry Agent Service | {foundry["status"].upper()} | {foundry["mode"]} |
| Fabric IQ (replay) | {fabric["status"].upper()} | {fabric["mode"]} |
| Fabric IQ (live diagnostics) | {fabric["live"].upper()} | optional MCP diagnostics |
| Work IQ | {work_iq["status"].upper()} | {work_iq["mode"]} |

Cloud checks are honest: missing credentials or tenant entitlements are reported
as `skipped`/`license_gated`, never as success. No tokens, Authorization headers,
or tenant URLs appear in this report.
""",
        encoding="utf-8",
    )


def main() -> None:
    document = run_cloud_proof()
    _write_reports(document)

    def up(value: str) -> str:
        return value.replace("_", "-").upper()

    print(
        "Concord IQ cloud proof\n\n"
        f"Foundry Agent Service: {up(document['foundry_agent_service']['status'])}\n"
        f"Fabric IQ (replay):    {up(document['fabric_iq']['status'])}\n"
        f"Fabric IQ (live):      {up(document['fabric_iq']['live'])}\n"
        f"Work IQ:               {up(document['work_iq']['status'])}\n\n"
        f"Report:\n{REPORT_PATH}\n{JSON_PATH}"
    )


if __name__ == "__main__":
    main()
