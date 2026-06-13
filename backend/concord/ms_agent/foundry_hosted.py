"""Foundry Agent Service hosted-runtime tooling.

Foundry Agent Service is the intended cloud runtime for Concord IQ. These
commands prepare and verify a *deployed* hosted agent (distinct from the
in-process protocol smoke in `foundry_hosted_entrypoint.py`):

* `hosted_dry_run` — no cloud; checks the entrypoint and committed replay artifact
  and prints the required environment.
* `hosted_package` — no cloud; writes a deployment report describing what to ship.
* `hosted_smoke` — one real call to an already-deployed Foundry endpoint, asserting
  the response proves ReplayProvider + strict workflow + the Certification Ready
  conflict. ReplayProvider is used so the hosted agent needs no Fabric credentials.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict

from concord.config import CloudAccessDisabled, Settings
from concord.providers.foundry_hosted import foundry_responses_url

HOSTED_ENTRYPOINT_MODULE = "concord.ms_agent.foundry_hosted_entrypoint"
HOSTED_START_COMMAND = "python -m concord.ms_agent.foundry_hosted_entrypoint"
HOSTED_QUESTION = os.environ.get(
    "FOUNDRY_SMOKE_QUESTION",
    "Do HR, Learning and Development, and managers agree on who is Certification Ready?",
)
DEFAULT_OUTPUT_DIR = Path("artifacts/foundry")

EXPECTED_PROVIDER_MODE = "replay"
EXPECTED_WORKFLOW_MODE = "strict"
EXPECTED_TERM = os.environ.get("FOUNDRY_SMOKE_TERM", "Certification Ready")
EXPECTED_VERDICT = "conflict"
EXPECTED_VERIFICATION = "passed"
EXPECTED_STEPS = 10

PACKAGE_INCLUDES = (
    f"{HOSTED_START_COMMAND}  (hosted entrypoint)",
    "backend/concord/  (application package)",
    "pyproject.toml + uv.lock  (dependencies, incl. the foundry-hosting extra)",
    "artifacts/replay/sanitized/latest.json  (verified Fabric IQ replay artifact)",
    "ontology/  and  data/synthetic/  (deterministic grounding + analytics)",
)
PACKAGE_EXCLUDES = (
    ".env and any *.env files",
    "tokens / access keys / Authorization headers",
    ".venv/ and node_modules/",
    "artifacts/replay/raw/ (raw cloud responses, diagnostic.json)",
    "artifacts/foundry/ (build output)",
    "planning files and tenant screenshots",
)


class HostedSmokeError(RuntimeError):
    """Raised when a hosted smoke is misconfigured or the response is not valid."""


class HostedSmokeProof(BaseModel):
    """Non-secret proof extracted from a deployed Foundry agent's response."""

    model_config = ConfigDict(frozen=True)

    provider_mode: str
    workflow_mode: str
    term: str
    verdict: str
    verification_status: str
    specialist_steps: int


def required_hosted_env() -> dict[str, str]:
    """The environment a hosted deployment and its smoke caller require."""
    return {
        # Inside the hosted app (no cloud grounding needed — replay is self-contained):
        "PROVIDER": "replay",
        "CONCORD_WORKFLOW_MODE": "strict",
        "DATABASE_URL": "sqlite+pysqlite:////tmp/concord_iq_foundry_smoke.db",
        "REPLAY_ARTIFACT_PATH": "artifacts/replay/sanitized/latest.json",
        "ALLOW_CLOUD": "false",
        "MAX_CLOUD_CALLS": "0",
        # For the local smoke caller that reaches the deployed endpoint:
        "FOUNDRY_HOSTED_ENDPOINT": "<https endpoint of the deployed agent>",
        "FOUNDRY_HOSTED_AGENT_ID": "<optional deployed agent id>",
        "FOUNDRY_ACCESS_TOKEN": "<short-lived bearer token, or use az login>",
        "FOUNDRY_SMOKE_ALLOW_CLOUD": "true (caller only)",
        "FOUNDRY_SMOKE_MAX_CLOUD_CALLS": "1 (caller only)",
    }


def _find_output_text(payload: Any) -> str | None:
    """Locate the agent's text output inside a Responses-API payload."""
    if isinstance(payload, dict):
        if payload.get("type") == "output_text" and isinstance(payload.get("text"), str):
            return payload["text"]
        for value in payload.values():
            found = _find_output_text(value)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _find_output_text(item)
            if found is not None:
                return found
    return None


