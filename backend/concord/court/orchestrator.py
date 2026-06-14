"""Application wrapper for the Microsoft Agent Framework Semantic Court."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from concord.court.transcript import DeliberationTranscript
from concord.court.workflow import build_semantic_court_workflow
from concord.llm import DisabledLLMProvider, LLMProvider
from concord.orchestration.casefile import ReconciliationCase


class CourtNotReady(ValueError):
    """Raised when a case has not completed enough stages to be deliberated."""


@dataclass(slots=True)
class SemanticCourt:
    """Run a conditional Agent Framework debate over an immutable case."""

    llm: LLMProvider = field(default_factory=DisabledLLMProvider)

    async def deliberate_async(self, case: ReconciliationCase) -> DeliberationTranscript:
        self._require_ready(case)
        before = case.model_dump(mode="json")
        run_result = await build_semantic_court_workflow(self.llm).run(case.model_copy(deep=True))
        outputs = [
            output
            for output in run_result.get_outputs()
            if isinstance(output, DeliberationTranscript)
        ]
        if len(outputs) != 1:
            raise RuntimeError("Semantic Court workflow did not produce exactly one transcript.")
        if case.model_dump(mode="json") != before:
            raise RuntimeError("Semantic Court mutated the caller's reconciliation case.")
        return outputs[0]

    def deliberate(self, case: ReconciliationCase) -> DeliberationTranscript:
        """Synchronous helper for CLI capture, deterministic evals, and unit tests."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.deliberate_async(case))
        raise RuntimeError("Use deliberate_async() while an event loop is running.")

    @staticmethod
    def _require_ready(case: ReconciliationCase) -> None:
        if not case.binding_semantics or not case.execution_results or not case.evidence:
            raise CourtNotReady("The Semantic Court needs a completed case with executed evidence.")
        if case.verdict == "incomplete":
            raise CourtNotReady("The Semantic Court cannot deliberate an incomplete verdict.")
        if (
            case.verification_status != "passed"
            or case.verifier_report is None
            or not case.verifier_report.passed
        ):
            raise CourtNotReady("The Semantic Court requires a verifier-approved case.")
