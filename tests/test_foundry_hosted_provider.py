"""Foundry-hosted app runtime tests with an injected no-network transport."""

from __future__ import annotations

import json
from typing import Any

import pytest
from concord.api.main import create_app
from concord.config import CloudAccessDisabled, Settings
from concord.orchestration.casefile import ReconciliationCase, ReconciliationRequest
from concord.orchestration.runner import ReconciliationRunner
from concord.providers import (
    FabricIQProvider,
    FoundryHostedProvider,
    FoundryHostedResponseError,
    FoundryIQProvider,
    ProviderNotConfigured,
    provider_statuses,
)
from concord.providers.cloud import HttpResult
from concord.storage.models import ReconciliationRun, SemanticProposal
from fastapi.testclient import TestClient
from sqlalchemy import func, select


class QueueTransport:
    """Return queued Responses payloads and retain only test-visible request data."""

    def __init__(self, *payloads: dict[str, Any]) -> None:
        self.payloads = list(payloads)
        self.requests: list[dict[str, Any]] = []

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any],
    ) -> HttpResult:
        self.requests.append(
            {
                "method": method,
                "url": url,
                "has_authorization": "Authorization" in headers,
                "body": body,
            }
        )
        return HttpResult(payload=self.payloads.pop(0), headers={})


def _settings(**overrides: Any) -> Settings:
    values = {
        "_env_file": None,
        "provider": "foundry_hosted",
        "scenario_pack": "business",
        "allow_cloud": True,
        "max_cloud_calls": 2,
        "foundry_hosted_endpoint": (
            "https://example.services.ai.azure.com/api/projects/demo/agents/"
            "concord-iq/endpoint/protocols/openai/responses?api-version=v1"
        ),
        "foundry_access_token": "test-token-never-persisted",
    }
    values.update(overrides)
    return Settings(**values)


def _hosted_case(case: ReconciliationCase) -> ReconciliationCase:
    hosted_case = case.model_copy(deep=True)
    assert hosted_case.context_packet is not None
    hosted_case.context_packet.provider_metadata["name"] = "ReplayProvider"
    hosted_case.context_packet.provider_metadata["mode"] = "replay"
    hosted_case.context_packet.provider_metadata["uses_cloud"] = False
    for step in hosted_case.agent_trace:
        step.provider_mode = "replay"
    return hosted_case


def _payload(case: ReconciliationCase, **proof_overrides: Any) -> dict[str, Any]:
    proof = {
        "provider_mode": "replay",
        "workflow_mode": "strict",
        "term": case.request.term,
        "verdict": case.verdict,
        "verification_status": case.verification_status,
        "specialist_steps": len(case.agent_trace),
    }
    proof.update(proof_overrides)
    return {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": json.dumps(
                            {
                                "concord_iq_proof": proof,
                                "case": case.model_dump(mode="json"),
                            }
                        ),
                    }
                ],
            }
        ],
    }


@pytest.fixture
def active_hosted_case(
    reconciliation_runner: ReconciliationRunner,
) -> ReconciliationCase:
    return _hosted_case(
        reconciliation_runner.run(
            ReconciliationRequest(
                question="Why do our Active Customer dashboards disagree?",
                term="Active Customer",
            )
        )
    )


def test_foundry_hosted_provider_refuses_when_cloud_is_disabled(
    active_hosted_case: ReconciliationCase,
) -> None:
    transport = QueueTransport(_payload(active_hosted_case))
    provider = FoundryHostedProvider(
        _settings(allow_cloud=False, max_cloud_calls=0),
        transport=transport,
    )

    with pytest.raises(CloudAccessDisabled):
        provider.analyze(active_hosted_case.request)
    assert transport.requests == []


def test_foundry_hosted_provider_requires_endpoint(
    active_hosted_case: ReconciliationCase,
) -> None:
    provider = FoundryHostedProvider(
        _settings(foundry_hosted_endpoint=None),
        transport=QueueTransport(),
    )

    with pytest.raises(ProviderNotConfigured, match="FOUNDRY_HOSTED_ENDPOINT"):
        provider.analyze(active_hosted_case.request)


def test_foundry_hosted_provider_requires_token(
    active_hosted_case: ReconciliationCase,
) -> None:
    provider = FoundryHostedProvider(
        _settings(foundry_access_token=None),
        transport=QueueTransport(),
    )

    with pytest.raises(ProviderNotConfigured, match="FOUNDRY_ACCESS_TOKEN"):
        provider.analyze(active_hosted_case.request)


