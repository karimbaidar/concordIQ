"""Fail-closed client for a deployed Concord IQ Foundry hosted agent."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict

from concord.config import Settings
from concord.providers.base import ProviderMode, ProviderNotConfigured, QueryResult
from concord.providers.cloud import GuardedCloudClient, JsonTransport

if TYPE_CHECKING:
    from concord.orchestration.casefile import ReconciliationCase, ReconciliationRequest

EXPECTED_PROVIDER_MODE = "replay"
EXPECTED_WORKFLOW_MODE = "strict"
EXPECTED_VERIFICATION_STATUS = "passed"
EXPECTED_SPECIALIST_STEPS = 10


class FoundryHostedResponseError(RuntimeError):
    """Raised when a hosted response cannot prove a valid Concord IQ run."""


class FoundryHostedProof(BaseModel):
    """Proof fields emitted by the Concord IQ hosted Agent Framework workflow."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider_mode: str
    workflow_mode: str
    term: str
    verdict: str
    verification_status: str
    specialist_steps: int


def foundry_responses_url(endpoint: str) -> str:
    """Accept either a Foundry protocol base URL or the full Responses URL."""
    parsed = urlsplit(endpoint.strip())
    path = parsed.path.rstrip("/")
    response_path = path if path.endswith("/responses") else f"{path}/responses"
    return urlunsplit((parsed.scheme, parsed.netloc, response_path, parsed.query, parsed.fragment))


def _find_output_text(payload: Any) -> str | None:
    if isinstance(payload, dict):
        if payload.get("type") == "output_text" and isinstance(payload.get("text"), str):
            return payload["text"]
        for value in payload.values():
            found = _find_output_text(value)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _find_output_text(item)
            if found is not None:
                return found
    return None


def parse_foundry_hosted_response(
    payload: dict[str, Any],
    *,
    requested_term: str,
) -> tuple[FoundryHostedProof, ReconciliationCase]:
    """Validate the hosted proof envelope and return its typed case."""
    from concord.orchestration.casefile import ReconciliationCase

    response_status = payload.get("status")
    if response_status not in {None, "completed"}:
        raise FoundryHostedResponseError(
            f"Foundry hosted response ended with status {response_status!r}, not 'completed'."
        )
    text = _find_output_text(payload)
    if not text:
        raise FoundryHostedResponseError(
            "Foundry hosted response completed without Concord IQ output."
        )
    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise FoundryHostedResponseError(
            "Foundry hosted response output was not valid JSON."
        ) from error
    if not isinstance(document, dict):
        raise FoundryHostedResponseError("Foundry hosted output must be a JSON object.")

    try:
        proof = FoundryHostedProof.model_validate(document.get("concord_iq_proof"))
        case = ReconciliationCase.model_validate(document.get("case"))
    except ValueError as error:
        raise FoundryHostedResponseError(
            f"Foundry hosted proof envelope was malformed: {error}"
        ) from error

    failures: list[str] = []
    if proof.provider_mode != EXPECTED_PROVIDER_MODE:
        failures.append(
            f"provider_mode is {proof.provider_mode!r}, expected {EXPECTED_PROVIDER_MODE!r}"
        )
    if proof.workflow_mode != EXPECTED_WORKFLOW_MODE:
        failures.append(
            f"workflow_mode is {proof.workflow_mode!r}, expected {EXPECTED_WORKFLOW_MODE!r}"
        )
    if proof.verification_status != EXPECTED_VERIFICATION_STATUS:
        failures.append(
            "verification_status is "
            f"{proof.verification_status!r}, expected {EXPECTED_VERIFICATION_STATUS!r}"
        )
    if proof.specialist_steps != EXPECTED_SPECIALIST_STEPS:
        failures.append(
            f"specialist_steps is {proof.specialist_steps}, expected {EXPECTED_SPECIALIST_STEPS}"
        )
    if proof.term.casefold() != requested_term.casefold():
        failures.append(f"term is {proof.term!r}, expected {requested_term!r}")
    if case.request.term != proof.term:
        failures.append("case request term does not match concord_iq_proof.term")
    if case.verdict != proof.verdict:
        failures.append("case verdict does not match concord_iq_proof.verdict")
    if case.verification_status != proof.verification_status:
        failures.append("case verifier status does not match concord_iq_proof")
    if not case.verifier_report or not case.verifier_report.passed:
        failures.append("case verifier report did not pass")
    if len(case.agent_trace) != proof.specialist_steps:
        failures.append("case agent trace length does not match specialist_steps")
    if failures:
        raise FoundryHostedResponseError(
            "Foundry hosted proof was rejected: " + "; ".join(failures)
        )
    return proof, case


