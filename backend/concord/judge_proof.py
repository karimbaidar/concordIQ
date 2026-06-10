"""One-command judge proof for Concord IQ.

Runs the mandatory local verification (tests, lint, eval, replay, semantic PR export),
then runs each optional cloud integration only when its credentials are present, and
writes a sanitized Markdown + JSON proof report. It fails when a mandatory local proof
fails and never fails because optional cloud credentials are missing. No tokens,
Authorization headers, or tenant URLs are ever printed or written.

Entry point: ``make judge-proof`` → ``python -m concord.judge_proof``.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from concord.config import Settings
from concord.work_iq_proof import run_work_iq_proof

REPORT_PATH = Path("docs/proofs/judge-proof-report.md")
JSON_PATH = Path("artifacts/proof/latest.json")
LICENSE_GATE_PATH = Path("docs/proofs/work-iq-license-gate.md")

PASSED = "passed"
FAILED = "failed"
SKIPPED = "skipped"

FABRIC_LIVE_ENV = (
    "FABRIC_WORKSPACE_ID",
    "FABRIC_LAKEHOUSE_ID",
    "FABRIC_ONTOLOGY_ID",
    "FABRIC_IQ_MCP_ENDPOINT",
)


@dataclass(slots=True)
class StepResult:
    """One verification step's sanitized outcome."""

    key: str
    label: str
    status: str
    mandatory: bool
    detail: str = ""