def test_foundry_hosted_provider_parses_verified_proof_envelope(
    active_hosted_case: ReconciliationCase,
) -> None:
    transport = QueueTransport(_payload(active_hosted_case))
    provider = FoundryHostedProvider(_settings(), transport=transport)

    result = provider.analyze(active_hosted_case.request)

    assert result.verdict == "conflict"
    assert result.verification_status == "passed"
    assert result.context_packet is not None
    metadata = result.context_packet.provider_metadata
    assert metadata["name"] == "Foundry Agent Service"
    assert metadata["mode"] == "foundry_hosted"
    assert metadata["semantic_provider"]["mode"] == "replay"
    assert metadata["concord_iq_proof"]["specialist_steps"] == 10
    assert transport.requests[0]["url"].endswith("/responses?api-version=v1")
    assert "/responses/responses" not in transport.requests[0]["url"]
    assert transport.requests[0]["has_authorization"] is True
    assert "test-token-never-persisted" not in json.dumps(transport.requests)


def test_foundry_hosted_provider_rejects_completed_empty_output(
    active_hosted_case: ReconciliationCase,
) -> None:
    provider = FoundryHostedProvider(
        _settings(),
        transport=QueueTransport({"status": "completed", "output": []}),
    )

    with pytest.raises(FoundryHostedResponseError, match="completed without"):
        provider.analyze(active_hosted_case.request)


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"provider_mode": "fabric_iq"}, "provider_mode"),
        ({"workflow_mode": "fast"}, "workflow_mode"),
        ({"verification_status": "blocked"}, "verification_status"),
    ],
)
def test_foundry_hosted_provider_rejects_invalid_proof_fields(
    active_hosted_case: ReconciliationCase,
    overrides: dict[str, Any],
    match: str,
) -> None:
    provider = FoundryHostedProvider(
        _settings(),
        transport=QueueTransport(_payload(active_hosted_case, **overrides)),
    )

    with pytest.raises(FoundryHostedResponseError, match=match):
        provider.analyze(active_hosted_case.request)


def test_provider_status_requires_both_hosted_endpoint_and_token() -> None:
    without_token = {
        item["mode"]: item for item in provider_statuses(_settings(foundry_access_token=None))
    }
    configured = {item["mode"]: item for item in provider_statuses(_settings())}

    assert without_token["foundry_hosted"]["configured"] is False
    assert configured["foundry_hosted"]["configured"] is True


