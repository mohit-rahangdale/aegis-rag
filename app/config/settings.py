"""Application settings and environment configuration."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration management for AegisRAG.

    Loads values from environment variables or a .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core Application
    app_name: str = "aegisrag"
    app_version: str = "0.1.0"
    app_env: Literal["development", "testing", "staging", "production"] = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"

    # Server Network Binding
    host: str = "0.0.0.0"
    port: int = 8000

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "text"] = "json"

    # LLM Gateway Settings (Phase 2)
    gemini_api_key: str | None = None
    mistral_api_key: str | None = None
    primary_llm_provider: str = "gemini"
    fallback_llm_provider: str = "mistral"
    default_gemini_model: str = "gemini-2.5-flash"
    default_mistral_model: str = "mistral-small-latest"
    gateway_timeout_seconds: float = 30.0
    gateway_max_retries: int = 3
    gateway_backoff_factor: float = 1.5
    circuit_breaker_failure_threshold: int = 3
    circuit_breaker_recovery_timeout: float = 30.0

    @property
    def is_production(self) -> bool:
        """Check if application is running in production."""
        return self.app_env == "production"

    @property
    def is_testing(self) -> bool:
        """Check if application is running in test mode."""
        return self.app_env == "testing"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()