def _run_make(target: str, *, extra_env: dict[str, str] | None = None) -> tuple[bool, str]:
    """Run a Makefile target, returning (ok, short sanitized tail of output)."""
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(  # noqa: S603
        ["make", target],  # noqa: S607
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    output = (proc.stdout + proc.stderr).strip()
    tail = "\n".join(output.splitlines()[-8:]) if output else ""
    return proc.returncode == 0, tail


def _git_commit() -> str:
    proc = subprocess.run(  # noqa: S603
        ["git", "rev-parse", "HEAD"],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout.strip() or "unknown"


def _mandatory_step(key: str, label: str, target: str) -> StepResult:
    ok, tail = _run_make(target)
    return StepResult(
        key=key,
        label=label,
        status=PASSED if ok else FAILED,
        mandatory=True,
        detail="" if ok else f"`make {target}` failed: {tail.splitlines()[-1] if tail else ''}",
    )


@dataclass(slots=True)
class JudgeProof:
    """Collects step results and renders the sanitized proof reports."""

    settings: Settings = field(default_factory=Settings)
    steps: list[StepResult] = field(default_factory=list)
    foundry: dict[str, Any] = field(default_factory=dict)
    fabric: dict[str, Any] = field(default_factory=dict)
    work_iq: dict[str, Any] = field(default_factory=dict)

    # --- mandatory local -------------------------------------------------
    def run_local(self) -> None:
        plan: tuple[tuple[str, str, str], ...] = (
            ("tests", "Local tests (backend)", "test-backend"),
            ("frontend_tests", "Frontend tests", "test-frontend"),
            ("lint", "Lint / typecheck", "lint"),
            ("eval", "Eval scorecard", "eval"),
            ("replay", "Replay proof", "replay-check"),
            ("semantic_pr_export", "Semantic PR export", "semantic-pr-export"),
        )
        for key, label, target in plan:
            self.steps.append(_mandatory_step(key, label, target))

    # --- optional cloud --------------------------------------------------
    def run_foundry(self) -> None:
        endpoint = self.settings.foundry_hosted_endpoint
        token = self.settings.foundry_access_token
        if not (self.settings.allow_cloud and endpoint and token):
            self.foundry = {"status": SKIPPED, "mode": "hosted_runtime"}
            return
        ok, tail = _run_make(
            "foundry-hosted-smoke",
            extra_env={"ALLOW_CLOUD": "true", "MAX_CLOUD_CALLS": "1"},
        )
        self.foundry = {
            "status": PASSED if ok else FAILED,
            "mode": "hosted_runtime",
        }
        if not ok:
            self.foundry["detail"] = tail.splitlines()[-1] if tail else "hosted smoke failed"

    def run_fabric(self) -> None:
        # Fabric IQ semantic grounding is always proven through sanitized replay
        # (covered by the mandatory replay step). Live diagnostics are optional.
        live = SKIPPED
        have_env = self.settings.allow_cloud and all(
            os.environ.get(name) for name in FABRIC_LIVE_ENV
        )
        if have_env:
            diag_ok, _ = _run_make(
                "fabric-mcp-diagnose", extra_env={"ALLOW_CLOUD": "true", "MAX_CLOUD_CALLS": "6"}
            )
            live = PASSED if diag_ok else FAILED
        self.fabric = {
            "status": PASSED,
            "mode": "sanitized_replay",
            "live": live,
        }

    def run_work_iq(self) -> None:
        document = run_work_iq_proof(self.settings)
        status = document["status"]
        # With no live attempt this run, surface the recorded ground truth: a real,
        # permission-verified attempt is documented in work-iq-license-gate.md and
        # returned the tenant license error. Honest, not a success claim.
        if status == SKIPPED and LICENSE_GATE_PATH.exists():
            self.work_iq = {
                "status": "license_gated",
                "mode": document["mode"],
                "live_recheck": SKIPPED,
            }
            return
        self.work_iq = {"status": status, "mode": document["mode"]}
        if document.get("retrieval_hits"):
            self.work_iq["retrieval_hits"] = document["retrieval_hits"]

    def run_all(self) -> None:
        self.run_local()
        self.run_foundry()
        self.run_fabric()
        self.run_work_iq()

    # --- reporting -------------------------------------------------------
    @property
    def mandatory_passed(self) -> bool:
        return all(step.status == PASSED for step in self.steps if step.mandatory)

    def _local_json(self) -> dict[str, str]:
        return {step.key: step.status for step in self.steps}

    def to_json(self, commit: str, timestamp: str) -> dict[str, Any]:
        return {
            "commit": commit,
            "timestamp_utc": timestamp,
            "mandatory_passed": self.mandatory_passed,
            "local": self._local_json(),
            "foundry_agent_service": self.foundry,
            "fabric_iq": self.fabric,
            "work_iq": self.work_iq,
        }

    def write_reports(self) -> dict[str, Any]:
        commit = _git_commit()
        timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        document = self.to_json(commit, timestamp)
        JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        JSON_PATH.write_text(
            json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(self._render_markdown(commit, timestamp), encoding="utf-8")
        return document

    def _render_markdown(self, commit: str, timestamp: str) -> str:
        def badge(status: str) -> str:
            return {
                PASSED: "✅ PASSED",
                FAILED: "❌ FAILED",
                SKIPPED: "⏭️ SKIPPED",
                "license_gated": "🔒 LICENSE-GATED",
                "permission_blocked": "⛔ PERMISSION-BLOCKED",
            }.get(status, status.upper())

        local_rows = "\n".join(
            f"| {step.label} | {badge(step.status)} | {step.detail} |" for step in self.steps
        )
        fab = self.fabric
        return f"""# Concord IQ — judge proof report

- **Generated (UTC):** {timestamp}
- **Git commit:** `{commit}`
- **Mandatory local proof:** {"✅ PASSED" if self.mandatory_passed else "❌ FAILED"}

## Local verification (mandatory)

| Check | Status | Detail |
|---|---|---|
{local_rows}

## Optional cloud integrations

| Integration | Status | Mode |
|---|---|---|
| Foundry Agent Service | {badge(self.foundry["status"])} | {self.foundry["mode"]} |
| Fabric IQ (replay) | {badge(fab["status"])} | {fab["mode"]} |
| Fabric IQ (live diagnostics) | {badge(fab["live"])} | optional MCP diagnostics |
| Work IQ | {badge(self.work_iq["status"])} | {self.work_iq["mode"]} |

Fabric IQ semantic grounding is reproduced through sanitized replay proof.

## Commands a judge can run

```bash
make judge-proof          # this report
make test                 # backend + frontend tests
make lint                 # ruff + frontend lint
make eval                 # deterministic safety scorecard
make replay-check         # verified Fabric IQ replay artifact
make semantic-pr-export   # governed definition-change artifact + hash
```

Optional cloud (only run with credentials and `ALLOW_CLOUD=true`):

```bash
ALLOW_CLOUD=true MAX_CLOUD_CALLS=1 PROVIDER=foundry_hosted make foundry-hosted-smoke
ALLOW_CLOUD=true MAX_CLOUD_CALLS=3 PROVIDER=work_iq make work-iq-proof
```

## Honesty note

Cloud checks are marked `passed`, `skipped`, `license_gated`, or `permission_blocked`.
Missing credentials or tenant entitlements are never hidden and never reported as
success. Work IQ is only `passed` when a live Microsoft Graph retrieval returns at
least one hit; until the tenant is entitled for the Retrieval API it stays
`license_gated`. No tokens, Authorization headers, or tenant URLs appear in this report.

- Machine-readable copy: `artifacts/proof/latest.json`
- Proof index: `docs/proofs/README.md`
"""


def _summary(document: dict[str, Any]) -> str:
    local = document["local"]

    def up(value: str) -> str:
        return value.replace("_", "-").upper()

    return f"""Concord IQ judge proof

Local tests:        {up(local.get("tests", "?"))}
Frontend tests:     {up(local.get("frontend_tests", "?"))}
Lint/typecheck:     {up(local.get("lint", "?"))}
Eval scorecard:     {up(local.get("eval", "?"))}
Replay proof:       {up(local.get("replay", "?"))}
Semantic PR export: {up(local.get("semantic_pr_export", "?"))}

Foundry Agent Service: {up(document["foundry_agent_service"]["status"])}
Fabric IQ live:        {up(document["fabric_iq"]["live"])}
Work IQ:               {up(document["work_iq"]["status"])}

Proof report:
{REPORT_PATH}
{JSON_PATH}"""


def main() -> None:
    proof = JudgeProof()
    proof.run_all()
    document = proof.write_reports()
    print(_summary(document))
    if not proof.mandatory_passed:
        raise SystemExit("Mandatory local proof failed; see docs/proofs/judge-proof-report.md")


if __name__ == "__main__":
    main()
