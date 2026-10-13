"""Generated private markers must never enter public errors or approved logs."""

import errno
import io
import logging
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from test_agent_rest import headers
from test_authorization_security import security_api as phase9b_api
from test_import_api import upload

from app.core.logging import LOGGER_NAME, configure_logging

security_api = phase9b_api


def test_application_log_whitelist_removes_private_parameters():
    marker = uuid4().hex
    logger = configure_logging()
    output = io.StringIO()
    handler = logging.StreamHandler(output)
    logger.addHandler(handler)
    try:
        logger.error("private %s", marker, extra={"authorization": marker}, stack_info=True)
        try:
            raise RuntimeError(marker)
        except RuntimeError:
            logger.exception("Unhandled server error")
    finally:
        logger.removeHandler(handler)
    assert marker not in output.getvalue()
    assert "Traceback" not in output.getvalue() and "Stack" not in output.getvalue()
    assert "suppressed" in output.getvalue()
    assert logging.getLogger("uvicorn.access").disabled


@pytest.mark.parametrize("kind,status", [("http", 403), ("python", 500), ("sql", 500)])
def test_generated_secrets_absent_from_errors_and_logs(security_api, kind, status):
    app, client, _a, _b = security_api
    marker = uuid4().hex
    output = io.StringIO()
    logger = logging.getLogger(LOGGER_NAME)
    handler = logging.StreamHandler(output)
    logger.addHandler(handler)

    @app.get("/synthetic-private-error")
    def fail():
        if kind == "http":
            raise HTTPException(403, detail=marker)
        if kind == "sql":
            raise SQLAlchemyError(marker)
        raise RuntimeError(marker)

    try:
        response = client.get("/synthetic-private-error", headers={"Authorization": marker})
    finally:
        logger.removeHandler(handler)
    assert response.status_code == status
    assert marker not in response.text and marker not in output.getvalue()


def test_storage_exhaustion_has_no_job_or_private_error(security_api, monkeypatch):
    app, client, a, _b = security_api
    marker = uuid4().hex
    original = Path.open

    def disk_full(path, *args, **kwargs):
        if path.suffix == ".part":
            raise OSError(errno.ENOSPC, marker)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", disk_full)
    response = upload(client, a[0])
    assert response.status_code == 500
    assert marker not in response.text
    assert list(app.state.import_artifact_store._root.iterdir()) == []


def test_real_pool_exhaustion_is_bounded_and_content_minimal(security_api, database_engine):
    app, client, a, _b = security_api
    engine = create_engine(
        database_engine.url, pool_size=1, max_overflow=0, pool_timeout=0.05, hide_parameters=True
    )
    app.state.database._engine = engine
    try:
        with engine.connect():
            for path in ("/api/v1/persons", "/api/v1/memory/control"):
                response = client.get(path, headers=headers(a[0]))
                assert response.status_code == 503
                assert "QueuePool" not in response.text and "postgres" not in response.text
    finally:
        engine.dispose()


@pytest.mark.parametrize("stream", [False, True])
def test_agent_rest_and_sse_failures_exclude_generated_private_input(
    security_api, monkeypatch, stream
):
    _app, client, a, _b = security_api
    marker = uuid4().hex

    class FailedProvider:
        async def structured_output(self, *args, **kwargs):
            raise RuntimeError(marker)

    monkeypatch.setattr(
        "app.api.dependencies.create_llm_provider", lambda _settings: FailedProvider()
    )
    suffix = "/stream" if stream else ""
    response = client.post(
        f"/api/v1/conversations/{a[3]}/agent-runs{suffix}",
        headers=headers(a[0]),
        json={"message": marker, "operation_key": uuid4().hex},
    )
    assert response.status_code == (200 if stream else 502)
    assert "agent_failure" in response.text
    assert marker not in response.text
