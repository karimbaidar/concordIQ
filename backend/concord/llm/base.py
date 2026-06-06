"""Typed contract for optional narration over verified reconciliation facts."""

from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


class LLMMode(StrEnum):
    """Supported narration modes."""

    DISABLED = "disabled"
    OLLAMA = "ollama"


class NarrationTask(StrEnum):
    """The three bounded places where readable narration is permitted."""

    DECISION = "decision"
    VERIFIER = "verifier"
    AUDIT = "audit"


class NarrationModel(BaseModel):
    """Immutable base for narration requests and results."""

    model_config = ConfigDict(frozen=True)


class NarrationRequest(NarrationModel):
    """Verified facts plus deterministic fallback text for one narration task."""

    task: NarrationTask
    facts: dict[str, Any]
    fallback_text: str


class NarrationOutput(NarrationModel):
    """Schema-constrained text returned by a language model."""

    text: str = Field(min_length=1, max_length=1200)


class NarrationResult(NarrationModel):
    """Auditable narration with explicit provenance and fallback state."""

    task: NarrationTask
    text: str = Field(min_length=1, max_length=1200)
    provider_name: str
    model: str | None = None
    generated: bool = False
    fallback_reason: str | None = None


@runtime_checkable
class LLMProvider(Protocol):
    """Language generation contract that cannot return truth-path fields."""

    name: str
    mode: LLMMode
    enabled: bool
    model: str | None

    def narrate(self, request: NarrationRequest) -> NarrationResult:
        """Return generated text or the request's deterministic fallback."""
