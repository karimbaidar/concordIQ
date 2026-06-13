from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def token() -> str:
    return subprocess.run(
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
    ).stdout.strip()


def get_json(url: str, access_token: str) -> dict:
    req = Request(url, headers={"Authorization": f"Bearer {access_token}"})
    try:
        with urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        print(error.read().decode("utf-8", "replace"))
        raise


def main() -> None:
    load_dotenv()
    workspace_id = os.environ["FABRIC_WORKSPACE_ID"]
    access_token = token()

    url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items"
    payload = get_json(url, access_token)

    print("Workspace items:")
    for item in payload.get("data", []):
        name = item.get("displayName") or item.get("name")
        item_type = item.get("type")
        item_id = item.get("id")
        print(f"- {name} | type={item_type} | id={item_id}")

    print("\nRaw JSON:")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
