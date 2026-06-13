from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

TABLES = [
    "ciq_ontology_entities",
    "ciq_certifications",
    "ciq_readiness_definitions",
    "ciq_required_modules",
    "ciq_required_labs",
    "ciq_learners",
    "ciq_module_completions",
    "ciq_lab_completions",
    "ciq_practice_assessments",
    "ciq_manager_approvals",
    "ciq_certification_ready",
    "ciq_false_ready_learners",
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
    token = result.stdout.strip()
    if not token:
        raise RuntimeError("Azure CLI returned an empty Fabric token.")
    return token


def call(method: str, url: str, token: str, body: dict | None = None) -> tuple[int, dict, dict]:
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req = Request(url, data=data, headers=headers, method=method)

    try:
        with urlopen(req, timeout=120) as response:  # noqa: S310
            raw = response.read().decode("utf-8", "replace")
            parsed = json.loads(raw) if raw.strip() else {}
            return response.status, dict(response.headers), parsed
    except HTTPError as error:
        raw = error.read().decode("utf-8", "replace")
        raise RuntimeError(f"{method} {url} failed with HTTP {error.code}: {raw[:1000]}") from error


def wait_for_operation(location: str, token: str) -> None:
    for _ in range(120):
        status_code, _, payload = call("GET", location, token)

        status = payload.get("Status", payload.get("status"))
        percent = payload.get("PercentComplete", payload.get("percentComplete"))

        print(f"  operation status={status!r} percent={percent!r}")

        if status in (3, "Success", "Succeeded", "Completed", "completed"):
            return
        if status in (4, "Failed", "failed"):
            raise RuntimeError(f"Load operation failed: {json.dumps(payload, indent=2)}")

        time.sleep(5)

    raise TimeoutError(f"Timed out waiting for operation: {location}")


def main() -> None:
    load_dotenv()

    workspace_id = os.environ.get("FABRIC_WORKSPACE_ID", "").strip()
    lakehouse_id = os.environ.get("FABRIC_LAKEHOUSE_ID", "").strip()

    if not workspace_id or not lakehouse_id:
        raise SystemExit("Missing FABRIC_WORKSPACE_ID or FABRIC_LAKEHOUSE_ID in .env or shell.")

    token = fabric_token()
    base = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/lakehouses/{lakehouse_id}"

    for table in TABLES:
        relative_path = f"{REMOTE_DIR.rstrip('/')}/{table}.csv"
        url = f"{base}/tables/{table}/load"
        body = {
            "relativePath": relative_path,
            "pathType": "File",
            "mode": "Overwrite",
            "formatOptions": {
                "header": True,
                "delimiter": ",",
                "format": "Csv",
            },
        }

        print(f"\nLoading {relative_path} -> table {table}")
        status, headers, payload = call("POST", url, token, body)

        location = headers.get("Location") or headers.get("location")
        if location:
            wait_for_operation(location, token)
        else:
            print(f"  submitted status={status}, payload={payload}")

    print("\nListing Lakehouse tables:")
    _, _, payload = call("GET", f"{base}/tables", token)
    for item in payload.get("data", []):
        print(f"- {item.get('name')} [{item.get('format')}]")

    print("\nDONE. Now map/publish Fabric ontology entity type CertificationReady to table ciq_certification_ready.")


if __name__ == "__main__":
    main()
