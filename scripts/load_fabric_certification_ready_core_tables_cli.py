from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

TABLES = [
    "ciq_certification_ready",
    "ciq_learners",
    "ciq_false_ready_learners",
    "ciq_certifications",
    "ciq_readiness_definitions",
    "ciq_module_completions",
    "ciq_lab_completions",
    "ciq_practice_assessments",
    "ciq_manager_approvals",
    "ciq_required_modules",
    "ciq_required_labs",
]

REMOTE_DIR = os.environ.get("CIQ_FABRIC_REMOTE_DIR", "Files/concord_iq_seed/learning")


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def fabric_token() -> str:
    result = subprocess.run(
        [
            "az",
            "account",
            "get-access-token",
            "--resource",
            "https://api.fabric.microsoft.com",
            "--query",
            "accessToken",
            "-o",
            "tsv",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def call(method: str, url: str, token: str, body: dict | None = None) -> tuple[int, dict, dict]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=120) as response:  # noqa: S310
            raw = response.read().decode("utf-8", "replace")
            return response.status, dict(response.headers), json.loads(raw) if raw.strip() else {}
    except HTTPError as error:
        raw = error.read().decode("utf-8", "replace")
        raise RuntimeError(f"{method} {url} failed HTTP {error.code}: {raw[:1500]}") from error


def wait(location: str, token: str, table: str) -> bool:
    for _ in range(90):
        _, _, payload = call("GET", location, token)
        status = payload.get("status") or payload.get("Status")
        print(f"  {table}: {status}")

        if str(status).lower() in {"succeeded", "success", "completed", "3"}:
            return True

        if str(status).lower() in {"failed", "4"}:
            print(json.dumps(payload, indent=2))
            return False

        time.sleep(5)

    print(f"  {table}: timed out")
    return False


def main() -> None:
    load_dotenv()

    workspace_id = os.environ.get("FABRIC_WORKSPACE_ID", "").strip()
    lakehouse_id = os.environ.get("FABRIC_LAKEHOUSE_ID", "").strip()

    if not workspace_id or not lakehouse_id:
        raise SystemExit("Missing FABRIC_WORKSPACE_ID or FABRIC_LAKEHOUSE_ID")

    token = fabric_token()
    base = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/lakehouses/{lakehouse_id}"

    ok = []
    failed = []

    for table in TABLES:
        relative_path = f"{REMOTE_DIR.rstrip('/')}/{table}.csv"
        url = f"{base}/tables/{table}/load"

        body = {
            "relativePath": relative_path,
            "pathType": "File",
            "mode": "Overwrite",
            "recursive": False,
            "formatOptions": {
                "format": "Csv",
                "header": True,
                "delimiter": ",",
            },
        }

        print(f"\nLoading {table}")
        print(f"  from {relative_path}")

        try:
            status, headers, payload = call("POST", url, token, body)
            location = headers.get("Location") or headers.get("location")

            if location:
                if wait(location, token, table):
                    ok.append(table)
                else:
                    failed.append(table)
            else:
                print(f"  submitted status={status} payload={payload}")
                ok.append(table)

        except Exception as error:
            print(f"  FAILED: {error}")
            failed.append(table)

    print("\nLoaded tables:")
    for table in ok:
        print(f"- {table}")

    print("\nFailed tables:")
    for table in failed:
        print(f"- {table}")

    print("\nNext required ontology mapping:")
    print("CertificationReady -> ciq_certification_ready")
    print("Learner -> ciq_learners")
    print("FalseReadyLearner -> ciq_false_ready_learners")

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
