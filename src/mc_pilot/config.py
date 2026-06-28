"""Typed application configuration."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables and an optional `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="MC_PILOT_",
        extra="ignore",
        frozen=True,
    )

    environment: str = "development"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65_535)
    log_level: str = "INFO"
    sqlite_url: str = "sqlite:///data/mc_pilot.db"
    qdrant_url: str = "http://localhost:6333"
    qdrant_timeout_seconds: int = Field(default=2, gt=0, le=30)

    deepseek_api_key: SecretStr | None = Field(default=None, validation_alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com", validation_alias="DEEPSEEK_BASE_URL"
    )
    deepseek_model: str = Field(
        default="deepseek-v4-flash", validation_alias="DEEPSEEK_MODEL"
    )

    def safe_summary(self) -> dict[str, str | int | bool]:
        """Return non-secret configuration suitable for diagnostics."""

        return {
            "environment": self.environment,
            "host": self.host,
            "port": self.port,
            "log_level": self.log_level,
            "sqlite_backend": self.sqlite_url.split(":", maxsplit=1)[0],
            "qdrant_url": self.qdrant_url,
            "qdrant_timeout_seconds": self.qdrant_timeout_seconds,
            "deepseek_configured": bool(
                self.deepseek_api_key and self.deepseek_api_key.get_secret_value()
            ),
            "deepseek_model": self.deepseek_model,
        }


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide immutable configuration instance."""

    return Settings()
