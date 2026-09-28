"""Real JWT → FastAPI → AgentService → MockLLM → PostgreSQL tests."""

import io
import json
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
import pytest
from agent_demo import CaptureMock, queue_run
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.core.logging import LOGGER_NAME
from app.db.models import AgentRun, Message, User
from app.db.repositories import records
from app.main import create_app

SECRET = "phase4b-synthetic-secret-with-more-than-32-bytes"
PATH = "/api/v1/conversations/{conversation_id}/agent-runs"


def settings(engine: Engine, **overrides) -> Settings:
    options = dict(
        app_env="test",
        database_url=engine.url.render_as_string(hide_password=False),
        auth_jwt_secret=SECRET,
        auth_jwt_issuer="test-issuer",
        auth_jwt_audience="test-api",
        llm_provider="mock",
        _env_file=None,
    )
    options.update(overrides)
    return Settings(**options)


def signed_token(user_id: UUID, *, key=SECRET, **overrides) -> str:
    claims = {
        "sub": str(user_id),
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        "iss": "test-issuer",
        "aud": "test-api",
    }
    claims.update(overrides)
    return jwt.encode(claims, key, algorithm="HS256")


def headers(user_id: UUID, **overrides) -> dict[str, str]:
    return {"Authorization": f"Bearer {signed_token(user_id, **overrides)}"}


def scope(engine: Engine, *, relationship=False):
    make_session = sessionmaker(bind=engine, expire_on_commit=False)
    with make_session() as db, db.begin():
        user = records.create_user(db)
        relation_id = None
        person_id = None
        if relationship:
            person = records.create_person(db, user.id, "Synthetic person")
            relation = records.create_relationship(db, user.id, person.id, "dating", "active")
            relation_id, person_id = relation.id, person.id
        conversation = records.create_conversation(db, user.id, relation_id)
        return user.id, conversation.id, relation_id, person_id


def persisted(engine: Engine, conversation_id: UUID):
    make_session = sessionmaker(bind=engine, expire_on_commit=False)
    with make_session() as db:
        messages = list(
            db.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at, Message.id)
            )
        )
        runs = list(db.scalars(select(AgentRun).where(AgentRun.conversation_id == conversation_id)))
        return messages, runs


def safety_provider():
    from app.llm.mock import MockLLMProvider

    provider = MockLLMProvider()
    provider.queue_structured(
        {"risk_level": "high", "safety_route_required": True, "risk_categories": ["violence"]}
    )
    return provider


def create_client(engine: Engine, monkeypatch, provider=None):
    app = create_app(settings(engine))
    if provider is not None:
        monkeypatch.setattr("app.api.dependencies.create_llm_provider", lambda _settings: provider)
    return app, TestClient(app)


def test_signed_http_success_persists_and_reuses_runtime(database_engine, monkeypatch):
    user, conversation, _, _ = scope(database_engine)
    provider = safety_provider()
    provider.queue_structured(
        {"risk_level": "high", "safety_route_required": True, "risk_categories": ["violence"]}
    )
    calls = []

    def provider_factory(_settings):
        calls.append(1)
        return provider

    app = create_app(settings(database_engine))
    monkeypatch.setattr("app.api.dependencies.create_llm_provider", provider_factory)
    with TestClient(app) as client:
        assert app.state.agent_service is None
        first = client.post(
            PATH.format(conversation_id=conversation),
            json={"message": "有人正在伤害我"},
            headers=headers(user),
        )
        service = app.state.agent_service
        second = client.post(
            PATH.format(conversation_id=conversation),
            json={"message": "我需要帮助"},
            headers=headers(user),
        )
        assert app.state.agent_service is service
    assert first.status_code == second.status_code == 200
    assert calls == [1]
    payload = first.json()
    assert payload["status"] == "completed"
    assert payload["conversation_id"] == str(conversation)
    assert payload["assistant_message"]["role"] == "assistant"
    assert payload["assistant_message"]["content"]
    assert "analysis" not in payload and "prompt" not in payload
    messages, runs = persisted(database_engine, conversation)
    assert len(messages) == 4 and len(runs) == 2
    assert [item.role for item in messages] == ["user", "assistant", "user", "assistant"]
    assert all(run.status == "completed" for run in runs)
    assert UUID(payload["run_id"]) in {run.id for run in runs}
    assert payload["assistant_message"]["content"] == messages[1].content


