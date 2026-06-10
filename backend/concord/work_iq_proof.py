"""Guarded Work IQ (Microsoft 365 Copilot Retrieval) proof runner.

Work IQ finds *where people wrote the definitions* — the SharePoint / M365 documents
that disagree. This runner attempts one live Microsoft Graph Copilot Retrieval call and
records an honest, fail-closed status:

* ``passed`` — retrieval returned at least one hit; writes ``work-iq-artifact-proof.md``.
* ``license_gated`` — Graph accepted the token/scopes but the tenant lacks the
  Retrieval API entitlement; writes/keeps ``work-iq-license-gate.md``.
* ``permission_blocked`` — Graph rejected the token/scopes (401/403, not a license).
* ``skipped`` — cloud access or credentials are not configured.

The raw Graph response may be written only to ``/tmp`` and is never committed. Tokens,
Authorization headers, and tenant URLs never appear in any committed report.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from concord.config import Settings

QUERY = "Concord IQ Active Customer definition Finance Sales Customer Success trailing days"
RAW_RESPONSE_PATH = Path("/tmp/concord-work-iq-raw.json")  # noqa: S108 — deliberate /tmp-only sink
LICENSE_GATE_PATH = Path("docs/proofs/work-iq-license-gate.md")
ARTIFACT_PROOF_PATH = Path("docs/proofs/work-iq-artifact-proof.md")
STATUS_PATH = Path("artifacts/proof/work-iq-status.json")

OPTIONAL_MODE = "optional_m365_artifact_grounding"

LICENSE_GATE_BODY = """# Work IQ verification status

The Work IQ provider is implemented and permission-verified.

A dedicated Entra app was created and the token contained the required delegated \
Microsoft Graph scopes: `User.Read`, `Files.Read.All`, and `Sites.Read.All`.

A live Microsoft Graph Copilot Retrieval API call was attempted against SharePoint \
content. Microsoft Graph accepted the token/scopes but returned:

```text
Authorization Failed - User does not have valid license
```

This repo does not claim completed Work IQ tenant retrieval. It claims the Work IQ \
path is implemented, guarded, permission-verified, and fail-closed until the tenant \
has the required Retrieval API entitlement.
"""


def _is_license_error(text: str) -> bool:
    lowered = text.lower()
    return "license" in lowered and ("valid license" in lowered or "does not have" in lowered)


def _retrieval_hit_count(payload: Any) -> int:
    if isinstance(payload, dict):
        hits = payload.get("retrievalHits")
        if isinstance(hits, list):
            return len(hits)
    return 0


def _write_status(status: str, *, mode: str = OPTIONAL_MODE, **extra: Any) -> dict[str, Any]:
    """Persist a sanitized machine-readable status (no tokens, no tenant URLs)."""
    document = {
        "component": "work_iq",
        "status": status,
        "mode": mode,
        "data_source": Settings().work_iq_data_source,
        "timestamp_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **extra,
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return document


def _ensure_license_gate_doc() -> None:
    LICENSE_GATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    LICENSE_GATE_PATH.write_text(LICENSE_GATE_BODY, encoding="utf-8")


def _write_artifact_proof(hit_count: int) -> None:
    ARTIFACT_PROOF_PATH.parent.mkdir(parents=True, exist_ok=True)
    body = f"""# Work IQ artifact proof

A live Microsoft Graph Copilot Retrieval call against `{Settings().work_iq_data_source}` \
returned **{hit_count}** retrieval hit(s) for the Concord IQ Active Customer query.

This proves the Work IQ path retrieves real Microsoft 365 definition documents. The raw \
response is stored only at `/tmp/concord-work-iq-raw.json` and is never committed; tenant \
URLs and author identities are not reproduced here.

- **Data source:** `{Settings().work_iq_data_source}`
- **Retrieval hits:** {hit_count}
- **Timestamp (UTC):** {datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}
"""
    ARTIFACT_PROOF_PATH.write_text(body, encoding="utf-8")


def _call_graph(settings: Settings) -> tuple[int | None, str]:
    """Make one Graph retrieval call. Returns (hit_count or None, raw_text)."""
    endpoint = settings.work_iq_endpoint
    token = settings.work_iq_access_token
    assert endpoint and token  # guarded by caller
    body = json.dumps(
        {
            "queryString": QUERY,
            "dataSource": settings.work_iq_data_source,
            "maximumNumberOfResults": 25,
        }
    ).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {token.get_secret_value()}",
        "Content-Type": "application/json",
    }
    request = Request(endpoint, data=body, headers=headers, method="POST")  # noqa: S310
    try:
        with urlopen(request, timeout=60) as response:  # noqa: S310
            raw = response.read().decode("utf-8", "replace")
    except HTTPError as error:
        raw = error.read().decode("utf-8", "replace")
        # Persist only to /tmp for debugging; never returned to a committed report.
        RAW_RESPONSE_PATH.write_text(raw, encoding="utf-8")
        if error.code in (401, 403) and not _is_license_error(raw):
            raise PermissionError(raw[:300]) from error
        return None, raw
    except URLError as error:
        raise ConnectionError(str(error.reason)) from error
    RAW_RESPONSE_PATH.write_text(raw, encoding="utf-8")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        payload = {}
    return _retrieval_hit_count(payload), raw


def run_work_iq_proof(settings: Settings | None = None) -> dict[str, Any]:
    """Attempt the guarded Work IQ proof and return a sanitized status document."""
    active = settings or Settings()
    configured = bool(
        active.allow_cloud and active.work_iq_endpoint and active.work_iq_access_token
    )
    if not configured:
        # No live attempt this run. The committed license-gate artifact still records
        # the permission-verified, license-gated ground truth from the real attempt.
        _ensure_license_gate_doc()
        return _write_status("skipped", detail="ALLOW_CLOUD/WORK_IQ_* not configured")

    try:
        hit_count, raw = _call_graph(active)
    except PermissionError as error:
        return _write_status("permission_blocked", detail=str(error)[:200])
    except ConnectionError as error:
        return _write_status("permission_blocked", detail=f"connection error: {error}"[:200])

    if hit_count is not None and hit_count > 0:
        _write_artifact_proof(hit_count)
        return _write_status("passed", retrieval_hits=hit_count)
    if hit_count == 0:
        # 200 with no hits is not a pass; treat as skipped-with-empty (honest non-claim).
        return _write_status("skipped", detail="retrieval returned zero hits")
    if _is_license_error(raw):
        _ensure_license_gate_doc()
        return _write_status("license_gated", detail="tenant lacks Retrieval API license")
    return _write_status("permission_blocked", detail="graph rejected the request")


def main() -> None:
    """Run the guarded Work IQ proof and print a one-line status."""
    document = run_work_iq_proof()
    print(f"Work IQ proof: {document['status'].upper()} | mode={document['mode']}")


if __name__ == "__main__":
    main()
