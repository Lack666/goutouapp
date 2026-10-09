"""Only explicit local development browsers may consume signed resource HTTP."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "https://example.com",
        "http://localhost",
        "http://localhost:8087/",
        "http://user@localhost:8087",
        "http://localhost:8087?token=x",
    ],
)
def test_unsafe_cors_config_rejected(origin):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, dev_cors_origins=[origin])


@pytest.mark.parametrize("environment", ["production", "staging"])
def test_no_development_cors_in_deployment(environment):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env=environment, dev_cors_origins=["http://localhost:8087"])


def test_local_cors_does_not_bypass_auth_and_denies_other_origins():
    with TestClient(
        create_app(Settings(_env_file=None, dev_cors_origins=["http://localhost:8087"]))
    ) as client:
        headers = {
            "Origin": "http://localhost:8087",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        }
        allowed = client.options("/api/v1/persons", headers=headers)
        assert allowed.status_code == 200
        assert allowed.headers["access-control-allow-origin"] == headers["Origin"]
        assert "access-control-allow-credentials" not in allowed.headers
        denied = client.options(
            "/api/v1/persons", headers={**headers, "Origin": "https://example.com"}
        )
        assert denied.status_code == 400
        assert "access-control-allow-origin" not in denied.headers
        response = client.get("/api/v1/persons", headers={"Origin": headers["Origin"]})
        assert response.status_code == 401


def test_default_has_no_cors():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.get("/health", headers={"Origin": "http://localhost:8087"})
        assert "access-control-allow-origin" not in response.headers
