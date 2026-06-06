"""Configuration-driven optional narration provider construction."""

from concord.config import Settings
from concord.llm.base import LLMMode, LLMProvider
from concord.llm.disabled import DisabledLLMProvider
from concord.llm.ollama import OllamaLLMProvider


def create_llm_provider(settings: Settings) -> LLMProvider:
    """Create the configured narrator without changing grounding behavior."""
    try:
        mode = LLMMode(settings.llm_provider)
    except ValueError as error:
        raise ValueError(f"Unknown LLM provider mode: {settings.llm_provider}") from error
    if mode is LLMMode.DISABLED:
        return DisabledLLMProvider()
    if mode is LLMMode.OLLAMA:
        return OllamaLLMProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
        )
    raise ValueError(f"Unsupported LLM provider mode: {mode}")