class FoundryHostedProvider:
    """Runtime adapter for a deployed Concord IQ Foundry Agent Service endpoint.

    This is intentionally not a semantic ``GroundingProvider``. The hosted agent
    already ran the full Agent Framework workflow and returns a verified typed
    case, so the main app must render that case rather than execute it again.
    """

    name = "Foundry Agent Service"
    mode = ProviderMode.FOUNDRY_HOSTED
    uses_cloud = True
    data_type = "hosted runtime"

    def __init__(self, settings: Settings, *, transport: JsonTransport | None = None) -> None:
        self.settings = settings
        self.scenario_pack = settings.scenario_pack
        self.client = GuardedCloudClient(
            settings,
            provider_name=self.name,
            transport=transport,
        )

    def analyze(self, request: ReconciliationRequest) -> ReconciliationCase:
        """Call the hosted Responses endpoint once and return its verified case."""
        self.settings.require_cloud_access(self.name)
        endpoint = self.settings.foundry_hosted_endpoint
        if not endpoint:
            raise ProviderNotConfigured("FoundryHostedProvider requires FOUNDRY_HOSTED_ENDPOINT.")
        token = self.settings.foundry_access_token
        if not token:
            raise ProviderNotConfigured("FoundryHostedProvider requires FOUNDRY_ACCESS_TOKEN.")

        headers = {
            "Authorization": f"Bearer {token.get_secret_value()}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Foundry-Features": "HostedAgents=V1Preview",
        }
        period = request.period
        body: dict[str, Any] = {
            "input": json.dumps(
                {
                    "term": request.term,
                    "question": request.question,
                    "period": f"{period.start_date.isoformat()}/{period.end_date.isoformat()}",
                }
            ),
            "stream": False,
        }
        endpoint_path = urlsplit(endpoint).path
        agent_id = self.settings.foundry_hosted_agent_id
        if agent_id and "/agents/" not in endpoint_path and "/applications/" not in endpoint_path:
            body["agent_reference"] = {
                "type": "agent_reference",
                "name": agent_id,
            }

        result = self.client.request(
            "POST",
            foundry_responses_url(endpoint),
            headers=headers,
            body=body,
        )
        proof, case = parse_foundry_hosted_response(
            result.payload,
            requested_term=request.term,
        )
        return self._with_runtime_metadata(case, proof)

    def nl_query(self, question: str) -> QueryResult:
        """Resolve a question locally to a term before one hosted runtime call."""
        from concord.providers.local import LocalProvider

        result = LocalProvider.for_scenario_pack(
            self.settings.scenario_pack,
            duckdb_path=self.settings.duckdb_path,
        ).nl_query(question)
        return result.model_copy(
            update={"grounding_provider": "Foundry Agent Service (local ontology routing)"}
        )

    def _with_runtime_metadata(
        self,
        case: ReconciliationCase,
        proof: FoundryHostedProof,
    ) -> ReconciliationCase:
        hosted_case = case.model_copy(deep=True)
        if hosted_case.context_packet is None:
            raise FoundryHostedResponseError("Foundry hosted case is missing its context packet.")
        semantic_provider = dict(hosted_case.context_packet.provider_metadata)
        hosted_case.context_packet.provider_metadata = {
            "name": self.name,
            "mode": self.mode.value,
            "uses_cloud": True,
            "data_type": self.data_type,
            "runtime": self.name,
            "semantic_provider": semantic_provider,
            "concord_iq_proof": proof.model_dump(mode="json"),
        }
        return hosted_case
