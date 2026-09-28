"""Environment-backed server settings. No external service is required at startup."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
