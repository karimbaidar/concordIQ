"""Runtime cloud token acquisition for Concord IQ developer modes.

Security contract (see AGENTS.md §1.5):

* Tokens are returned to the caller in memory only.
* Token values are NEVER logged, printed, written to ``.env``, or placed on a
  command line. The only on-disk persistence is the user-local MSAL cache,
  which lives outside the repository.
* Every exception message is sanitized — it never echoes a bearer token, an
  ``Authorization`` header, or raw provider output that could contain one.
* Acquisition is injectable so tests never call Azure CLI, MSAL, or Microsoft.

Public API::

    get_foundry_access_token()   # az account get-access-token --resource https://ai.azure.com
    get_fabric_access_token()    # az account get-access-token --resource https://api.fabric.microsoft.com
    get_work_iq_access_token()   # MSAL delegated (silent cache, device-code fallback)
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Protocol

# Resource audiences (kept consistent with the provider implementations).
FOUNDRY_RESOURCE = "https://ai.azure.com"
FABRIC_RESOURCE = "https://api.fabric.microsoft.com"

# Delegated Microsoft Graph scopes Work IQ requires.
WORK_IQ_SCOPES: tuple[str, ...] = ("User.Read", "Files.Read.All", "Sites.Read.All")

# MSAL token cache lives outside the repo so it is never committed.
MSAL_CACHE_PATH = Path.home() / ".cache" / "concord-iq" / "msal-token-cache.json"

# Injected Azure-CLI runner: takes argv, returns a CompletedProcess-like object.
AzCliRunner = Callable[[Sequence[str]], "subprocess.CompletedProcess[str]"]


class CloudAuthError(RuntimeError):
    """A sanitized, user-safe cloud authentication failure."""


def _default_az_runner(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        list(args),
        check=False,
        capture_output=True,
        text=True,
    )


def _login_hint(tenant_id: str | None) -> str:
    tenant = tenant_id or "<configured tenant>"
    return f"Run: az login --tenant {tenant}"


def _acquire_az_token(
    resource: str,
    *,
    label: str,
    runner: AzCliRunner | None = None,
    tenant_id: str | None = None,
) -> str:
    """Obtain a short-lived bearer token via Azure CLI for ``resource``.

    The token is never logged. Only sanitized failure context is surfaced.
    """
    run = runner or _default_az_runner
    args = (
        "az",
        "account",
        "get-access-token",
        "--resource",
        resource,
        "--query",
        "accessToken",
        "-o",
        "tsv",
    )
    try:
        completed = run(args)
    except FileNotFoundError as error:
        raise CloudAuthError(
            f"{label}: Azure CLI (az) is not installed. {_login_hint(tenant_id)}"
        ) from error

    if completed.returncode != 0:
        raise CloudAuthError(
            f"{label}: Azure CLI could not return a token. {_login_hint(tenant_id)}"
        )
    token = (completed.stdout or "").strip()
    if not token:
        raise CloudAuthError(
            f"{label}: Azure CLI returned an empty token. {_login_hint(tenant_id)}"
        )
    return token


def get_foundry_access_token(
    *, runner: AzCliRunner | None = None, tenant_id: str | None = None
) -> str:
    """Acquire a Foundry Agent Service token (audience ``https://ai.azure.com``)."""
    return _acquire_az_token(
        FOUNDRY_RESOURCE,
        label="Foundry Agent Service",
        runner=runner,
        tenant_id=tenant_id,
    )


def get_fabric_access_token(
    *, runner: AzCliRunner | None = None, tenant_id: str | None = None
) -> str:
    """Acquire a Fabric IQ token (audience ``https://api.fabric.microsoft.com``)."""
    return _acquire_az_token(
        FABRIC_RESOURCE,
        label="Fabric IQ",
        runner=runner,
        tenant_id=tenant_id,
    )


class PublicClientLike(Protocol):
    """The slice of an MSAL ``PublicClientApplication`` we depend on."""

    def get_accounts(self) -> list[Any]: ...
    def acquire_token_silent(self, scopes: list[str], account: Any) -> dict[str, Any] | None: ...
    def initiate_device_flow(self, scopes: list[str]) -> dict[str, Any]: ...
    def acquire_token_by_device_flow(self, flow: dict[str, Any]) -> dict[str, Any]: ...


def _missing_scopes(result: dict[str, Any], scopes: Sequence[str]) -> list[str]:
    granted = str(result.get("scope", "")).lower()
    return [scope for scope in scopes if scope.lower() not in granted]


def _validate_token_result(result: dict[str, Any] | None, scopes: Sequence[str]) -> str:
    """Validate an MSAL result and return the access token, or raise sanitized."""
    if not result:
        raise CloudAuthError("Work IQ: no token was returned by Microsoft.")
    token = result.get("access_token")
    if not token:
        # Surface only the short, non-secret error code/description from MSAL.
        code = result.get("error", "unknown_error")
        description = str(result.get("error_description", "")).splitlines()
        first = description[0] if description else ""
        raise CloudAuthError(f"Work IQ: authentication failed ({code}). {first}".strip())
    missing = _missing_scopes(result, scopes)
    if missing:
        raise CloudAuthError(
            "Work IQ: token is missing required delegated scopes: " + ", ".join(missing)
        )
    return str(token)


def _build_public_client(client_id: str, tenant_id: str, cache: Any) -> PublicClientLike:
    """Construct a real MSAL public client (msal imported lazily)."""
    try:
        import msal  # noqa: PLC0415 — optional cloud-only dependency
    except ImportError as error:  # pragma: no cover - exercised only without msal
        raise CloudAuthError(
            "Work IQ device-code auth needs the optional 'msal' dependency. "
            "Install it with: uv sync --extra cloud"
        ) from error
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    return msal.PublicClientApplication(client_id, authority=authority, token_cache=cache)


def _load_msal_cache(cache_path: Path) -> Any:
    """Load (or create) a serializable MSAL cache outside the repository."""
    try:
        import msal  # noqa: PLC0415 — optional cloud-only dependency
    except ImportError:  # pragma: no cover - exercised only without msal
        return None
    cache = msal.SerializableTokenCache()
    if cache_path.exists():
        cache.deserialize(cache_path.read_text(encoding="utf-8"))
    return cache


def _persist_msal_cache(cache: Any, cache_path: Path) -> None:
    if cache is None or not getattr(cache, "has_state_changed", False):
        return
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(cache.serialize(), encoding="utf-8")


def get_work_iq_access_token(
    *,
    client_id: str | None,
    tenant_id: str | None,
    scopes: Sequence[str] = WORK_IQ_SCOPES,
    client: PublicClientLike | None = None,
    cache: Any | None = None,
    cache_path: Path = MSAL_CACHE_PATH,
    prompt: Callable[[str], None] = print,
) -> str:
    """Acquire a delegated Work IQ token via MSAL silent cache or device code.

    Order: silent acquisition from the user-local cache first; if no cached
    account is usable, fall back to device-code authentication. The device-code
    *message* (verification URL + user code) is printed — never the token. The
    returned token is validated to contain every required delegated scope.

    ``client``/``cache`` are injectable so tests never touch MSAL or Microsoft.
    """
    if not client_id or not tenant_id:
        raise CloudAuthError("Work IQ: WORK_IQ_CLIENT_ID and WORK_IQ_TENANT_ID must be configured.")
    scope_list = list(scopes)
    active_cache = cache if cache is not None else _load_msal_cache(cache_path)
    app = client or _build_public_client(client_id, tenant_id, active_cache)

    result: dict[str, Any] | None = None
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(scope_list, account=accounts[0])

    if not result:
        flow = app.initiate_device_flow(scopes=scope_list)
        if "user_code" not in flow:
            raise CloudAuthError("Work IQ: could not start device-code authentication.")
        # flow["message"] is a sign-in instruction (URL + code), not a token.
        prompt(flow.get("message", "Complete device-code sign-in in your browser."))
        result = app.acquire_token_by_device_flow(flow)

    token = _validate_token_result(result, scope_list)
    _persist_msal_cache(active_cache, cache_path)
    return token
