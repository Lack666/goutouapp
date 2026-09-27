"""Phase 2D smoke checks for transport, database, and LLM coexistence."""

import asyncio
import hmac
import io
import json
import logging

import httpx
from fastapi.testclient import TestClient
from pydantic import BaseModel, SecretStr
from sqlalchemy import Engine, text

from app.core.config import Settings
from app.core.logging import LOGGER_NAME
from app.db.repositories import records
from app.db.session import Database
from app.llm import LLMMessage, StreamChunk, create_llm_provider
from app.llm.mock import MockLLMProvider
from app.main import create_app
from app.services.conversation import ConversationService

MESSAGES = [LLMMessage(role="user", content="synthetic smoke input")]


class SmokeValue(BaseModel):
    ok: bool


def database_settings(database_engine: Engine) -> Settings:
    return Settings(
        app_env="test",
        database_url=SecretStr(database_engine.url.render_as_string(hide_password=False)),
        llm_provider="mock",
        llm_api_key=None,
        _env_file=None,
    )


def test_app_postgres_and_mock_liveness_readiness_status(database_engine: Engine) -> None:
    app = create_app(database_settings(database_engine))
    assert app.state.database._engine is None  # No connection at construction/startup.
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 200
        status = client.get("/api/v1/status")
        assert status.status_code == 200
        assert status.json()["environment"] == "test"
        engine = app.state.database.engine()
        assert engine.pool.checkedout() == 0
    assert app.state.database._engine is None  # Lifespan disposed the pool.


def test_app_starts_and_stays_live_without_postgres() -> None:
    app = create_app(
        Settings(
            app_env="test",
            database_url=SecretStr("postgresql+psycopg://local:private@127.0.0.1:1/offline"),
            llm_provider="mock",
            llm_api_key=None,
            _env_file=None,
        )
    )
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 503
        assert client.get("/health").status_code == 200
    assert app.state.database._engine is None


def test_mock_chat_structured_and_stream_in_application_configuration() -> None:
    app = create_app(
        Settings(app_env="test", llm_provider="mock", llm_api_key=None, _env_file=None)
    )
    provider = create_llm_provider(app.state.settings)
    assert isinstance(provider, MockLLMProvider)
    provider.queue_chat("queued reply")
    provider.queue_structured({"ok": True})
    provider.queue_stream(
        StreamChunk(content="one"), StreamChunk(content="two", finish_reason="stop")
    )

    async def exercise() -> tuple[str, SmokeValue, list[StreamChunk]]:
        reply = await provider.chat(MESSAGES)
        structured = await provider.structured_output(MESSAGES, SmokeValue)
        chunks = [chunk async for chunk in provider.stream(MESSAGES)]
        return reply.content, structured, chunks

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        content, structured, chunks = asyncio.run(exercise())
    assert content == "queued reply"
    assert structured == SmokeValue(ok=True)
    assert [chunk.content for chunk in chunks] == ["one", "two"]
    assert chunks[-1].finish_reason == "stop"


def test_compatible_configuration_uses_only_fake_transport() -> None:
    key = "phase2d-synthetic-key"
    app = create_app(
        Settings(
            app_env="test",
            llm_provider="openai_compatible",
            llm_api_key=key,
            llm_base_url="https://compatible.example/v1",
            llm_model="offline-model",
            _env_file=None,
        )
    )
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert hmac.compare_digest(request.headers["Authorization"], f"Bearer {key}")
        return httpx.Response(
            200,
            json={
                "model": "offline-model",
                "choices": [
                    {"message": {"content": "fake transport reply"}, "finish_reason": "stop"}
                ],
            },
        )

    async def exercise() -> tuple[str, bool]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = create_llm_provider(app.state.settings, client=client)
            result = await provider.chat(MESSAGES)
        return result.content, client.is_closed

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        status = client.get("/api/v1/status")
        assert status.status_code == 200
        assert key not in status.text
        content, closed = asyncio.run(exercise())
    assert content == "fake transport reply"
    assert closed
    assert len(requests) == 1
    assert json.loads(requests[0].content)["model"] == "offline-model"


def test_database_and_mock_provider_share_one_lifecycle(database_engine: Engine) -> None:
    app = create_app(database_settings(database_engine))
    provider = create_llm_provider(app.state.settings)
    assert isinstance(provider, MockLLMProvider)
    provider.queue_chat("ordinary test result")

    with TestClient(app) as client:
        assert client.get("/ready").status_code == 200
        with app.state.database.session() as session:
            user = records.create_user(session)
            service = ConversationService(session)
            conversation = service.create(user.id)
            result = asyncio.run(provider.chat(MESSAGES))
            message = service.add_message(user.id, conversation.id, "assistant", result.content)
            assert message is not None
            user_id, conversation_id, message_id = user.id, conversation.id, message.id
            session.commit()

        with app.state.database.session() as session:
            messages = ConversationService(session).list_messages(user_id, conversation_id)
            assert [(item.id, item.content) for item in messages] == [
                (message_id, "ordinary test result")
            ]
        assert app.state.database.engine().pool.checkedout() == 0
    assert app.state.database._engine is None


def test_python_dependencies_compose_without_fastapi_app(database_engine: Engine) -> None:
    settings = database_settings(database_engine)
    database = Database(settings)
    provider = create_llm_provider(settings)
    assert isinstance(provider, MockLLMProvider)
    provider.queue_chat("injected reply")
    try:
        with database.session() as session:
            assert session.scalar(text("SELECT 1")) == 1
            assert (
                ConversationService(session).list_for_owner(records.create_user(session).id) == []
            )
            assert asyncio.run(provider.chat(MESSAGES)).content == "injected reply"
            session.rollback()
        assert database.engine().pool.checkedout() == 0
    finally:
        database.dispose()
    assert database._engine is None


def test_combined_status_and_logs_hide_all_foundation_secrets() -> None:
    secrets = ("db-password", "llm-key", "auth-token")
    settings = Settings(
        app_env="test",
        app_debug=True,
        database_url="postgresql+psycopg://user:db-password@127.0.0.1:1/offline",
        llm_provider="openai_compatible",
        llm_api_key="llm-key",
        llm_base_url="https://compatible.example/v1",
        llm_model="offline-model",
        _env_file=None,
    )
    output = io.StringIO()
    logger = logging.getLogger(LOGGER_NAME)
    handler = logging.StreamHandler(output)
    logger.addHandler(handler)
    try:
        with TestClient(create_app(settings)) as client:
            status = client.get("/api/v1/status", headers={"Authorization": "Bearer auth-token"})
            readiness = client.get("/ready")
        assert status.status_code == 200
        assert readiness.status_code == 503
        combined = repr(settings) + status.text + readiness.text + output.getvalue()
        if any(secret in combined for secret in secrets):
            raise AssertionError("Foundation secret appeared in a public or logged value")
    finally:
        logger.removeHandler(handler)
