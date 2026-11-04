"""Environment-backed server settings. No external service is required at startup."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
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
    dev_cors_origins: list[str] = Field(default_factory=list)
    database_url: SecretStr | None = None
    llm_provider: str = "mock"
    llm_api_key: SecretStr | None = None
    llm_base_url: SecretStr | None = None
    llm_model: str | None = None
    llm_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    llm_max_output_tokens: int | None = Field(default=None, ge=1, le=32768)
    ica_mock_execution_enabled: bool = False
    llm_temperature: float | None = Field(default=None, ge=0, le=2)
    llm_thinking: Literal["enabled", "disabled"] | None = None
    eval_live_opt_in: bool = False
    eval_max_requests: int = Field(default=30, ge=1, le=1000)
    eval_max_tokens: int = Field(default=500000, ge=1, le=10000000)
    eval_max_cost_cny: float = Field(default=5.0, gt=0, le=100)
    auth_jwt_secret: SecretStr | None = None
    auth_jwt_issuer: str = "goutouapp"
    auth_jwt_audience: str = "goutouapp-api"
    chat_import_artifact_root: Path = Path(".cache/import-artifacts")
    max_chat_import_bytes: int = Field(default=100 * 1024 * 1024, gt=0)
    max_chat_import_speakers: int = Field(default=1024, ge=1, le=10000)
    memory_retention_days: int = Field(default=180, ge=1, le=3650, strict=True)
    memory_challenge_cleanup_grace_hours: int = Field(default=24, ge=1, le=8760, strict=True)
    memory_cleanup_batch_size: int = Field(default=100, ge=1, le=1000, strict=True)
    chat_import_retention_hours: int = Field(default=72, ge=1, le=24 * 365)
    # One deployment shares a DB, private root and identical admission policy.
    admission_uploads_global: int = Field(default=8, ge=1, le=64)
    admission_uploads_owner: int = Field(default=4, ge=1, le=64)
    admission_processing_global: int = Field(default=2, ge=1, le=32)
    admission_processing_owner: int = Field(default=2, ge=1, le=32)
    admission_storage_global_bytes: int = Field(default=8 * 1024**3, gt=0)
    admission_storage_owner_bytes: int = Field(default=2 * 1024**3, gt=0)
    admission_pending_global: int = Field(default=1000, ge=1, le=10000)
    admission_pending_owner: int = Field(default=100, ge=1, le=10000)
    admission_requests_per_minute: int = Field(default=6000, ge=1, le=100000)
    admission_owner_requests_per_minute: int = Field(default=600, ge=1, le=100000)
    admission_uploads_per_minute: int = Field(default=120, ge=1, le=10000)
    admission_owner_uploads_per_minute: int = Field(default=30, ge=1, le=10000)
    admission_body_idle_seconds: float = Field(default=15, gt=0, le=120)
    admission_body_total_seconds: float = Field(default=120, gt=0, le=600)
    admission_min_free_bytes: int = Field(default=256 * 1024**2, ge=0)
    admission_inventory_limit: int = Field(default=10000, ge=1, le=100000)
    database_pool_size: int = Field(default=5, ge=1, le=64)
    database_max_overflow: int = Field(default=10, ge=0, le=64)
    database_pool_timeout_seconds: float = Field(default=1, gt=0, le=30)

    @model_validator(mode="after")
    def local_cors_only(self):
        from urllib.parse import urlsplit

        if self.dev_cors_origins and self.app_env not in {"development", "test"}:
            raise ValueError("Development CORS is restricted to development/test")
        for origin in self.dev_cors_origins:
            url = urlsplit(origin)
            if (
                url.scheme not in {"http", "https"}
                or url.hostname not in {"localhost", "127.0.0.1", "::1"}
                or not url.port
                or url.path
                or url.query
                or url.fragment
                or url.username
                or url.password
            ):
                raise ValueError("Development CORS requires explicit loopback origins")
        return self

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
