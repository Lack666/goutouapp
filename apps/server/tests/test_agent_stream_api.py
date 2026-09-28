"""Signed SSE → AgentService → runtime → real PostgreSQL integration."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
import pytest
from agent_demo import CaptureMock, queue_run
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import sessionmaker

from app.agent.dependencies import RuntimeDependencies
from app.agent.memory import MemoryService
from app.agent.runtime import AgentRuntime
from app.api.streaming import ManagedRunStreamingResponse
from app.core.config import Settings
from app.core.logging import LOGGER_NAME
from app.db.models import AgentRun, MemoryRecordRow, Message
from app.db.repositories import records
from app.db.repositories.memory import SQLAlchemyMemoryStore
from app.llm.mock import MockLLMProvider
from app.main import create_app
from app.schemas.stream_event import NETWORK_EVENT_ADAPTER
from app.services.agent_service import AgentService, actor_from_verified_identity

SECRET = "phase4c-signed-stream-synthetic-secret-over-32-bytes"
PATH = "/api/v1/conversations/{conversation_id}/agent-runs/stream"


def config(engine: Engine):
    return Settings(
        app_env="test",
        database_url=engine.url.render_as_string(hide_password=False),
        auth_jwt_secret=SECRET,
        auth_jwt_issuer="stream-issuer",
        auth_jwt_audience="stream-api",
        llm_provider="mock",
        _env_file=None,
    )


def token(user_id: UUID, **changes):
    claims = {
        "sub": str(user_id),
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        "iss": "stream-issuer",
        "aud": "stream-api",
    }
    claims.update(changes)
    return jwt.encode(claims, SECRET, algorithm="HS256")


def headers(user_id: UUID):
    return {"Authorization": f"Bearer {token(user_id)}"}


def scope(engine: Engine, *, relationship=False):
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db, db.begin():
        user = records.create_user(db)
        relation_id = person_id = None
        if relationship:
            person = records.create_person(db, user.id, "Synthetic person")
            relation = records.create_relationship(db, user.id, person.id, "dating", "active")
            relation_id, person_id = relation.id, person.id
        conversation = records.create_conversation(db, user.id, relation_id)
        return user.id, conversation.id, person_id


def persisted(engine: Engine, conversation_id: UUID):
    with sessionmaker(bind=engine)() as db:
        messages = list(
            db.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at, Message.id)
            )
        )
        runs = list(db.scalars(select(AgentRun).where(AgentRun.conversation_id == conversation_id)))
        return messages, runs


def parse(response):
    assert response.headers["content-type"].startswith("text/event-stream")
    frames = []
    for block in response.content.split(b"\n\n"):
        if not block:
            continue
        name, data = block.decode("utf-8").split("\n")
        event = NETWORK_EVENT_ADAPTER.validate_json(data.removeprefix("data: "))
        assert name == f"event: {event.event}"
        frames.append(event)
    return frames


def safety_provider(count=1):
    provider = MockLLMProvider()
    for _ in range(count):
        provider.queue_structured(
            {"risk_level": "high", "safety_route_required": True, "risk_categories": ["violence"]}
        )
    return provider


def test_signed_success_is_one_run_and_committed_before_completed(database_engine, monkeypatch):
    user, conversation, _ = scope(database_engine)
    provider = safety_provider()
    factory_calls = []

    def provider_factory(_settings):
        factory_calls.append(1)
        return provider

    monkeypatch.setattr("app.api.dependencies.create_llm_provider", provider_factory)
    app = create_app(config(database_engine))
    with TestClient(app) as client:
        response = client.post(
            PATH.format(conversation_id=conversation),
            json={"message": "有人正在伤害我"},
            headers=headers(user),
        )
    assert response.status_code == 200
    events = parse(response)
    types = [event.event for event in events]
    assert types[0] == "run_started" and types[-1] == "completed"
    assert types.count("final_response") == types.count("completed") == 1
    assert "status" in types
    assert all(event.schema_version == "1" for event in events)
    assert len({event.run_id for event in events}) == 1
    assert not {"analyzing", "planning", "composing"} & {
        event.data.status for event in events if event.event == "status"
    }
    messages, runs = persisted(database_engine, conversation)
    assert [message.role for message in messages] == ["user", "assistant"]
    assert len(runs) == 1 and runs[0].status == "completed"
    assert events[-1].run_id == runs[0].id
    assert next(event for event in events if event.event == "final_response").data.answer == (
        messages[1].content
    )
    assert factory_calls == [1]


def test_foreign_conversation_and_unknown_subject_fail_before_stream(database_engine, monkeypatch):
    owner, conversation, _ = scope(database_engine)
    foreign, _, _ = scope(database_engine)
    app = create_app(config(database_engine))
    monkeypatch.setattr(
        "app.api.dependencies.create_llm_provider", lambda _settings: safety_provider()
    )
    with TestClient(app) as client:
        denied = client.post(
            PATH.format(conversation_id=conversation),
            json={"message": "private attempt"},
            headers=headers(foreign),
        )
        missing = client.post(
            PATH.format(conversation_id=uuid4()),
            json={"message": "private attempt"},
            headers=headers(owner),
        )
        unknown = client.post(
            PATH.format(conversation_id=conversation),
            json={"message": "private attempt"},
            headers=headers(uuid4()),
        )
    assert denied.status_code == missing.status_code == 404
    assert denied.json() == missing.json()
    assert unknown.status_code == 401
    assert "text/event-stream" not in denied.headers["content-type"]
    assert persisted(database_engine, conversation) == ([], [])


def test_runtime_failure_is_typed_failed_and_retains_only_user_message(
    database_engine, monkeypatch
):
    user, conversation, _ = scope(database_engine)
    monkeypatch.setattr(
        "app.api.dependencies.create_llm_provider", lambda _settings: MockLLMProvider()
    )
    with TestClient(create_app(config(database_engine))) as client:
        response = client.post(
            PATH.format(conversation_id=conversation),
            json={"message": "private input"},
            headers=headers(user),
        )
    assert response.status_code == 200
    events = parse(response)
    assert events[0].event == "run_started" and events[-1].event == "failed"
    assert "completed" not in [event.event for event in events]
    assert events[-1].data.code == "agent_failure"
    assert "private input" not in response.text
    messages, runs = persisted(database_engine, conversation)
    assert [item.role for item in messages] == ["user"]
    assert len(runs) == 1 and runs[0].status == "failed"


def test_assistant_persistence_failure_never_emits_final_or_completed(database_engine, monkeypatch):
    user, conversation, _ = scope(database_engine)
    monkeypatch.setattr(
        "app.api.dependencies.create_llm_provider", lambda _settings: safety_provider()
    )
    original = records.create_message

    def fail_assistant(db, user_id, conversation_id, role, content, speaker=None):
        if role == "assistant":
            raise RuntimeError("private DB URL and answer")
        return original(db, user_id, conversation_id, role, content, speaker)

    monkeypatch.setattr(records, "create_message", fail_assistant)
    with TestClient(create_app(config(database_engine))) as client:
        response = client.post(
            PATH.format(conversation_id=conversation),
            json={"message": "有人正在伤害我"},
            headers=headers(user),
        )
    assert response.status_code == 200
    events = parse(response)
    assert events[-1].event == "failed"
    assert events[-1].data.code == "persistence_failure"
    assert "final_response" not in [event.event for event in events]
    assert "completed" not in [event.event for event in events]
    assert "private DB URL" not in response.text
    messages, runs = persisted(database_engine, conversation)
    assert [item.role for item in messages] == ["user"]
    assert runs[0].status == "failed"
    assert events[-1].run_id == runs[0].id


def test_memory_failure_is_completed_with_warning_status(database_engine, monkeypatch):
    user, conversation, person = scope(database_engine, relationship=True)
    provider = CaptureMock()
    queue_run(provider, first=True, person_id=person)
    monkeypatch.setattr("app.api.dependencies.create_llm_provider", lambda _settings: provider)

    def fail_save(self, _record):
        raise RuntimeError("private memory content")

    monkeypatch.setattr(SQLAlchemyMemoryStore, "save_record", fail_save)
    with TestClient(create_app(config(database_engine))) as client:
        response = client.post(
            PATH.format(conversation_id=conversation),
            json={
                "message": "关于对象A：我们已确认关系。我明确同意把这项稳定信息存入长期关系档案。"
            },
            headers=headers(user),
        )
    events = parse(response)
    types = [item.event for item in events]
    assert response.status_code == 200
    assert types.index("final_response") < types.index("memory_status") < types.index("completed")
    assert next(item for item in events if item.event == "memory_status").data.status == "failed"
    assert events[-1].data.memory_status == "failed"
    assert "private memory content" not in response.text
    messages, runs = persisted(database_engine, conversation)
    assert [item.role for item in messages] == ["user", "assistant"]
    assert runs[0].status == "completed"


def test_same_conversation_active_run_gets_409_for_both_transports(database_engine):
    user, conversation, _ = scope(database_engine)
    factory = sessionmaker(bind=database_engine, expire_on_commit=False)
    service = AgentService(
        factory,
        AgentRuntime(dependencies=RuntimeDependencies(llm_provider=safety_provider())),
    )
    actor = actor_from_verified_identity(user)

    async def start():
        return await service.stream(actor=actor, conversation_id=conversation, message="first")

    handle = asyncio.run(start())
    app = create_app(config(database_engine))
    # A separate service instance proves the guard is in PostgreSQL, not a set.
    app.state.agent_service = AgentService(
        factory,
        AgentRuntime(dependencies=RuntimeDependencies(llm_provider=safety_provider())),
    )
    try:
        with TestClient(app) as client:
            for path in (
                PATH.format(conversation_id=conversation),
                f"/api/v1/conversations/{conversation}/agent-runs",
            ):
                response = client.post(path, json={"message": "second"}, headers=headers(user))
                assert response.status_code == 409
                assert response.json()["error"]["code"] == "conversation_busy"
        messages, runs = persisted(database_engine, conversation)
        assert [item.content for item in messages] == ["first"]
        assert len(runs) == 1 and runs[0].status == "running"
    finally:
        handle.cancel_if_running()
    assert persisted(database_engine, conversation)[1][0].failure_code == "client_disconnected"


def test_disconnect_before_first_frame_closes_preflight_run(database_engine):
    user, conversation, _ = scope(database_engine)
    factory = sessionmaker(bind=database_engine)
    service = AgentService(
        factory,
        AgentRuntime(dependencies=RuntimeDependencies(llm_provider=safety_provider())),
    )

    async def abort_at_headers():
        stream = await service.stream(
            actor=actor_from_verified_identity(user),
            conversation_id=conversation,
            message="private input",
        )
        response = ManagedRunStreamingResponse(stream)

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            if message["type"] == "http.response.start":
                raise asyncio.CancelledError

        with pytest.raises(asyncio.CancelledError):
            await response(
                {"type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"}},
                receive,
                send,
            )

    asyncio.run(abort_at_headers())
    messages, runs = persisted(database_engine, conversation)
    assert [item.role for item in messages] == ["user"]
    assert len(runs) == 1 and runs[0].status == "failed"
    assert runs[0].failure_code == "client_disconnected"


def test_two_users_and_two_conversations_are_isolated(database_engine):
    user_a, conversation_a, _ = scope(database_engine)
    user_b, conversation_b, _ = scope(database_engine)
    with sessionmaker(bind=database_engine)() as db, db.begin():
        conversation_c = records.create_conversation(db, user_a).id
    provider = safety_provider(3)
    service = AgentService(
        sessionmaker(bind=database_engine),
        AgentRuntime(dependencies=RuntimeDependencies(llm_provider=provider)),
    )

    async def one(user_id, conversation_id, message):
        stream = await service.stream(
            actor=actor_from_verified_identity(user_id),
            conversation_id=conversation_id,
            message=message,
        )
        return [event async for event in stream.events]

    async def run_all():
        return await asyncio.gather(
            one(user_a, conversation_a, "甲一"),
            one(user_b, conversation_b, "乙"),
            one(user_a, conversation_c, "甲二"),
        )

    batches = asyncio.run(run_all())
    assert len({batch[0].run_id for batch in batches}) == 3
    for batch, conversation, message in zip(
        batches,
        (conversation_a, conversation_b, conversation_c),
        ("甲一", "乙", "甲二"),
        strict=True,
    ):
        assert all(event.run_id == batch[0].run_id for event in batch)
        assert batch[-1].__class__.__name__ == "ServiceCompleted"
        messages, runs = persisted(database_engine, conversation)
        assert [row.role for row in messages] == ["user", "assistant"]
        assert messages[0].content == message and runs[0].id == batch[0].run_id


def test_concurrent_user_memory_streams_keep_owner_and_person_scope(database_engine):
    user_a, conversation_a, person_a = scope(database_engine, relationship=True)
    user_b, conversation_b, person_b = scope(database_engine, relationship=True)
    factory = sessionmaker(bind=database_engine, expire_on_commit=False)
    services = []
    for person in (person_a, person_b):
        provider = CaptureMock()
        queue_run(provider, first=True, person_id=person)
        services.append(
            AgentService(
                factory,
                AgentRuntime(
                    dependencies=RuntimeDependencies(
                        llm_provider=provider,
                        memory_service=MemoryService(SQLAlchemyMemoryStore(factory)),
                    )
                ),
            )
        )

    async def one(service, user_id, conversation_id):
        stream = await service.stream(
            actor=actor_from_verified_identity(user_id),
            conversation_id=conversation_id,
            message="关于对象A：我们已确认关系。我明确同意把这项稳定信息存入长期关系档案。",
        )
        return [event async for event in stream.events]

    async def both():
        return await asyncio.gather(
            one(services[0], user_a, conversation_a),
            one(services[1], user_b, conversation_b),
        )

    batches = asyncio.run(both())
    assert all(batch[-1].__class__.__name__ == "ServiceCompleted" for batch in batches)
    assert {batch[0].run_id for batch in batches} == {
        persisted(database_engine, conversation_a)[1][0].id,
        persisted(database_engine, conversation_b)[1][0].id,
    }
    with factory() as db:
        memory = list(
            db.scalars(
                select(MemoryRecordRow).where(MemoryRecordRow.owner_user_id.in_((user_a, user_b)))
            )
        )
    assert {(record.owner_user_id, record.person_id) for record in memory} == {
        (user_a, person_a),
        (user_b, person_b),
    }


def test_stream_log_does_not_include_token_or_message(database_engine, monkeypatch):
    user, conversation, _ = scope(database_engine)
    monkeypatch.setattr(
        "app.api.dependencies.create_llm_provider", lambda _settings: safety_provider()
    )
    credential = token(user)
    message = "private relation input"
    output = []

    class Capture(logging.Handler):
        def emit(self, record):
            output.append(record.getMessage())

    logger = logging.getLogger(LOGGER_NAME)
    handler = Capture()
    logger.addHandler(handler)
    try:
        with TestClient(create_app(config(database_engine))) as client:
            response = client.post(
                PATH.format(conversation_id=conversation),
                json={"message": message},
                headers={"Authorization": f"Bearer {credential}"},
            )
        assert response.status_code == 200
        assert credential not in "".join(output)
        assert message not in "".join(output)
        assert "Bearer" not in "".join(output)
        final = next(item for item in parse(response) if item.event == "final_response")
        assert final.data.answer not in "".join(output)
    finally:
        logger.removeHandler(handler)
