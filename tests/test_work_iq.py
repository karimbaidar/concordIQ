"""Work IQ adapter contract tests (artifact proof vs full snapshot).

No test makes a cloud call: the Copilot Retrieval transport is injected and
LocalProvider supplies the deterministic snapshot. Work IQ is a guarded, fail-closed
adapter; it is never marked "verified" here.
"""

from typing import Any

import pytest
from concord.config import CloudAccessDisabled, Settings
from concord.demo import DEMO_SCENARIOS
from concord.providers import (
    LocalProvider,
    WorkIQProvider,
    provider_statuses,
    work_iq_is_configured,
)
from concord.providers.base import ProviderMode, ProviderNotConfigured
from concord.providers.cloud import CloudCallBudgetExceeded, HttpResult
from concord.providers.replay_schema import snapshot_provider_scenario


class QueueTransport:
    def __init__(self, responses: list[HttpResult]) -> None:
        self.responses = responses
        self.requests: list[dict[str, Any]] = []

    def request(self, method, url, *, headers, body) -> HttpResult:
        self.requests.append({"method": method, "url": url, "body": body})
        return self.responses.pop(0)


def _work_settings(*, allow_cloud: bool = True, max_calls: int = 6) -> Settings:
    return Settings(
        _env_file=None,
        provider="work_iq",
        allow_cloud=allow_cloud,
        max_cloud_calls=max_calls,
        work_iq_endpoint="https://graph.microsoft.com/beta/copilot/retrieval",
        work_iq_access_token="super-secret-token",
    )


def _retrieval(term: str, urls: list[str]) -> HttpResult:
    """A Copilot Retrieval response where each hit's passage defines the metric."""
    return HttpResult(
        payload={
            "retrievalHits": [
                {"webUrl": url, "extracts": [{"text": f"This report defines {term} as ..."}]}
                for url in urls
            ]
        },
        headers={},
    )


_ACTIVE_REPORTS = [
    "https://contoso.sharepoint.com/Finance/ActiveCustomer.pbix",
    "https://contoso.sharepoint.com/Sales/ActiveCustomer.pbix",
]


def test_artifact_proof_resolves_concept_and_uses_local_snapshot(
    p2_local_provider: LocalProvider,
) -> None:
    transport = QueueTransport([_retrieval("Active Customer", _ACTIVE_REPORTS)])
    provider = WorkIQProvider(
        _work_settings(), transport=transport, local_provider=p2_local_provider
    )

    concept = provider.resolve_concept("Active Customer")
    assert concept.concept_id == "active_customer"

    proof = provider.artifact_proofs["Active Customer"]
    assert proof["artifact_count"] == 2
    assert tuple(proof["artifact_refs"]) == tuple(_ACTIVE_REPORTS)

    # The deterministic local evidence is present for the actual reconciliation.
    bindings = provider.get_binding_semantics(concept.concept_id)
    assert {binding.owner for binding in bindings} == {"Finance", "Sales", "Customer Success"}

    # The retrieval query is real Work IQ shaped and names the metric.
    sent = transport.requests[0]["body"]
    assert "Active Customer" in sent["queryString"]
    assert sent["dataSource"] == "sharePoint"


def test_full_snapshot_mode_uses_returned_snapshot(
    p2_local_provider: LocalProvider,
) -> None:
    scenario = next(item for item in DEMO_SCENARIOS if item.term == "Active Customer")
    snapshot = snapshot_provider_scenario(p2_local_provider, scenario)
    transport = QueueTransport(
        [
            HttpResult(
                payload={
                    "retrievalHits": [
                        {
                            "webUrl": "https://x/report",
                            "extracts": [{"text": snapshot.model_dump_json()}],
                        }
                    ]
                },
                headers={},
            )
        ]
    )
    provider = WorkIQProvider(_work_settings(), transport=transport)

    assert provider.resolve_concept("Active Customer") == snapshot.concept
    assert provider.artifact_proofs == {}  # full snapshot, not an artifact proof


def test_connectivity_only_response_is_rejected(
    p2_local_provider: LocalProvider,
) -> None:
    transport = QueueTransport(
        [
            HttpResult(
                payload={
                    "retrievalHits": [
                        {
                            "webUrl": "https://x/a",
                            "extracts": [{"text": "Quarterly revenue summary"}],
                        },
                        {"webUrl": "https://x/b", "extracts": [{"text": "Pipeline overview"}]},
                    ]
                },
                headers={},
            )
        ]
    )
    provider = WorkIQProvider(
        _work_settings(), transport=transport, local_provider=p2_local_provider
    )
    with pytest.raises(ProviderNotConfigured, match="fewer than"):
        provider.resolve_concept("Active Customer")


def test_fails_closed_when_cloud_is_disabled() -> None:
    provider = WorkIQProvider(_work_settings(allow_cloud=False), transport=QueueTransport([]))
    with pytest.raises(CloudAccessDisabled):
        provider.resolve_concept("Active Customer")


def test_enforces_cloud_call_budget(p2_local_provider: LocalProvider) -> None:
    transport = QueueTransport([_retrieval("Active Customer", _ACTIVE_REPORTS)])
    provider = WorkIQProvider(
        _work_settings(max_calls=1), transport=transport, local_provider=p2_local_provider
    )

    provider.resolve_concept("Active Customer")  # consumes the single allowed call
    with pytest.raises(CloudCallBudgetExceeded):
        provider.resolve_concept("Net Revenue")


def test_provider_status_reports_work_iq() -> None:
    assert work_iq_is_configured(_work_settings()) is True
    assert work_iq_is_configured(Settings(_env_file=None)) is False

    configured = {item["mode"]: item for item in provider_statuses(_work_settings())}
    assert configured[ProviderMode.WORK_IQ]["name"] == "WorkIQProvider"
    assert configured[ProviderMode.WORK_IQ]["configured"] is True
    assert configured[ProviderMode.WORK_IQ]["cloud"] is True

    bare = {item["mode"]: item for item in provider_statuses(Settings(_env_file=None))}
    assert bare[ProviderMode.WORK_IQ]["configured"] is False