def extract_hosted_proof(payload: dict[str, Any]) -> HostedSmokeProof:
    """Extract the self-describing proof from a hosted Responses payload."""
    text = _find_output_text(payload)
    if text is None:
        raise HostedSmokeError("Hosted response contained no Concord IQ output text.")
    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise HostedSmokeError("Hosted response output was not valid JSON.") from error
    proof = document.get("concord_iq_proof")
    if isinstance(proof, dict):
        try:
            return HostedSmokeProof.model_validate(proof)
        except ValueError as error:
            raise HostedSmokeError(f"Hosted proof was malformed: {error}") from error
    raise HostedSmokeError(
        "Hosted response is missing the concord_iq_proof envelope; the deployed agent "
        "must run the current Concord IQ hosted entrypoint."
    )


def validate_hosted_proof(proof: HostedSmokeProof) -> None:
    """Reject any response that does not prove replay + strict + the conflict."""
    failures: list[str] = []
    if proof.provider_mode != EXPECTED_PROVIDER_MODE:
        failures.append(f"provider_mode is {proof.provider_mode!r}, expected 'replay'")
    if proof.workflow_mode != EXPECTED_WORKFLOW_MODE:
        failures.append(f"workflow_mode is {proof.workflow_mode!r}, expected 'strict'")
    if proof.term != EXPECTED_TERM:
        failures.append(f"term is {proof.term!r}, expected {EXPECTED_TERM!r}")
    if proof.verdict != EXPECTED_VERDICT:
        failures.append(f"verdict is {proof.verdict!r}, expected 'conflict'")
    if proof.verification_status != EXPECTED_VERIFICATION:
        failures.append(f"verification_status is {proof.verification_status!r}, expected 'passed'")
    if proof.specialist_steps != EXPECTED_STEPS:
        failures.append(f"specialist_steps is {proof.specialist_steps}, expected 10")
    if failures:
        raise HostedSmokeError("Hosted smoke response is invalid: " + "; ".join(failures))


def hosted_dry_run(settings: Settings | None = None) -> dict[str, object]:
    """Validate the hosted runtime locally without any cloud call."""
    active = settings or Settings()
    entrypoint_available = importlib.util.find_spec(HOSTED_ENTRYPOINT_MODULE) is not None
    artifact = Path(active.replay_artifact_path)
    if not entrypoint_available:
        raise HostedSmokeError(f"Hosted entrypoint module {HOSTED_ENTRYPOINT_MODULE} is missing.")
    if not artifact.exists():
        raise HostedSmokeError(
            f"Verified replay artifact is missing: {artifact}. Run the Fabric capture first."
        )
    return {
        "status": "ready",
        "intended_runtime": "Foundry Agent Service",
        "start_command": HOSTED_START_COMMAND,
        "provider_mode": "replay",
        "workflow_mode": "strict",
        "replay_artifact": str(artifact),
        "required_env": required_hosted_env(),
        "explanation": (
            "Foundry Agent Service is the intended cloud runtime. ReplayProvider is used "
            "for the smoke test so the hosted agent does not need Fabric credentials."
        ),
    }


