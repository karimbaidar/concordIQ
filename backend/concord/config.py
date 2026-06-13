"""Runtime configuration with cloud access disabled by default."""

from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CloudAccessDisabled(RuntimeError):
    """Raised when a cloud-capable path is requested without explicit permission."""


class ScenarioPack(StrEnum):
    """Reviewed deterministic scenario registries."""

    LEARNING = "learning"
    BUSINESS = "business"


class Settings(BaseSettings):
    """Concord IQ runtime settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    provider: str = "local"
    scenario_pack: ScenarioPack = Field(
        default=ScenarioPack.LEARNING,
        validation_alias="CONCORD_SCENARIO_PACK",
    )
    enable_business: bool = Field(
        default=False,
        validation_alias="CONCORD_ENABLE_BUSINESS",
    )
    runtime_switching: bool = Field(
        default=False,
        validation_alias="CONCORD_RUNTIME_SWITCHING",
    )
    default_runtime_profile: Literal[
        "fabric_live",
        "fabric_replay",
        "foundry_live",
        "local",
    ] = Field(
        default="local",
        validation_alias="CONCORD_DEFAULT_RUNTIME",
    )
    agent_workflow_mode: Literal["fast", "strict"] = Field(
        default="fast",
        validation_alias=AliasChoices("CONCORD_WORKFLOW_MODE", "AGENT_WORKFLOW_MODE"),
    )
    allow_cloud: bool = False
    max_cloud_calls: int = 0
    llm_provider: str = "disabled"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"
    database_url: str = "postgresql+psycopg://concord:concord-local-only@localhost:5432/concord_iq"
    duckdb_path: Path = Path("data/concord_iq.duckdb")
    replay_artifact_path: Path = Path("artifacts/replay/sanitized/latest.json")
    learning_replay_artifact_path: Path = Path(
        "artifacts/replay/sanitized/certification-ready.latest.json"
    )
    business_replay_artifact_path: Path = Path("artifacts/replay/sanitized/latest.json")
    court_transcript_path: Path = Path(
        "artifacts/replay/sanitized/certification-ready.deliberation.json"
    )
    replay_require_verified_capture: bool = True
    capture_raw_dir: Path = Path("artifacts/replay/raw")
    capture_sanitized_path: Path = Path("artifacts/replay/sanitized/latest.json")
    foundry_iq_endpoint: str | None = None
    foundry_iq_knowledge_base: str | None = None
    foundry_iq_api_version: str = "2026-04-01"
    foundry_iq_access_token: SecretStr | None = None
    foundry_iq_api_key: SecretStr | None = None
    work_iq_endpoint: str | None = None
    work_iq_access_token: SecretStr | None = None
    work_iq_data_source: str = "sharePoint"
    work_iq_api_version: str = "beta"
    work_iq_client_id: str | None = None
    work_iq_tenant_id: str | None = None
    foundry_hosted_endpoint: str | None = None
    foundry_hosted_agent_id: str | None = None
    foundry_access_token: SecretStr | None = None
    fabric_iq_mcp_endpoint: str | None = None
    fabric_iq_access_token: SecretStr | None = None
    fabric_workspace_name: str = "ConcordIQHackathon"
    fabric_lakehouse_name: str = "ConcordIQLakehouse"
    fabric_ontology_name: str = "ConcordIQOntology"
    fabric_capacity_id: str | None = None
    fabric_workspace_id: str | None = None
    fabric_lakehouse_id: str | None = None
    fabric_ontology_id: str | None = None

    @field_validator("scenario_pack", mode="before")
    @classmethod
    def validate_scenario_pack(cls, value: object) -> object:
        """Return a normalized pack or an actionable configuration error."""
        if isinstance(value, ScenarioPack):
            return value
        normalized = str(value).strip().casefold()
        try:
            return ScenarioPack(normalized)
        except ValueError as error:
            valid = ", ".join(pack.value for pack in ScenarioPack)
            raise ValueError(
                f"Invalid CONCORD_SCENARIO_PACK={value!r}. Valid values: {valid}."
            ) from error

    def require_cloud_access(self, provider_name: str) -> None:
        """Fail closed unless cloud access and a positive call budget are explicit."""
        if not self.allow_cloud or self.max_cloud_calls < 1:
            raise CloudAccessDisabled(
                f"{provider_name} is disabled. Set ALLOW_CLOUD=true and "
                "MAX_CLOUD_CALLS to a positive value for a manual smoke test."
            )
