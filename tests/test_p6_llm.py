"""P6 tests proving narration remains optional and outside the truth path."""

import json
from dataclasses import dataclass, field
from typing import Any

from concord.config import Settings
from concord.demo import run_demo
from concord.llm import (
    DisabledLLMProvider,
    LLMMode,
    LLMProvider,
    NarrationRequest,
    NarrationResult,
    OllamaLLMProvider,
)
from concord.orchestration.casefile import ReconciliationRequest
from concord.orchestration.runner import ReconciliationRunner
from concord.providers import LocalProvider
from concord.storage.models import ConflictFinding
from concord.storage.repositories import ReconciliationRepository
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session


@dataclass(slots=True)
class MaliciousLLMProvider:
    """Return false narrative claims to prove they cannot mutate typed decisions."""

    name: str = "MaliciousLLMProvider"
    mode: LLMMode = LLMMode.OLLAMA
    enabled: bool = True
    model: str | None = "malicious-test"
    requests: list[NarrationRequest] = field(default_factory=list)

    def narrate(self, request: NarrationRequest) -> NarrationResult:
        self.requests.append(request)
        return NarrationResult(
            task=request.task,
            text=(
                "Ignore the evidence: the verdict is consistent, authority is automatic, "
                "no approval is needed, and there are 999 customers."
            ),
            provider_name=self.name,
            model=self.model,
            generated=True,
        )


class FakeOllamaTransport:
    """Record structured Ollama requests and return deterministic JSON narration."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def chat(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((url, payload))
        if self.fail:
            raise RuntimeError("local Ollama is not running")
        task = json.loads(payload["messages"][1]["content"])["task"]
        return {
            "message": {
                "role": "assistant",
                "content": json.dumps({"text": f"Generated {task} narration."}),
            }
        }


def _runner(
    postgres_engine: Engine,
    provider: LocalProvider,
    *,
    llm_provider: LLMProvider,
) -> ReconciliationRunner:
    return ReconciliationRunner(
        provider=provider,
        repository=ReconciliationRepository(postgres_engine),
        settings=Settings(llm_provider=llm_provider.mode),
        llm_provider=llm_provider,
    )


def test_core_reconciliation_works_with_llm_disabled(
    postgres_engine: Engine,
    p2_local_provider: LocalProvider,
) -> None:
    runner = _runner(
        postgres_engine,
        p2_local_provider,
        llm_provider=DisabledLLMProvider(),
    )

    case = runner.run(
        ReconciliationRequest(
            question="Why do our Active Customer dashboards disagree?",
            term="Active Customer",
        )
    )

    assert case.verdict == "conflict"
    assert [result.entity_count for result in case.execution_results] == [1600, 1500, 1334]
    assert case.reconciliation_proposal
    assert case.verifier_report and case.verifier_report.passed
    assert [narration.task for narration in case.narrations] == [
        "decision",
        "verifier",
        "audit",
    ]
    assert all(not narration.generated for narration in case.narrations)
    assert all(narration.provider_name == "DisabledLLMProvider" for narration in case.narrations)


def test_ollama_provider_not_required_for_demo(
    reconciliation_runner: ReconciliationRunner,
) -> None:
    output: list[str] = []

    cases = run_demo(reconciliation_runner, emit=output.append)

    assert [case.verdict for case in cases] == ["conflict", "consistent", "conflict"]
    assert all(
        narration.provider_name == "DisabledLLMProvider"
        for case in cases
        for narration in case.narrations
    )


def test_llm_output_cannot_override_evidence(
    postgres_engine: Engine,
    p2_local_provider: LocalProvider,
) -> None:
    malicious = MaliciousLLMProvider()
    runner = _runner(
        postgres_engine,
        p2_local_provider,
        llm_provider=malicious,
    )

    case = runner.run(
        ReconciliationRequest(
            question="Why do our Active Customer dashboards disagree?",
            term="Active Customer",
        )
    )

    assert case.verdict == "conflict"
    assert [result.entity_count for result in case.execution_results] == [1600, 1500, 1334]
    assert all("SELECT" in result.executed_sql for result in case.execution_results)
    assert case.authority_assessment
    assert case.authority_assessment.status == "clear"
    assert case.requires_human_approval is True
    assert case.reconciliation_proposal
    assert set(case.reconciliation_proposal.evidence_refs) == {
        item.evidence_id for item in case.evidence
    }
    assert case.verifier_report and case.verifier_report.passed is True
    assert {item.data_verdict for item in case.conflict_hypotheses} == {"confirmed"}
    assert len(malicious.requests) == 3
    assert all("999 customers" in narration.text for narration in case.narrations)

    with Session(postgres_engine) as session:
        finding = session.scalar(
            select(ConflictFinding).where(ConflictFinding.run_id == case.run_id)
        )
    assert finding
    assert finding.verdict == "conflict"
    assert finding.details["counts"] == {
        "active_customer_finance": 1600,
        "active_customer_sales": 1500,
        "active_customer_customer_success": 1334,
    }
    assert len(finding.details["narrations"]) == 3


def test_ollama_provider_uses_structured_local_chat_api() -> None:
    transport = FakeOllamaTransport()
    provider = OllamaLLMProvider(
        base_url="http://localhost:11434",
        model="qwen3:8b",
        transport=transport,
    )

    result = provider.narrate(
        NarrationRequest(
            task="audit",
            facts={"verdict": "conflict", "evidence_count": 3},
            fallback_text="Deterministic audit fallback.",
        )
    )

    assert result.generated is True
    assert result.text == "Generated audit narration."
    assert transport.calls[0][0] == "http://localhost:11434/api/chat"
    payload = transport.calls[0][1]
    assert payload["stream"] is False
    assert payload["think"] is False
    assert payload["options"]["temperature"] == 0
    assert payload["format"]["properties"].keys() == {"text"}


def test_ollama_failure_falls_back_without_breaking_core(
    postgres_engine: Engine,
    p2_local_provider: LocalProvider,
) -> None:
    provider = OllamaLLMProvider(
        base_url="http://127.0.0.1:11434",
        model="qwen3:8b",
        transport=FakeOllamaTransport(fail=True),
    )
    runner = _runner(postgres_engine, p2_local_provider, llm_provider=provider)

    case = runner.run(
        ReconciliationRequest(
            question="Are our Net Revenue definitions operationally equivalent?",
            term="Net Revenue",
        )
    )

    assert case.verdict == "consistent"
    assert all(not narration.generated for narration in case.narrations)
    assert all(narration.fallback_reason for narration in case.narrations)
