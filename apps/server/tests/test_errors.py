"""Uniform errors do not echo request or exception secrets."""

import io
import logging

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.logging import LOGGER_NAME, configure_logging
from app.main import create_app


def test_not_found_uses_uniform_error_shape() -> None:
    with TestClient(create_app(Settings(app_env="test", _env_file=None))) as client:
        response = client.get("/missing")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Resource not found"}}


def test_http_and_validation_errors_share_shape_without_input_echo() -> None:
    app = create_app(Settings(app_env="test", _env_file=None))

    @app.get("/test-input")
    def test_input(count: int) -> dict[str, int]:
        return {"count": count}

    @app.get("/test-http-error")
    def test_http_error() -> None:
        raise HTTPException(status_code=400, detail="private-chat-text")

    @app.get("/test-auth-error")
    def test_auth_error() -> None:
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Bearer"})

    with TestClient(app) as client:
        invalid = client.get("/test-input?count=private-chat-text")
        explicit = client.get("/test-http-error")
        unauthorized = client.get("/test-auth-error")
    assert invalid.status_code == 422
    assert invalid.json() == {"error": {"code": "validation_error", "message": "Invalid request"}}
    assert explicit.status_code == 400
    assert explicit.json() == {"error": {"code": "http_error", "message": "Request failed"}}
    assert unauthorized.status_code == 401
    assert unauthorized.headers["WWW-Authenticate"] == "Bearer"
    assert "private-chat-text" not in invalid.text + explicit.text


def test_unexpected_error_does_not_log_authorization_or_private_chat() -> None:
    app = create_app(Settings(app_env="test", app_debug=True, _env_file=None))
    logger = logging.getLogger(LOGGER_NAME)
    output = io.StringIO()
    capture = logging.StreamHandler(output)
    logger.addHandler(capture)

    @app.post("/test-unexpected")
    def test_unexpected() -> None:
        raise RuntimeError("private-chat-text")

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/test-unexpected",
                headers={"Authorization": "Bearer test-secret-key"},
                json={"chat": "private-chat-text"},
            )
        assert response.status_code == 500
        assert response.json() == {
            "error": {"code": "internal_error", "message": "Internal server error"}
        }
        combined = output.getvalue() + response.text
        assert "test-secret-key" not in combined
        assert "private-chat-text" not in combined
    finally:
        logger.removeHandler(capture)


def test_logging_configuration_is_idempotent() -> None:
    logger = configure_logging()
    count = len(logger.handlers)
    configure_logging()
    assert len(logger.handlers) == count
