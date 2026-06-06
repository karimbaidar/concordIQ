"""Runtime configuration with cloud access disabled by default."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class CloudAccessDisabled(RuntimeError):
    """Raised when a cloud-capable path is requested without explicit permission."""


class Settings(BaseSettings):
    """Concord IQ runtime settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    provider: str = "local"
    allow_cloud: bool = False
    max_cloud_calls: int = 0
    llm_provider: str = "disabled"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"
    database_url: str = "postgresql+psycopg://concord:concord-local-only@localhost:5432/concord_iq"
    duckdb_path: Path = Path("data/concord_iq.duckdb")

    def require_cloud_access(self, provider_name: str) -> None:
        """Fail closed unless cloud access and a positive call budget are explicit."""
        if not self.allow_cloud or self.max_cloud_calls < 1:
            raise CloudAccessDisabled(
                f"{provider_name} is disabled. Set ALLOW_CLOUD=true and "
                "MAX_CLOUD_CALLS to a positive value for a manual smoke test."
            )
