"""Settings work without external services and honor environment values."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings

SETTING_NAMES = (
    "APP_ENV",
    "APP_DEBUG",
    "APP_HOST",
    "APP_PORT",
    "DATABASE_URL",
    "LLM_PROVIDER",
    "LLM_API_KEY",
    "LLM_BASE_URL",
    "LLM_MODEL",
    "LLM_TIMEOUT_SECONDS",
)


def test_defaults_need_no_database_or_llm_key(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in SETTING_NAMES:
        monkeypatch.delenv(name, raising=False)
    settings = Settings(_env_file=None)
    assert settings.app_env == "development"
    assert settings.app_debug is False
    assert settings.app_host == "127.0.0.1"
    assert settings.app_port == 8000
    assert settings.database_url is None
    assert settings.llm_provider == "mock"
    assert settings.llm_api_key is None
    assert settings.llm_base_url is None
    assert settings.llm_model is None
    assert settings.llm_timeout_seconds == 30


def test_environment_override_and_secret_representation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_DEBUG", "true")
    monkeypatch.setenv("APP_HOST", "0.0.0.0")
    monkeypatch.setenv("APP_PORT", "8123")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:db-secret@localhost/db")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("LLM_API_KEY", "api-secret")
    monkeypatch.setenv("LLM_BASE_URL", "https://api-secret@example.test/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "12.5")
    settings = Settings(_env_file=None)
    assert settings.app_env == "test"
    assert settings.app_debug is True
    assert settings.app_host == "0.0.0.0"
    assert settings.app_port == 8123
    assert settings.database_url.get_secret_value().endswith("/db")
    assert settings.llm_api_key.get_secret_value() == "api-secret"
    assert settings.llm_base_url.get_secret_value().endswith("/v1")
    assert settings.llm_model == "test-model"
    assert settings.llm_timeout_seconds == 12.5
    if "api-secret" in repr(settings) or "db-secret" in repr(settings):
        pytest.fail("Secret exposure detected", pytrace=False)


def test_invalid_port_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_PORT", "70000")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_invalid_llm_timeout_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "0")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
