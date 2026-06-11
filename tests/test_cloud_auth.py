"""Deterministic tests for runtime cloud token acquisition.

No test here calls Azure CLI, MSAL, or any Microsoft service: every external
interaction is injected. Tests assert tokens are returned but never surfaced in
exception messages.
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from typing import Any

import pytest
from concord import cloud_auth
from concord.cloud_auth import (
    CloudAuthError,
    get_fabric_access_token,
    get_foundry_access_token,
    get_work_iq_access_token,
)

SECRET = "eyJ0-secret-bearer-token-value"


def _ok_runner(stdout: str):
    def runner(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(list(args), 0, stdout=stdout, stderr="")

    return runner


def _fail_runner(returncode: int = 1, stderr: str = "Please run az login"):
    def runner(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(list(args), returncode, stdout="", stderr=stderr)

    return runner


# --------------------------------------------------------------------------- #
# Foundry / Fabric Azure CLI acquisition
# --------------------------------------------------------------------------- #
def test_foundry_token_success_uses_ai_azure_resource() -> None:
    seen: dict[str, Any] = {}

    def runner(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        seen["args"] = list(args)
        return subprocess.CompletedProcess(list(args), 0, stdout=SECRET + "\n", stderr="")

    token = get_foundry_access_token(runner=runner)
    assert token == SECRET
    assert "https://ai.azure.com" in seen["args"]
    assert "get-access-token" in seen["args"]


def test_fabric_token_success_uses_fabric_resource() -> None:
    seen: dict[str, Any] = {}

    def runner(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        seen["args"] = list(args)
        return subprocess.CompletedProcess(list(args), 0, stdout=SECRET, stderr="")

    token = get_fabric_access_token(runner=runner)
    assert token == SECRET
    assert "https://api.fabric.microsoft.com" in seen["args"]


def test_foundry_token_failure_is_sanitized_and_actionable() -> None:
    with pytest.raises(CloudAuthError) as excinfo:
        get_foundry_access_token(runner=_fail_runner(), tenant_id="contoso")
    message = str(excinfo.value)
    assert "az login" in message
    assert "contoso" in message
    assert SECRET not in message


def test_fabric_token_missing_cli_raises_login_hint() -> None:
    def runner(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("az")

    with pytest.raises(CloudAuthError) as excinfo:
        get_fabric_access_token(runner=runner)
    assert "az login" in str(excinfo.value)


def test_empty_token_is_rejected() -> None:
    with pytest.raises(CloudAuthError):
        get_foundry_access_token(runner=_ok_runner("   \n"))


# --------------------------------------------------------------------------- #
# Work IQ MSAL acquisition
# --------------------------------------------------------------------------- #
class FakeMsalClient:
    """Injectable stand-in for an MSAL PublicClientApplication."""

    def __init__(
        self,
        *,
        accounts: list[Any] | None = None,
        silent: dict[str, Any] | None = None,
        device_flow: dict[str, Any] | None = None,
        device_result: dict[str, Any] | None = None,
    ) -> None:
        self._accounts = accounts or []
        self._silent = silent
        self._device_flow = device_flow or {
            "user_code": "ABCD-EFGH",
            "message": "Go to https://aka.ms/devicelogin and enter ABCD-EFGH",
        }
        self._device_result = device_result
        self.device_started = False

    def get_accounts(self) -> list[Any]:
        return self._accounts

    def acquire_token_silent(self, scopes: list[str], account: Any) -> dict[str, Any] | None:
        return self._silent

    def initiate_device_flow(self, scopes: list[str]) -> dict[str, Any]:
        self.device_started = True
        return self._device_flow

    def acquire_token_by_device_flow(self, flow: dict[str, Any]) -> dict[str, Any]:
        return self._device_result or {}


GRANTED = "User.Read Files.Read.All Sites.Read.All"


def test_work_iq_silent_cache_path() -> None:
    client = FakeMsalClient(
        accounts=[{"username": "user@contoso"}],
        silent={"access_token": SECRET, "scope": GRANTED},
    )
    token = get_work_iq_access_token(client_id="client", tenant_id="tenant", client=client)
    assert token == SECRET
    assert client.device_started is False


def test_work_iq_device_code_fallback() -> None:
    printed: list[str] = []
    client = FakeMsalClient(
        accounts=[],
        device_result={"access_token": SECRET, "scope": GRANTED},
    )
    token = get_work_iq_access_token(
        client_id="client",
        tenant_id="tenant",
        client=client,
        prompt=printed.append,
    )
    assert token == SECRET
    assert client.device_started is True
    # The device-code message (URL + code) is printed, never the token itself.
    assert any("devicelogin" in line for line in printed)
    assert all(SECRET not in line for line in printed)


def test_work_iq_requires_all_scopes() -> None:
    client = FakeMsalClient(
        accounts=[{"u": 1}],
        silent={"access_token": SECRET, "scope": "User.Read"},
    )
    with pytest.raises(CloudAuthError) as excinfo:
        get_work_iq_access_token(client_id="client", tenant_id="tenant", client=client)
    message = str(excinfo.value)
    assert "Files.Read.All" in message
    assert "Sites.Read.All" in message
    assert SECRET not in message


def test_work_iq_license_error_is_sanitized() -> None:
    client = FakeMsalClient(
        accounts=[],
        device_result={
            "error": "invalid_grant",
            "error_description": "AADSTS65001: user has not granted\nsecret-trace",
        },
    )
    with pytest.raises(CloudAuthError) as excinfo:
        get_work_iq_access_token(client_id="client", tenant_id="tenant", client=client)
    message = str(excinfo.value)
    assert "invalid_grant" in message
    assert "secret-trace" not in message


def test_work_iq_requires_client_and_tenant() -> None:
    with pytest.raises(CloudAuthError):
        get_work_iq_access_token(client_id=None, tenant_id="tenant")
    with pytest.raises(CloudAuthError):
        get_work_iq_access_token(client_id="client", tenant_id=None)


def test_required_scopes_constant() -> None:
    assert cloud_auth.WORK_IQ_SCOPES == ("User.Read", "Files.Read.All", "Sites.Read.All")