def hosted_package(
    settings: Settings | None = None,
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    """Write a minimal, secret-free deployment report for Foundry Agent Service."""
    active = settings or Settings()
    artifact = Path(active.replay_artifact_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    env_lines = "\n".join(f"- `{key}={value}`" for key, value in required_hosted_env().items())
    includes = "\n".join(f"- {item}" for item in PACKAGE_INCLUDES)
    excludes = "\n".join(f"- {item}" for item in PACKAGE_EXCLUDES)
    report = f"""# Concord IQ — Foundry Agent Service deployment package

Foundry Agent Service is the intended cloud runtime for Concord IQ.

## Startup command

```bash
{HOSTED_START_COMMAND}
```

## Provider / workflow mode

- Provider mode: **replay** (uses the committed verified Fabric IQ artifact; no Fabric credentials)
- Workflow mode: **strict** (Microsoft Agent Framework drives each specialist stage)

## Required environment variables

{env_lines}

## Included in the deployment

{includes}

## Excluded from the deployment (never ship)

{excludes}

## Verified replay artifact

- Path: `{artifact}`
- Present: {"yes" if artifact.exists() else "NO — run the Fabric capture first"}

Deploy steps and the real smoke command are in `docs/foundry-agent-service.md`.
This report contains no secrets.
"""
    report_path = output_dir / "package-report.md"
    report_path.write_text(report, encoding="utf-8")
    return report_path


def _urllib_caller(url: str, headers: dict[str, str], body: bytes) -> dict[str, Any]:
    request = Request(url, data=body, headers=headers, method="POST")  # noqa: S310
    try:
        with urlopen(request, timeout=60) as response:  # noqa: S310
            raw = response.read().decode("utf-8")
    except HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:300]
        raise HostedSmokeError(f"Hosted endpoint returned HTTP {error.code}: {detail}") from error
    except URLError as error:
        raise HostedSmokeError(f"Hosted endpoint request failed: {error.reason}") from error
    if raw.lstrip().startswith("data:"):
        lines = [line.removeprefix("data:").strip() for line in raw.splitlines()]
        raw = next((line for line in reversed(lines) if line and line != "[DONE]"), "{}")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise HostedSmokeError("Hosted endpoint returned non-JSON content.") from error
    if not isinstance(payload, dict):
        raise HostedSmokeError("Hosted endpoint returned a non-object JSON response.")
    return payload


HostedCaller = Callable[[str, dict[str, str], bytes], dict[str, Any]]


def hosted_smoke(
    settings: Settings | None = None,
    *,
    caller: HostedCaller = _urllib_caller,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    allow_extra_budget: bool = False,
) -> HostedSmokeProof:
    """Call a deployed Foundry agent once and verify the replay/strict proof.

    Fails closed: requires `ALLOW_CLOUD=true`, a one-call budget, and a configured
    HTTPS endpoint + bearer token. Never prints or persists the token, and never
    contacts Fabric IQ.
    """
    active = settings or Settings()
    active.require_cloud_access("Foundry Agent Service hosted smoke")
    if active.max_cloud_calls < 1:
        raise HostedSmokeError("Set MAX_CLOUD_CALLS=1 for the hosted smoke caller.")
    if active.max_cloud_calls > 1 and not allow_extra_budget:
        raise HostedSmokeError(
            "MAX_CLOUD_CALLS must be 1 for the hosted smoke (one call). Override deliberately."
        )
    endpoint = active.foundry_hosted_endpoint
    token = active.foundry_access_token
    if not endpoint or not token:
        raise HostedSmokeError(
            "Hosted smoke requires FOUNDRY_HOSTED_ENDPOINT and FOUNDRY_ACCESS_TOKEN."
        )
    if not endpoint.startswith("https://"):
        raise HostedSmokeError("FOUNDRY_HOSTED_ENDPOINT must use HTTPS.")

    url = foundry_responses_url(endpoint)
    headers = {
        "Authorization": f"Bearer {token.get_secret_value()}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    # Send the business question with the resolvable term so the deployed agent
    # reconciles Certification Ready through the strict workflow by default.
    inner = json.dumps({"term": EXPECTED_TERM, "question": HOSTED_QUESTION})
    body = json.dumps({"input": inner}).encode("utf-8")

    payload = caller(url, headers, body)
    proof = extract_hosted_proof(payload)
    validate_hosted_proof(proof)

    output_dir.mkdir(parents=True, exist_ok=True)
    report = f"""# Foundry Agent Service hosted-smoke report

Foundry Agent Service cloud runtime smoke: PASSED.

- Question asked: {HOSTED_QUESTION!r}
- Provider mode: {proof.provider_mode}
- Workflow mode: {proof.workflow_mode}
- Term: {proof.term}
- Verdict: {proof.verdict}
- Verification status: {proof.verification_status}
- Specialist steps: {proof.specialist_steps}

The deployed Foundry agent ran the strict Microsoft Agent Framework workflow over
ReplayProvider (the verified Fabric IQ replay artifact). No token is stored here;
no Fabric IQ call was made.
"""
    (output_dir / "hosted-smoke-report.md").write_text(report, encoding="utf-8")
    return proof


def main() -> None:
    parser = argparse.ArgumentParser(description="Concord IQ Foundry Agent Service hosted tooling.")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--dry-run", action="store_true")
    action.add_argument("--package", action="store_true")
    action.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    try:
        if args.dry_run:
            report = hosted_dry_run()
            print(json.dumps(report, indent=2, sort_keys=True))
        elif args.package:
            path = hosted_package()
            print(f"Wrote Foundry deployment report to {path}")
        else:
            proof = hosted_smoke()
            print("Foundry Agent Service cloud runtime smoke verified.")
            print(proof.model_dump_json())
    except (HostedSmokeError, CloudAccessDisabled) as error:
        raise SystemExit(f"Foundry hosted command refused: {error}") from error


if __name__ == "__main__":
    main()