@pytest.mark.parametrize(
    "credential",
    [
        None,
        "Bearer malformed.jwt.value",
        "Basic not-a-bearer-token",
        "Bearer wrong-signature",
        "expired",
        "wrong_issuer",
        "wrong_audience",
    ],
)
def test_bad_credentials_are_401_before_service(database_engine, monkeypatch, credential):
    user, conversation, _, _ = scope(database_engine)
    provider_calls = []
    app = create_app(settings(database_engine))
    monkeypatch.setattr(
        "app.api.dependencies.create_llm_provider",
        lambda _settings: provider_calls.append(1),
    )
    if credential == "expired":
        credential = f"Bearer {signed_token(user, exp=datetime.now(UTC) - timedelta(seconds=1))}"
    elif credential == "wrong_issuer":
        credential = f"Bearer {signed_token(user, iss='foreign')}"
    elif credential == "wrong_audience":
        credential = f"Bearer {signed_token(user, aud='foreign')}"
    elif credential == "Bearer wrong-signature":
        credential = "Bearer " + signed_token(
            user, key="another-synthetic-secret-with-more-than-32-bytes"
        )
    with TestClient(app) as client:
        response = client.post(
            PATH.format(conversation_id=conversation),
            json={"message": "private message"},
            headers={"Authorization": credential} if credential else {},
        )
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "invalid_credential"
    assert "private message" not in response.text
    assert provider_calls == []
    assert persisted(database_engine, conversation) == ([], [])


def test_signed_unknown_subject_does_not_create_user(database_engine, monkeypatch):
    _, conversation, _, _ = scope(database_engine)
    unknown = uuid4()
    app, client = create_client(database_engine, monkeypatch, safety_provider())
    with client:
        response = client.post(
            PATH.format(conversation_id=conversation),
            json={"message": "hello"},
            headers=headers(unknown),
        )
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "invalid_credential"
    with sessionmaker(bind=database_engine)() as db:
        assert db.get(User, unknown) is None
    assert persisted(database_engine, conversation) == ([], [])
    assert app.state.agent_service is not None


def test_foreign_conversation_is_404_without_side_effect(database_engine, monkeypatch):
    user_a, conversation_a, _, _ = scope(database_engine)
    user_b, _, _, _ = scope(database_engine)
    provider = safety_provider()
    app, client = create_client(database_engine, monkeypatch, provider)
    with client:
        denied = client.post(
            PATH.format(conversation_id=conversation_a),
            json={"message": "private attempt"},
            headers=headers(user_b),
        )
        allowed = client.post(
            PATH.format(conversation_id=conversation_a),
            json={"message": "owner message"},
            headers=headers(user_a),
        )
    assert denied.status_code == 404
    assert denied.json() == {"error": {"code": "not_found", "message": "Resource not found"}}
    assert allowed.status_code == 200
    messages, runs = persisted(database_engine, conversation_a)
    assert len(messages) == 2 and len(runs) == 1
    assert messages[0].content == "owner message"
    assert app.state.agent_service is not None


@pytest.mark.parametrize(
    "body,path_suffix",
    [
        ({}, None),
        ({"message": " \n "}, None),
        ({"message": "x" * 20001}, None),
        ({"message": "hello", "user_id": str(uuid4())}, None),
        ({"message": "hello", "person_id": str(uuid4())}, None),
        ({"message": "hello", "operation_key": ""}, None),
        ({"message": "hello", "expected_relationship_id": "wrong"}, None),
        ({"message": "hello"}, "not-a-uuid"),
        ({"message": "bad\u0000text"}, None),
    ],
)
def test_invalid_request_returns_uniform_4xx(database_engine, monkeypatch, body, path_suffix):
    user, conversation, _, _ = scope(database_engine)
    app, client = create_client(database_engine, monkeypatch, safety_provider())
    with client:
        response = client.post(
            PATH.format(conversation_id=path_suffix or conversation),
            json=body,
            headers=headers(user),
        )
    assert response.status_code == 422
    assert set(response.json()) == {"error"}
    assert response.json()["error"]["code"] == "validation_error"
    assert persisted(database_engine, conversation) == ([], [])


