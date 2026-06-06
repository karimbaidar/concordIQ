"""Shared fail-closed HTTP infrastructure for Microsoft IQ adapters."""

import json
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from concord.config import Settings
from concord.providers.base import ProviderNotConfigured


class CloudCallBudgetExceeded(RuntimeError):
    """Raised before a cloud request would exceed the configured budget."""


class CloudTransportError(RuntimeError):
    """Raised when a configured cloud endpoint cannot return valid JSON."""


@dataclass(frozen=True, slots=True)
class HttpResult:
    """Transport-neutral JSON response and non-secret headers."""

    payload: dict[str, Any]
    headers: dict[str, str]


class JsonTransport(Protocol):
    """Injectable JSON transport used by adapters and contract tests."""

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any],
    ) -> HttpResult:
        """Send one JSON request."""


class UrllibJsonTransport:
    """Small standard-library transport with JSON and SSE response support."""

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any],
    ) -> HttpResult:
        request = Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=30) as response:  # noqa: S310
                raw = response.read().decode("utf-8")
                response_headers = {
                    key.casefold(): value for key, value in response.headers.items()
                }
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:500]
            raise CloudTransportError(
                f"Cloud endpoint returned HTTP {error.code}: {detail}"
            ) from error
        except URLError as error:
            raise CloudTransportError(f"Cloud endpoint request failed: {error.reason}") from error

        if not raw.strip():
            return HttpResult(payload={}, headers=response_headers)
        if raw.lstrip().startswith("data:"):
            data_lines = [
                line.removeprefix("data:").strip()
                for line in raw.splitlines()
                if line.startswith("data:")
            ]
            raw = next((line for line in reversed(data_lines) if line and line != "[DONE]"), "{}")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as error:
            raise CloudTransportError("Cloud endpoint returned non-JSON content") from error
        if not isinstance(payload, dict):
            raise CloudTransportError("Cloud endpoint returned a non-object JSON response")
        return HttpResult(payload=payload, headers=response_headers)


class GuardedCloudClient:
    """Enforce opt-in and a hard request budget before every HTTP call."""

    def __init__(
        self,
        settings: Settings,
        *,
        provider_name: str,
        transport: JsonTransport | None = None,
    ) -> None:
        self.settings = settings
        self.provider_name = provider_name
        self.transport = transport or UrllibJsonTransport()
        self.cloud_call_count = 0
        self.raw_responses: list[dict[str, Any]] = []

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any],
    ) -> HttpResult:
        self.settings.require_cloud_access(self.provider_name)
        if self.cloud_call_count >= self.settings.max_cloud_calls:
            raise CloudCallBudgetExceeded(
                f"{self.provider_name} exhausted MAX_CLOUD_CALLS={self.settings.max_cloud_calls}."
            )
        if not url.startswith("https://"):
            raise ProviderNotConfigured(f"{self.provider_name} endpoint must use HTTPS.")

        self.cloud_call_count += 1
        result = self.transport.request(method, url, headers=headers, body=body)
        self.raw_responses.append(result.payload)
        return result
