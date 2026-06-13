from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import pandas as pd
import pyarrow as pa
from deltalake import write_deltalake

SOURCE_DIR = Path(os.environ.get("CIQ_SEED_OUTPUT_DIR", "fabric_seed/learning_cli"))
DELTA_DIR = Path(os.environ.get("CIQ_DELTA_OUTPUT_DIR", "fabric_seed/learning_delta"))

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

BOOL_COLUMNS = {
    "requires_all_modules",
    "requires_all_labs",
    "requires_manager_approval",
    "required",
    "role_requires_certification",
    "hr_eligible",
    "lms_claimed_ready",
    "manager_approved",
    "assessment_passed",
    "truth_certification_ready",
    "false_ready",
}

INT_COLUMNS = {
    "validity_days",
    "minimum_assessment_score",
    "sequence_number",
    "completion_score",
    "latest_score",
    "attempts",
    "modules_completed",
    "modules_required",
    "labs_completed",
    "labs_required",
    "assessment_score",
    "conflict_reason_count",
}

DATE_COLUMNS = {
    "created_on",
    "effective_on",
    "hire_date",
    "completed_on",
    "last_attempt_on",
    "approved_on",
    "evaluated_on",
}


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def storage_token() -> str:
    result = subprocess.run(
        [
            "az",
            "account",
            "get-access-token",
            "--resource",
            "https://storage.azure.com",
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
        raise RuntimeError("Azure CLI returned an empty OneLake storage token.")
    return token


def onelake_url(workspace_id: str, lakehouse_id: str, relative_path: str) -> str:
    encoded = "/".join(quote(part) for part in relative_path.strip("/").split("/"))
    return f"https://onelake.dfs.fabric.microsoft.com/{workspace_id}/{lakehouse_id}/{encoded}"


def request(
    method: str,
    url: str,
    token: str,
    data: bytes | None = None,
    extra_headers: dict | None = None,
    ignore_404: bool = False,
) -> int:
    headers = {
        "Authorization": f"Bearer {token}",
        "x-ms-version": "2023-11-03",
    }
    if extra_headers:
        headers.update(extra_headers)

    req = Request(url, data=data, headers=headers, method=method)

    try:
        with urlopen(req, timeout=120) as response:  # noqa: S310
            return response.status
    except HTTPError as error:
        if ignore_404 and error.code == 404:
            return 404
        body = error.read().decode("utf-8", "replace")[:800]
        raise RuntimeError(f"{method} failed HTTP {error.code}: {body}") from error
    except URLError as error:
        raise RuntimeError(f"{method} failed: {error.reason}") from error


def ensure_directory(workspace_id: str, lakehouse_id: str, relative_dir: str, token: str) -> None:
    parts = [part for part in relative_dir.strip("/").split("/") if part]
    current = []

    for part in parts:
        current.append(part)
        path = "/".join(current)
        url = onelake_url(workspace_id, lakehouse_id, path) + "?resource=directory"
        try:
            request("PUT", url, token)
        except RuntimeError as error:
            if "HTTP 409" not in str(error):
                raise


def delete_directory(workspace_id: str, lakehouse_id: str, relative_dir: str, token: str) -> None:
    url = onelake_url(workspace_id, lakehouse_id, relative_dir) + "?recursive=true"
    request("DELETE", url, token, ignore_404=True)


def upload_file(workspace_id: str, lakehouse_id: str, local_path: Path, remote_path: str, token: str) -> None:
    body = local_path.read_bytes()
    remote_dir = "/".join(remote_path.split("/")[:-1])
    ensure_directory(workspace_id, lakehouse_id, remote_dir, token)

    base_url = onelake_url(workspace_id, lakehouse_id, remote_path)

    request("PUT", f"{base_url}?resource=file", token)

    if body:
        request(
            "PATCH",
            f"{base_url}?action=append&position=0",
            token,
            data=body,
            extra_headers={"Content-Length": str(len(body))},
        )

    request("PATCH", f"{base_url}?action=flush&position={len(body)}", token)


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    for column in df.columns:
        if column in BOOL_COLUMNS:
            df[column] = (
                df[column]
                .astype("string")
                .str.lower()
                .map({"true": True, "false": False, "1": True, "0": False})
                .astype("boolean")
            )
        elif column in INT_COLUMNS:
            df[column] = pd.to_numeric(df[column], errors="coerce").astype("Int64")
        elif column in DATE_COLUMNS:
            df[column] = pd.to_datetime(df[column], errors="coerce").dt.date
        else:
            df[column] = df[column].astype("string")
    return df


def build_delta_tables() -> None:
    if not SOURCE_DIR.exists():
        raise SystemExit(f"Missing seed directory: {SOURCE_DIR}")

    DELTA_DIR.mkdir(parents=True, exist_ok=True)

    for table in TABLES:
        csv_path = SOURCE_DIR / f"{table}.csv"
        if not csv_path.exists():
            raise FileNotFoundError(csv_path)

        df = pd.read_csv(csv_path, dtype="string")
        df = normalize_dataframe(df)

        target = DELTA_DIR / table
        if target.exists():
            shutil.rmtree(target)

        arrow_table = pa.Table.from_pandas(df, preserve_index=False)
        write_deltalake(str(target), arrow_table, mode="overwrite")

        print(f"Built Delta table: {target}")


def upload_delta_tables() -> None:
    load_dotenv()

    workspace_id = os.environ.get("FABRIC_WORKSPACE_ID", "").strip()
    lakehouse_id = os.environ.get("FABRIC_LAKEHOUSE_ID", "").strip()

    if not workspace_id or not lakehouse_id:
        raise SystemExit("Missing FABRIC_WORKSPACE_ID or FABRIC_LAKEHOUSE_ID in .env or shell.")

    token = storage_token()

    for table in TABLES:
        local_table_dir = DELTA_DIR / table
        remote_table_dir = f"Tables/{table}"

        print(f"\nReplacing OneLake table folder: {remote_table_dir}")
        delete_directory(workspace_id, lakehouse_id, remote_table_dir, token)
        ensure_directory(workspace_id, lakehouse_id, remote_table_dir, token)

        for local_file in sorted(local_table_dir.rglob("*")):
            if local_file.is_dir():
                continue

            inside = local_file.relative_to(local_table_dir).as_posix()
            remote_path = f"{remote_table_dir}/{inside}"
            upload_file(workspace_id, lakehouse_id, local_file, remote_path, token)
            print(f"  uploaded {remote_path}")

    print("\nDONE.")
    print("Delta tables uploaded under OneLake Tables/.")
    print("Now refresh the Lakehouse UI, then map/publish:")
    print("CertificationReady -> ciq_certification_ready")


def main() -> None:
    build_delta_tables()
    upload_delta_tables()


if __name__ == "__main__":
    main()