def test_foundry_hosted_api_routes_without_fabric_calls(
    active_hosted_case: ReconciliationCase,
    reconciliation_runner: ReconciliationRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_fabric_call(*args: object, **kwargs: object) -> None:
        raise AssertionError("FoundryHostedProvider attempted an IQ provider call")

    monkeypatch.setattr(FabricIQProvider, "_retrieve_snapshot", unexpected_fabric_call)
    monkeypatch.setattr(FoundryIQProvider, "_retrieve_snapshot", unexpected_fabric_call)
    transport = QueueTransport(_payload(active_hosted_case), _payload(active_hosted_case))
    settings = _settings(duckdb_path=reconciliation_runner.provider.duckdb_path)
    provider = FoundryHostedProvider(settings, transport=transport)
    app = create_app(
        settings,
        foundry_hosted_provider=provider,
        engine=reconciliation_runner.repository.engine,
    )

    with TestClient(app) as client:
        health = client.get("/health")
        analyzed = client.post(
            "/analyze",
            json={
                "question": active_hosted_case.request.question,
                "term": active_hosted_case.request.term,
            },
        )
        asked = client.post(
            "/ask",
            json={"question": "Why do our active customer dashboards disagree?"},
        )
        statuses = {item["mode"]: item for item in client.get("/providers").json()}

    assert health.status_code == 200
    assert health.json()["runtime"] == "Foundry Agent Service"
    assert analyzed.status_code == 200
    assert analyzed.json()["context_packet"]["provider_metadata"]["mode"] == "foundry_hosted"
    assert asked.status_code == 200
    assert asked.json()["case"]["verdict"] == "conflict"
    assert statuses["foundry_hosted"]["configured"] is True
    assert len(transport.requests) == 2


def test_foundry_hosted_case_supports_court_approval_and_local_governed_rerun(
    active_hosted_case: ReconciliationCase,
    reconciliation_runner: ReconciliationRunner,
    isolated_canonical_registry: None,
) -> None:
    transport = QueueTransport(_payload(active_hosted_case))
    settings = _settings(duckdb_path=reconciliation_runner.provider.duckdb_path)
    provider = FoundryHostedProvider(settings, transport=transport)
    app = create_app(
        settings,
        foundry_hosted_provider=provider,
        engine=reconciliation_runner.repository.engine,
    )

    with TestClient(app) as client:
        analyzed = client.post(
            "/analyze",
            json={
                "question": active_hosted_case.request.question,
                "term": active_hosted_case.request.term,
            },
        )
        run_id = analyzed.json()["run_id"]
        court = client.post(f"/runs/{run_id}/court")
        unauthorized = client.post(
            f"/proposals/{run_id}/approve",
            json={"approver": "Sales"},
        )
        approved = client.post(
            f"/proposals/{run_id}/approve",
            json={"approver": "Data Governance Council"},
        )
        governed = client.post(f"/runs/{run_id}/governed-rerun")

    assert analyzed.status_code == 200
    assert court.status_code == 200
    assert court.json()["source_run_id"] == run_id
    assert unauthorized.status_code == 403
    assert approved.status_code == 200
    assert approved.json()["registry_scope"] == "concord_iq"
    assert governed.status_code == 200
    assert governed.json()["verdict"] == "consistent"
    assert governed.json()["context_packet"]["provider_metadata"]["mode"] == "local"
    assert len(transport.requests) == 1


def test_foundry_hosted_case_import_is_idempotent(
    active_hosted_case: ReconciliationCase,
    reconciliation_runner: ReconciliationRunner,
) -> None:
    transport = QueueTransport(_payload(active_hosted_case), _payload(active_hosted_case))
    settings = _settings(duckdb_path=reconciliation_runner.provider.duckdb_path)
    provider = FoundryHostedProvider(settings, transport=transport)
    app = create_app(
        settings,
        foundry_hosted_provider=provider,
        engine=reconciliation_runner.repository.engine,
    )

    request = {
        "question": active_hosted_case.request.question,
        "term": active_hosted_case.request.term,
    }
    with TestClient(app) as client:
        first = client.post("/analyze", json=request)
        second = client.post("/analyze", json=request)

    assert first.status_code == second.status_code == 200
    assert first.json()["run_id"] == second.json()["run_id"]
    with reconciliation_runner.repository.engine.connect() as connection:
        run_count = connection.scalar(
            select(func.count())
            .select_from(ReconciliationRun)
            .where(ReconciliationRun.id == active_hosted_case.run_id)
        )
        proposal_count = connection.scalar(
            select(func.count())
            .select_from(SemanticProposal)
            .where(SemanticProposal.run_id == active_hosted_case.run_id)
        )
    assert run_count == 1
    assert proposal_count == 1
    assert len(transport.requests) == 2


def test_foundry_hosted_owner_rejection_is_final_and_rerun_remains_conflicted(
    active_hosted_case: ReconciliationCase,
    reconciliation_runner: ReconciliationRunner,
    isolated_canonical_registry: None,
) -> None:
    transport = QueueTransport(_payload(active_hosted_case))
    settings = _settings(duckdb_path=reconciliation_runner.provider.duckdb_path)
    provider = FoundryHostedProvider(settings, transport=transport)
    app = create_app(
        settings,
        foundry_hosted_provider=provider,
        engine=reconciliation_runner.repository.engine,
    )

    with TestClient(app) as client:
        analyzed = client.post(
            "/analyze",
            json={
                "question": active_hosted_case.request.question,
                "term": active_hosted_case.request.term,
            },
        )
        run_id = analyzed.json()["run_id"]
        rejected = client.post(
            f"/proposals/{run_id}/reject",
            json={"approver": "Data Governance Council"},
        )
        repeated = client.post(
            f"/proposals/{run_id}/reject",
            json={"approver": "Data Governance Council"},
        )
        governed = client.post(f"/runs/{run_id}/governed-rerun")

    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert repeated.status_code == 409
    assert governed.status_code == 200
    assert governed.json()["verdict"] == "conflict"
    assert governed.json()["reconciliation_proposal"] is not None
    assert len(transport.requests) == 1
