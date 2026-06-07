"""Local-first bootstrap for Concord IQ resources in Microsoft Fabric."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from concord.config import CloudAccessDisabled, Settings
from concord.fabric_seed import (
    DEFAULT_DATA_DIR,
    DEFAULT_OUTPUT_DIR,
    FabricSeedManifest,
    build_ontology_definition,
    export_fabric_seed,
)

# Fabric REST surfaces below are VERIFIED against current Microsoft Learn
# (Ontology REST API, updated 2026-05/06), not assumed:
#   - POST /workspaces/{id}/ontologies                      (Create Ontology, 202 LRO)
#   - POST /workspaces/{id}/ontologies/{id}/updateDefinition?updateMetadata=...
#   - GET  /workspaces/{id}/items?type=Ontology|Lakehouse   (list items, ItemType enum)
#   - POST /workspaces/{id}/lakehouses                       (Create Lakehouse)
#   - POST /workspaces/{id}/assignToCapacity                 (assign capacity)
#   - MCP: /v1/mcp/dataPlane/workspaces/{ws}/items/{ont}/ontologyEndpoint
# Prerequisites the operator must satisfy (see docs/iq-integration.md): the
# "Enable Ontology item (preview)" tenant setting, a contributor role with the
# Item.ReadWrite.All delegated scope, and a supported capacity (F2 is the minimum
# SKU for the Ontology preview). The one best-effort surface is the `.platform`
# definition part payload (its exact schema is not published); if updateDefinition
# is rejected, the bootstrap preserves resources and prints the manual UI fallback.
FABRIC_API_ROOT = "https://api.fabric.microsoft.com/v1"


class FabricBootstrapError(RuntimeError):
    """Raised when a guarded Fabric bootstrap cannot continue."""


class FabricApiError(FabricBootstrapError):
    """A non-success response from the Fabric REST API."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(f"Fabric API returned HTTP {status_code}: {message}")
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class FabricHttpResponse:
    """Small response contract used by the real and test transports."""

    status_code: int
    payload: dict[str, Any]
    headers: dict[str, str]


class FabricTransport(Protocol):
    """Injectable Fabric REST transport."""

    def request(
        self,
        method: str,
        url: str,
        *,
        token: str,
        body: dict[str, Any] | None = None,
    ) -> FabricHttpResponse:
        """Send one authenticated JSON request."""


class UrllibFabricTransport:
    """Standard-library Fabric REST transport that never logs credentials."""

    def request(
        self,
        method: str,
        url: str,
        *,
        token: str,
        body: dict[str, Any] | None = None,
    ) -> FabricHttpResponse:
        encoded = json.dumps(body).encode("utf-8") if body is not None else None
        request = Request(
            url,
            data=encoded,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method=method,
        )
        try:
            with urlopen(request, timeout=30) as response:  # noqa: S310
                raw = response.read().decode("utf-8")
                headers = {key.casefold(): value for key, value in response.headers.items()}
                payload = json.loads(raw) if raw.strip() else {}
                return FabricHttpResponse(response.status, payload, headers)
        except HTTPError as error:
            raw = error.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw) if raw.strip() else {}
            except json.JSONDecodeError:
                payload = {}
            message = str(payload.get("message") or payload.get("errorCode") or raw[:300])
            raise FabricApiError(error.code, message) from error
        except URLError as error:
            raise FabricBootstrapError(f"Fabric API request failed: {error.reason}") from error
        except json.JSONDecodeError as error:
            raise FabricBootstrapError("Fabric API returned invalid JSON.") from error


@dataclass(frozen=True, slots=True)
class FabricResource:
    """A created or reused Fabric resource."""

    resource_id: str
    display_name: str
    action: str


@dataclass(frozen=True, slots=True)
class FabricBootstrapResult:
    """Non-secret results from a Fabric bootstrap."""

    workspace: FabricResource
    lakehouse: FabricResource
    ontology: FabricResource
    mcp_endpoint: str
    ontology_seeded: bool
    capacity_assignment: str
    warnings: tuple[str, ...]


def fabric_mcp_endpoint(workspace_id: str, ontology_id: str) -> str:
    """Build the documented Fabric ontology MCP endpoint."""
    return (
        f"{FABRIC_API_ROOT}/mcp/dataPlane/workspaces/{workspace_id}/"
        f"items/{ontology_id}/ontologyEndpoint"
    )


