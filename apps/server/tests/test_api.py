"""In-process checks for the two foundation endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health_is_unversioned_liveness() -> None:
    with TestClient(create_app(Settings(app_env="test", _env_file=None))) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_without_database_is_generic_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(create_app(Settings(app_env="test", _env_file=None))) as client:
        assert client.get("/health").status_code == 200
        response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {
        "error": {"code": "database_unavailable", "message": "Database unavailable"}
    }


def test_status_uses_v1_and_exposes_no_secrets() -> None:
    settings = Settings(
        app_env="test",
        database_url="postgresql://user:db-password@localhost/example",
        llm_api_key="test-secret-key",
        _env_file=None,
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/status")
        old_path = client.get("/api/status")
        schema = client.get("/openapi.json").json()

    assert response.status_code == 200
    assert response.json() == {
        "service": "goutoujunshi-server",
        "status": "running",
        "environment": "test",
    }
    assert old_path.status_code == 404
    assert "/api/v1/status" in schema["paths"]
    error_schema = schema["paths"]["/api/v1/status"]["get"]["responses"]["422"]["content"][
        "application/json"
    ]["schema"]
    assert error_schema["$ref"].endswith("/ErrorResponse")
    assert "test-secret-key" not in response.text
    assert "db-password" not in response.text
