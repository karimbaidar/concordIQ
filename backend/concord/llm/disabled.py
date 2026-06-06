"""Deterministic narration provider used by default and in automated tests."""

from concord.llm.base import (
    LLMMode,
    NarrationRequest,
    NarrationResult,
)


class DisabledLLMProvider:
    """Return reviewed fallback text without model or network access."""

    name = "DisabledLLMProvider"
    mode = LLMMode.DISABLED
    enabled = False
    model: str | None = None

    def narrate(self, request: NarrationRequest) -> NarrationResult:
        return NarrationResult(
            task=request.task,
            text=request.fallback_text,
            provider_name=self.name,
            generated=False,
            fallback_reason="LLM narration is disabled.",
        )