def _azure_cli_token() -> str:
    try:
        completed = subprocess.run(
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
    except FileNotFoundError as error:
        raise FabricBootstrapError(
            "FABRIC_IQ_ACCESS_TOKEN is empty and Azure CLI is not installed."
        ) from error
    except subprocess.CalledProcessError as error:
        raise FabricBootstrapError(
            "Could not obtain a Fabric token from Azure CLI. Run `az login` or "
            "set FABRIC_IQ_ACCESS_TOKEN in .env."
        ) from error
    token = completed.stdout.strip()
    if not token:
        raise FabricBootstrapError("Azure CLI returned an empty Fabric access token.")
    return token


class FabricApiClient:
    """Minimal idempotent client for supported Fabric bootstrap APIs."""

    def __init__(
        self,
        token: str,
        *,
        transport: FabricTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._token = token
        self._transport = transport or UrllibFabricTransport()
        self._sleep = sleep

    def _request(
        self,
        method: str,
        path_or_url: str,
        body: dict[str, Any] | None = None,
    ) -> FabricHttpResponse:
        url = (
            path_or_url if path_or_url.startswith("https://") else f"{FABRIC_API_ROOT}{path_or_url}"
        )
        response = self._transport.request(
            method,
            url,
            token=self._token,
            body=body,
        )
        if response.status_code >= 400:
            message = str(
                response.payload.get("message")
                or response.payload.get("errorCode")
                or "request failed"
            )
            raise FabricApiError(response.status_code, message)
        return response

    def _list(self, path: str) -> list[dict[str, Any]]:
        values: list[dict[str, Any]] = []
        next_url: str | None = path
        for _ in range(10):
            if next_url is None:
                break
            response = self._request("GET", next_url)
            values.extend(
                item for item in response.payload.get("value", []) if isinstance(item, dict)
            )
            continuation = response.payload.get("continuationUri")
            next_url = str(continuation) if continuation else None
        return values

    def _poll_operation(self, response: FabricHttpResponse) -> None:
        if response.status_code != 202:
            return
        location = response.headers.get("location")
        if not location:
            return
        for _ in range(10):
            self._sleep(1)
            operation = self._request("GET", location)
            status = str(operation.payload.get("status", "")).casefold()
            if status in {"succeeded", "completed"}:
                return
            if status in {"failed", "cancelled"}:
                raise FabricBootstrapError(
                    f"Fabric long-running operation ended with status {status}."
                )
        raise FabricBootstrapError("Fabric long-running operation timed out.")

    def _find_workspace(self, name: str) -> dict[str, Any] | None:
        return next(
            (item for item in self._list("/workspaces") if item.get("displayName") == name),
            None,
        )

    def workspace(
        self,
        name: str,
        *,
        configured_id: str | None,
        capacity_id: str | None,
    ) -> FabricResource:
        if configured_id:
            return FabricResource(configured_id, name, "reused configured ID")
        existing = self._find_workspace(name)
        if existing:
            return FabricResource(str(existing["id"]), name, "reused by name")
        body: dict[str, Any] = {
            "displayName": name,
            "description": "Synthetic Concord IQ hackathon workspace.",
        }
        if capacity_id:
            body["capacityId"] = capacity_id
        response = self._request("POST", "/workspaces", body)
        self._poll_operation(response)
        resource_id = response.payload.get("id")
        if not resource_id:
            created = self._find_workspace(name)
            resource_id = created.get("id") if created else None
        if not resource_id:
            raise FabricBootstrapError("Fabric created the workspace but returned no ID.")
        return FabricResource(str(resource_id), name, "created")

    def assign_capacity(self, workspace_id: str, capacity_id: str | None) -> str:
        if not capacity_id:
            return "not requested"
        response = self._request(
            "POST",
            f"/workspaces/{workspace_id}/assignToCapacity",
            {"capacityId": capacity_id},
        )
        self._poll_operation(response)
        return "requested"

    def _find_item(
        self,
        workspace_id: str,
        item_type: str,
        name: str,
    ) -> dict[str, Any] | None:
        query = urlencode({"type": item_type})
        return next(
            (
                item
                for item in self._list(f"/workspaces/{workspace_id}/items?{query}")
                if item.get("displayName") == name
            ),
            None,
        )

    def lakehouse(
        self,
        workspace_id: str,
        name: str,
        *,
        configured_id: str | None,
    ) -> FabricResource:
        if configured_id:
            return FabricResource(configured_id, name, "reused configured ID")
        existing = self._find_item(workspace_id, "Lakehouse", name)
        if existing:
            return FabricResource(str(existing["id"]), name, "reused by name")
        response = self._request(
            "POST",
            f"/workspaces/{workspace_id}/lakehouses",
            {
                "displayName": name,
                "description": "Tiny synthetic Concord IQ lakehouse.",
            },
        )
        self._poll_operation(response)
        resource_id = response.payload.get("id")
        if not resource_id:
            created = self._find_item(workspace_id, "Lakehouse", name)
            resource_id = created.get("id") if created else None
        if not resource_id:
            raise FabricBootstrapError("Fabric created the lakehouse but returned no ID.")
        return FabricResource(str(resource_id), name, "created")

    def ontology(
        self,
        workspace_id: str,
        name: str,
        *,
        configured_id: str | None,
    ) -> FabricResource:
        if configured_id:
            return FabricResource(configured_id, name, "reused configured ID")
        existing = self._find_item(workspace_id, "Ontology", name)
        if existing:
            return FabricResource(str(existing["id"]), name, "reused by name")
        response = self._request(
            "POST",
            f"/workspaces/{workspace_id}/ontologies",
            {
                "displayName": name,
                "description": "Concord IQ governed business vocabulary.",
            },
        )
        self._poll_operation(response)
        resource_id = response.payload.get("id")
        if not resource_id:
            created = self._find_item(workspace_id, "Ontology", name)
            resource_id = created.get("id") if created else None
        if not resource_id:
            raise FabricBootstrapError("Fabric created the ontology but returned no ID.")
        return FabricResource(str(resource_id), name, "created")

    def update_ontology_definition(
        self,
        workspace_id: str,
        ontology_id: str,
        definition: dict[str, object],
    ) -> None:
        response = self._request(
            "POST",
            (
                f"/workspaces/{workspace_id}/ontologies/{ontology_id}/"
                "updateDefinition?updateMetadata=true"
            ),
            {"definition": definition},
        )
        self._poll_operation(response)


def _manual_fallback(ontology_name: str = "ConcordIQOntology") -> str:
    return f"""Manual ontology fallback:
1. Open the Fabric workspace.
2. Open {ontology_name}.
3. Add or import:
   - fabric_seed/ontology_seed.md
   - fabric_seed/active-customer-snapshot.md
   - fabric_seed/net-revenue-snapshot.md
   - fabric_seed/churned-customer-snapshot.md
4. Publish the ontology.
5. Put the printed MCP endpoint and a fresh token in .env, then run capture."""


def _write_report(
    manifest: FabricSeedManifest,
    *,
    mode: str,
    result: FabricBootstrapResult | None = None,
    error: str | None = None,
) -> Path:
    lines = [
        "# Fabric bootstrap report",
        "",
        f"Mode: {mode}",
        "",
        "- Seed artifacts were regenerated from LocalProvider.",
        "- No access token was written or printed.",
    ]
    if result:
        lines.extend(
            [
                f"- Workspace: {result.workspace.display_name} ({result.workspace.action})",
                f"- Lakehouse: {result.lakehouse.display_name} ({result.lakehouse.action})",
                f"- Ontology: {result.ontology.display_name} ({result.ontology.action})",
                f"- Capacity assignment: {result.capacity_assignment}",
                (
                    "- Generated ontology definition was accepted."
                    if result.ontology_seeded
                    else "- Generated ontology definition needs manual review/import."
                ),
                "- Resource IDs and the MCP endpoint were printed to the terminal only.",
            ]
        )
        lines.extend(f"- Warning: {warning}" for warning in result.warnings)
    if error:
        lines.append(f"- Bootstrap stopped: {error}")
    ontology_name = result.ontology.display_name if result else "ConcordIQOntology"
    lines.extend(["", _manual_fallback(ontology_name), ""])
    path = manifest.output_dir / "bootstrap-report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def dry_run(
    settings: Settings | None = None,
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    data_dir: Path = DEFAULT_DATA_DIR,
) -> FabricSeedManifest:
    """Refresh local artifacts and describe bootstrap without cloud calls."""
    active_settings = settings or Settings()
    manifest = export_fabric_seed(
        active_settings,
        output_dir=output_dir,
        data_dir=data_dir,
    )
    _write_report(manifest, mode="dry run")
    print("Fabric bootstrap dry run complete. No Microsoft API was called.")
    print("Will create or reuse:")
    print(f"- Workspace: {active_settings.fabric_workspace_name}")
    print(f"- Lakehouse: {active_settings.fabric_lakehouse_name}")
    print(f"- Ontology: {active_settings.fabric_ontology_name}")
    print("Will attempt preview ontology definition import after resource creation.")
    print("Required .env values for cloud bootstrap:")
    print("- ALLOW_CLOUD=true")
    print("- FABRIC_IQ_ACCESS_TOKEN=<short-lived token>, or an authenticated Azure CLI")
    print("Optional .env values:")
    print("- FABRIC_CAPACITY_ID")
    print("- FABRIC_WORKSPACE_ID, FABRIC_LAKEHOUSE_ID, FABRIC_ONTOLOGY_ID")
    print("Cloud calls remain disabled unless ALLOW_CLOUD=true.")
    print("The bootstrap never writes .env. Paste printed endpoint/ID values into .env manually.")
    return manifest


def bootstrap(
    settings: Settings | None = None,
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    data_dir: Path = DEFAULT_DATA_DIR,
    transport: FabricTransport | None = None,
    token_loader: Callable[[], str] = _azure_cli_token,
    sleep: Callable[[float], None] = time.sleep,
) -> FabricBootstrapResult:
    """Create or reuse supported Fabric resources after explicit opt-in."""
    active_settings = settings or Settings()
    if not active_settings.allow_cloud:
        raise CloudAccessDisabled(
            "Fabric bootstrap is disabled. Set ALLOW_CLOUD=true for this manual operation."
        )
    manifest = export_fabric_seed(
        active_settings,
        output_dir=output_dir,
        data_dir=data_dir,
    )
    configured_token = active_settings.fabric_iq_access_token
    token = configured_token.get_secret_value() if configured_token else token_loader()
    if not token:
        raise FabricBootstrapError("No Fabric access token is available.")
    client = FabricApiClient(token, transport=transport, sleep=sleep)
    warnings: list[str] = []
    try:
        workspace = client.workspace(
            active_settings.fabric_workspace_name,
            configured_id=active_settings.fabric_workspace_id,
            capacity_id=active_settings.fabric_capacity_id,
        )
        if workspace.action == "created" and active_settings.fabric_capacity_id:
            capacity_assignment = "included at workspace creation"
        else:
            try:
                capacity_assignment = client.assign_capacity(
                    workspace.resource_id,
                    active_settings.fabric_capacity_id,
                )
            except FabricBootstrapError as error:
                capacity_assignment = "failed; manual assignment may be required"
                warnings.append(str(error))
        lakehouse = client.lakehouse(
            workspace.resource_id,
            active_settings.fabric_lakehouse_name,
            configured_id=active_settings.fabric_lakehouse_id,
        )
        ontology = client.ontology(
            workspace.resource_id,
            active_settings.fabric_ontology_name,
            configured_id=active_settings.fabric_ontology_id,
        )
        ontology_seeded = True
        try:
            client.update_ontology_definition(
                workspace.resource_id,
                ontology.resource_id,
                build_ontology_definition(
                    active_settings.fabric_ontology_name,
                    manifest.snapshots,
                ),
            )
        except FabricBootstrapError as error:
            ontology_seeded = False
            warnings.append(f"Preview ontology definition import failed: {error}")
        result = FabricBootstrapResult(
            workspace=workspace,
            lakehouse=lakehouse,
            ontology=ontology,
            mcp_endpoint=fabric_mcp_endpoint(
                workspace.resource_id,
                ontology.resource_id,
            ),
            ontology_seeded=ontology_seeded,
            capacity_assignment=capacity_assignment,
            warnings=tuple(warnings),
        )
    except FabricBootstrapError as error:
        _write_report(manifest, mode="cloud bootstrap", error=str(error))
        raise

    _write_report(manifest, mode="cloud bootstrap", result=result)
    print("Fabric bootstrap completed as far as the current public APIs allowed.")
    print("Paste these non-secret values into .env:")
    print(f"FABRIC_WORKSPACE_ID={result.workspace.resource_id}")
    print(f"FABRIC_LAKEHOUSE_ID={result.lakehouse.resource_id}")
    print(f"FABRIC_ONTOLOGY_ID={result.ontology.resource_id}")
    print(f"FABRIC_IQ_MCP_ENDPOINT={result.mcp_endpoint}")
    print("FABRIC_IQ_ACCESS_TOKEN was neither printed nor persisted.")
    if not result.ontology_seeded:
        print(_manual_fallback(active_settings.fabric_ontology_name))
    for warning in result.warnings:
        print(f"Warning: {warning}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        if args.dry_run:
            dry_run()
        else:
            bootstrap()
    except (CloudAccessDisabled, FabricBootstrapError) as error:
        raise SystemExit(f"Fabric bootstrap refused: {error}") from error


if __name__ == "__main__":
    main()