def test_invalid_unicode_is_validation_error(database_engine, monkeypatch):
    user, conversation, _, _ = scope(database_engine)
    _app, client = create_client(database_engine, monkeypatch, safety_provider())
    payload = json.dumps({"message": "bad" + chr(0xD800)}, ensure_ascii=True).encode("utf-8")
    with client:
        response = client.post(
            PATH.format(conversation_id=conversation),
            content=payload,
            headers={**headers(user), "Content-Type": "application/json"},
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert persisted(database_engine, conversation) == ([], [])


def test_runtime_failure_is_safe_5xx_and_retains_user_message(database_engine, monkeypatch):
    from app.llm.mock import MockLLMProvider

    user, conversation, _, _ = scope(database_engine)
    app, client = create_client(database_engine, monkeypatch, MockLLMProvider())
    with client:
        response = client.post(
            PATH.format(conversation_id=conversation),
            json={"message": "private content"},
            headers=headers(user),
        )
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "agent_failure"
    assert "private content" not in response.text
    messages, runs = persisted(database_engine, conversation)
    assert [message.role for message in messages] == ["user"]
    assert runs[0].status == "failed"
    assert response.json()["error"]["run_id"] == str(runs[0].id)
    assert app.state.agent_service is not None


def test_result_persistence_failure_has_run_id_and_recovery_state(database_engine, monkeypatch):
    user, conversation, _, _ = scope(database_engine)
    app, client = create_client(database_engine, monkeypatch, safety_provider())
    original = records.create_message

    def fail_assistant(db, user_id, conversation_id, role, content, speaker=None):
        if role == "assistant":
            raise RuntimeError("postgresql://private-secret@host")
        return original(db, user_id, conversation_id, role, content, speaker)

    monkeypatch.setattr(records, "create_message", fail_assistant)
    with client:
        response = client.post(
            PATH.format(conversation_id=conversation),
            json={"message": "hello"},
            headers=headers(user),
        )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "persistence_failure"
    assert response.json()["error"]["recovery_status"] == "failed"
    assert "private-secret" not in response.text
    messages, runs = persisted(database_engine, conversation)
    assert [message.role for message in messages] == ["user"]
    assert runs[0].status == "failed"
    assert response.json()["error"]["run_id"] == str(runs[0].id)
    assert app.state.agent_service is not None


def test_memory_warning_is_http_success(database_engine, monkeypatch):
    from app.db.repositories.memory import SQLAlchemyMemoryStore

    user, conversation, _, person = scope(database_engine, relationship=True)
    provider = CaptureMock()
    queue_run(provider, first=True, person_id=person)
    app, client = create_client(database_engine, monkeypatch, provider)

    def fail_save(self, _record):
        raise RuntimeError("private memory failure")

    monkeypatch.setattr(SQLAlchemyMemoryStore, "save_record", fail_save)
    with client:
        response = client.post(
            PATH.format(conversation_id=conversation),
            json={
                "message": "关于对象A：我们已确认关系。我明确同意把这项稳定信息存入长期关系档案。"
            },
            headers=headers(user),
        )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["memory_status"] == "failed"
    assert response.json()["warnings"]
    assert "private memory failure" not in response.text
    assert persisted(database_engine, conversation)[1][0].status == "completed"
    assert app.state.agent_service is not None


def test_openapi_and_health_are_public(database_engine):
    app = create_app(settings(database_engine))
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 200
        assert client.get("/api/v1/status").status_code == 200
    operation = schema["paths"][PATH]["post"]
    assert operation["security"] == [{"BearerCredential": []}]
    assert schema["components"]["securitySchemes"]["BearerCredential"]["type"] == "http"
    for public_path in ("/health", "/ready", "/api/v1/status"):
        assert "security" not in schema["paths"][public_path]["get"]


def test_credential_and_secret_never_enter_response_status_or_app_log(database_engine):
    user, conversation, _, _ = scope(database_engine)
    secret = "secret-unique-phase4b-marker-with-more-than-32-bytes"
    token = signed_token(user, key="wrong-secret-with-more-than-32-bytes")
    config = settings(database_engine, auth_jwt_secret=secret)
    output = io.StringIO()
    logger = logging.getLogger(LOGGER_NAME)
    handler = logging.StreamHandler(output)
    logger.addHandler(handler)
    try:
        with TestClient(create_app(config)) as client:
            response = client.post(
                PATH.format(conversation_id=conversation),
                json={"message": "private relation message"},
                headers={"Authorization": f"Bearer {token}"},
            )
            status = client.get("/api/v1/status")
        combined = repr(config) + response.text + status.text + output.getvalue()
        for sensitive in (secret, token, "private relation message"):
            assert sensitive not in combined
        assert response.status_code == 401
    finally:
        logger.removeHandler(handler)
