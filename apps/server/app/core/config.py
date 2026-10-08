"""Environment-backed server settings. No external service is required at startup."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_debug: bool = False
    app_host: str = "127.0.0.1"
    app_port: int = Field(default=8000, ge=1, le=65535)
    database_url: SecretStr | None = None
    llm_provider: str = "mock"
    llm_api_key: SecretStr | None = None
    llm_base_url: SecretStr | None = None
    llm_model: str | None = None
    llm_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    auth_jwt_secret: SecretStr | None = None
    auth_jwt_issuer: str = "goutouapp"
    auth_jwt_audience: str = "goutouapp-api"
    chat_import_artifact_root: Path = Path(".cache/import-artifacts")
    max_chat_import_bytes: int = Field(default=100 * 1024 * 1024, gt=0)
    memory_retention_days: int = Field(default=180, ge=1, le=3650, strict=True)
    memory_challenge_cleanup_grace_hours: int = Field(default=24, ge=1, le=8760, strict=True)
    memory_cleanup_batch_size: int = Field(default=100, ge=1, le=1000, strict=True)
    chat_import_retention_hours: int = Field(default=72, ge=1, le=24 * 365)

    @field_validator(
        "memory_retention_days",
        "memory_challenge_cleanup_grace_hours",
        "memory_cleanup_batch_size",
        mode="before",
    )
    @classmethod
    def retention_integer(cls, value):
        # Environment values are strings; reject fractions, bools and invalid text.
        if isinstance(value, str) and value.isascii() and value.isdecimal():
            return int(value)
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
