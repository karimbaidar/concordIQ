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
    "ciq_ontology_entities",
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
        raise RuntimeError("Empty Fabric token from az CLI")
    return token


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
            payload = json.loads(raw) if raw.strip() else {}
            return response.status, dict(response.headers), payload
    except HTTPError as error:
        raw = error.read().decode("utf-8", "replace")
        raise RuntimeError(f"{method} {url} failed HTTP {error.code}: {raw[:2000]}") from error


def wait_session_idle(session_url: str, token: str) -> None:
    for _ in range(120):
        _, _, payload = call("GET", session_url, token)
        state = payload.get("state")
        print(f"Session state: {state}")
        if state == "idle":
            return
        if state in {"dead", "error", "killed", "shutting_down"}:
            raise RuntimeError(json.dumps(payload, indent=2))
        time.sleep(5)
    raise TimeoutError("Timed out waiting for Livy session to become idle")


def run_statement(session_url: str, token: str, code: str) -> dict:
    _, _, payload = call(
        "POST",
        f"{session_url}/statements",
        token,
        {"kind": "pyspark", "code": code},
    )
    statement_id = payload["id"]
    statement_url = f"{session_url}/statements/{statement_id}"

    for _ in range(180):
        _, _, status = call("GET", statement_url, token)
        state = status.get("state")
        print(f"Statement {statement_id} state: {state}")

        if state == "available":
            output = status.get("output", {})
            print(json.dumps(output, indent=2)[:5000])
            if output.get("status") == "error":
                raise RuntimeError(json.dumps(output, indent=2))
            return status

        if state in {"error", "cancelled", "cancelling"}:
            raise RuntimeError(json.dumps(status, indent=2))

        time.sleep(5)

    raise TimeoutError("Timed out waiting for statement")


def main() -> None:
    load_dotenv()

    workspace_id = os.environ.get("FABRIC_WORKSPACE_ID", "").strip()
    lakehouse_id = os.environ.get("FABRIC_LAKEHOUSE_ID", "").strip()

    if not workspace_id or not lakehouse_id:
        raise SystemExit("Missing FABRIC_WORKSPACE_ID or FABRIC_LAKEHOUSE_ID in .env or shell.")

    token = fabric_token()
    sessions_url = (
        f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}"
        f"/lakehouses/{lakehouse_id}/livyapi/versions/2023-12-01/sessions"
    )

    print("Creating Livy Spark session...")
    status, _, session = call("POST", sessions_url, token, {})
    if status not in {200, 201, 202}:
        raise RuntimeError(json.dumps(session, indent=2))

    session_id = session["id"]
    session_url = f"{sessions_url}/{session_id}"
    print(f"Session ID: {session_id}")

    try:
        wait_session_idle(session_url, token)

        tables_literal = repr(TABLES)
        remote_dir_literal = repr(REMOTE_DIR.rstrip("/"))

        code = f'''
tables = {tables_literal}
remote_dir = {remote_dir_literal}

for table in tables:
    path = f"{{remote_dir}}/{{table}}.csv"
    print(f"Loading {{path}} -> {{table}}")

    df = (
        spark.read
        .option("header", "true")
        .option("inferSchema", "true")
        .option("multiLine", "true")
        .option("escape", '"')
        .csv(path)
    )

    (
        df.write
        .format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(table)
    )

print("Registered tables:")
spark.sql("SHOW TABLES").show(200, truncate=False)

print("Certification Ready sample:")
spark.sql("""
SELECT decision, COUNT(*) AS learner_count
FROM ciq_certification_ready
GROUP BY decision
ORDER BY learner_count DESC
""").show(truncate=False)
'''
        run_statement(session_url, token, code)

    finally:
        print("Deleting Livy session...")
        try:
            call("DELETE", session_url, token)
        except Exception as error:
            print(f"Session cleanup warning: {error}")

    print("DONE. Tables should now be registered in Lakehouse metadata.")


if __name__ == "__main__":
    main()
