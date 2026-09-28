"""Phase 4 signed API and PostgreSQL operation-key end-to-end acceptance."""

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
import pytest
from agent_demo import CaptureMock, queue_run
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.agent.dependencies import RuntimeDependencies
from app.agent.runtime import AgentRuntime
from app.core.config import Settings
from app.db.models import AgentRun, MemoryRecordRow, Message
from app.db.repositories import records
from app.db.repositories.memory import SQLAlchemyMemoryStore
from app.llm.mock import MockLLMProvider
from app.main import create_app
from app.schemas.stream_event import NETWORK_EVENT_ADAPTER
from app.services.agent_service import (
    AgentService,
    AgentServiceError,
    AgentServiceErrorCode,
    actor_from_verified_identity,
)

SECRET = "phase4d-synthetic-test-secret-longer-than-32-bytes"
SYNC = "/api/v1/conversations/{conversation_id}/agent-runs"
STREAM = SYNC + "/stream"
MESSAGE = "有人正在伤害我"


def settings(engine: Engine) -> Settings:
    return Settings(
        app_env="test",
        database_url=engine.url.render_as_string(hide_password=False),
        auth_jwt_secret=SECRET,
        auth_jwt_issuer="idempotency-issuer",
        auth_jwt_audience="idempotency-api",
        llm_provider="mock",
        _env_file=None,
    )


def headers(user_id: UUID) -> dict[str, str]:
    token = jwt.encode(
        {
            "sub": str(user_id),
            "exp": datetime.now(UTC) + timedelta(minutes=5),
            "iss": "idempotency-issuer",
            "aud": "idempotency-api",
        },
        SECRET,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def scope(engine: Engine, *, relationship: bool = False):
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db, db.begin():
        user = records.create_user(db)
        person_id = None
        if relationship:
            person = records.create_person(db, user.id, "Synthetic person")
            relation = records.create_relationship(db, user.id, person.id, "dating", "active")
            person_id = person.id
            relation_id = relation.id
        else:
            relation_id = None
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


def events(response):
    assert response.headers["content-type"].startswith("text/event-stream")
    result = []
    for frame in response.content.split(b"\n\n"):
        if frame:
            name, data = frame.decode("utf-8").split("\n")
            event = NETWORK_EVENT_ADAPTER.validate_json(data.removeprefix("data: "))
            assert name == f"event: {event.event}"
            result.append(event)
    return result


class CountingSafety(MockLLMProvider):
    def __init__(self, count: int = 1):
        super().__init__()
        self.calls = 0
        for _ in range(count):
            self.queue_structured(
                {
                    "risk_level": "high",
                    "safety_route_required": True,
                    "risk_categories": ["violence"],
                }
            )

    async def structured_output(self, messages, schema, **kwargs):
        self.calls += 1
        return await super().structured_output(messages, schema, **kwargs)


@pytest.mark.parametrize(
    ("first_transport", "retry_transport"),
    [("sync", "sync"), ("stream", "stream"), ("sync", "stream"), ("stream", "sync")],
)
def test_completed_operation_replays_across_both_transports(
    database_engine, monkeypatch, first_transport, retry_transport
):
    user, conversation, _ = scope(database_engine)
    provider = CountingSafety()
    monkeypatch.setattr("app.api.dependencies.create_llm_provider", lambda _settings: provider)
    body = {"message": MESSAGE, "operation_key": "opaque-key-1"}
    app = create_app(settings(database_engine))
    with TestClient(app) as client:
        first = client.post(
            (SYNC if first_transport == "sync" else STREAM).format(conversation_id=conversation),
            json=body,
            headers=headers(user),
        )
        second = client.post(
            (SYNC if retry_transport == "sync" else STREAM).format(conversation_id=conversation),
            json=body,
            headers=headers(user),
        )
    assert first.status_code == second.status_code == 200
    first_run = (
        first.json()["run_id"] if first_transport == "sync" else str(events(first)[0].run_id)
    )
    if retry_transport == "sync":
        assert second.json()["run_id"] == first_run
        if first_transport == "sync":
            assert second.json() == first.json()
    else:
        replay = events(second)
        assert [item.event for item in replay] == ["final_response", "completed"]
        assert all(item.schema_version == "1" and str(item.run_id) == first_run for item in replay)
    if first_transport == "stream":
        assert events(first)[-1].event == "completed"
    messages, runs = persisted(database_engine, conversation)
    assert provider.calls == 1
    assert [item.role for item in messages] == ["user", "assistant"]
    assert len(runs) == 1 and str(runs[0].id) == first_run
    assert runs[0].user_message_id == messages[0].id
    assert runs[0].assistant_message_id == messages[1].id
    assert runs[0].operation_key == body["operation_key"]
    assert len(runs[0].request_fingerprint) == 64


def test_same_key_different_payload_is_409_with_zero_new_side_effects(database_engine, monkeypatch):
    user, conversation, _ = scope(database_engine)
    provider = CountingSafety()
    monkeypatch.setattr("app.api.dependencies.create_llm_provider", lambda _settings: provider)
    with TestClient(create_app(settings(database_engine))) as client:
        first = client.post(
            SYNC.format(conversation_id=conversation),
            json={"message": MESSAGE, "operation_key": "key-A"},
            headers=headers(user),
        )
        for path in (SYNC, STREAM):
            conflict = client.post(
                path.format(conversation_id=conversation),
                json={"message": "different payload", "operation_key": "key-A"},
                headers=headers(user),
            )
            assert conflict.status_code == 409
            assert conflict.json()["error"]["code"] == "idempotency_conflict"
            assert conflict.json()["error"]["run_id"] == first.json()["run_id"]
        scope_conflict = client.post(
            SYNC.format(conversation_id=conversation),
            json={
                "message": MESSAGE,
                "operation_key": "key-A",
                "expected_relationship_id": str(uuid4()),
            },
            headers=headers(user),
        )
        assert scope_conflict.status_code == 409
        assert scope_conflict.json()["error"]["code"] == "idempotency_conflict"
    messages, runs = persisted(database_engine, conversation)
    assert first.status_code == 200 and provider.calls == 1
    assert len(messages) == 2 and len(runs) == 1


def test_fingerprint_uses_the_same_normalized_message_as_runtime(database_engine, monkeypatch):
    user, conversation, _ = scope(database_engine)
    provider = CountingSafety()
    monkeypatch.setattr("app.api.dependencies.create_llm_provider", lambda _settings: provider)
    with TestClient(create_app(settings(database_engine))) as client:
        first = client.post(
            SYNC.format(conversation_id=conversation),
            json={"message": "  e\u0301  ", "operation_key": "normalize"},
            headers=headers(user),
        )
        retry = client.post(
            SYNC.format(conversation_id=conversation),
            json={"message": "é", "operation_key": "normalize"},
            headers=headers(user),
        )
    assert first.status_code == retry.status_code == 200
    assert first.json() == retry.json() and provider.calls == 1
    messages, runs = persisted(database_engine, conversation)
    assert messages[0].content == "é"
    assert len(runs) == 1


def test_omitted_key_preserves_existing_message_text(database_engine, monkeypatch):
    user, conversation, _ = scope(database_engine)
    provider = CountingSafety()
    monkeypatch.setattr("app.api.dependencies.create_llm_provider", lambda _settings: provider)
    with TestClient(create_app(settings(database_engine))) as client:
        response = client.post(
            SYNC.format(conversation_id=conversation),
            json={"message": "  hello  "},
            headers=headers(user),
        )
    assert response.status_code == 200
    messages, runs = persisted(database_engine, conversation)
    assert messages[0].content == "  hello  "
    assert len(runs) == 1 and runs[0].operation_key is None


def test_key_scope_is_owner_and_conversation(database_engine, monkeypatch):
    user_a, conversation_a, _ = scope(database_engine)
    user_b, conversation_b, _ = scope(database_engine)
    with sessionmaker(bind=database_engine)() as db, db.begin():
        conversation_c = records.create_conversation(db, user_a).id
    provider = CountingSafety(3)
    monkeypatch.setattr("app.api.dependencies.create_llm_provider", lambda _settings: provider)
    with TestClient(create_app(settings(database_engine))) as client:
        responses = [
            client.post(
                SYNC.format(conversation_id=conversation),
                json={"message": MESSAGE, "operation_key": "shared-key"},
                headers=headers(user),
            )
            for user, conversation in (
                (user_a, conversation_a),
                (user_b, conversation_b),
                (user_a, conversation_c),
            )
        ]
        denied = client.post(
            SYNC.format(conversation_id=conversation_a),
            json={"message": MESSAGE, "operation_key": "shared-key"},
            headers=headers(user_b),
        )
    assert all(item.status_code == 200 for item in responses)
    assert len({item.json()["run_id"] for item in responses}) == 3
    assert provider.calls == 3
    assert denied.status_code == 404
    assert denied.json()["error"]["code"] == "not_found"


def test_database_unique_constraint_is_final_arbitrator(database_engine):
    user, conversation, _ = scope(database_engine)
    factory = sessionmaker(bind=database_engine)
    fingerprint = "a" * 64
    with factory() as db, db.begin():
        records.start_agent_run(
            db,
            user,
            conversation,
            uuid4(),
            operation_key="same-key",
            request_fingerprint=fingerprint,
        )
    with pytest.raises(IntegrityError), factory() as db, db.begin():
        records.start_agent_run(
            db,
            user,
            conversation,
            uuid4(),
            operation_key="same-key",
            request_fingerprint=fingerprint,
        )
    assert len(persisted(database_engine, conversation)[1]) == 1


def test_running_and_failed_key_never_reexecute(database_engine):
    user, conversation, _ = scope(database_engine)
    provider = CountingSafety()
    factory = sessionmaker(bind=database_engine)
    service = AgentService(
        factory, AgentRuntime(dependencies=RuntimeDependencies(llm_provider=provider))
    )
    actor = actor_from_verified_identity(user)
    body = dict(
        actor=actor, conversation_id=conversation, message=MESSAGE, operation_key="one-attempt"
    )
    handle = asyncio.run(service.stream(**body))
    with pytest.raises(AgentServiceError) as running:
        asyncio.run(AgentService(factory, service._runtime).execute(**body))
    assert running.value.code == AgentServiceErrorCode.OPERATION_IN_PROGRESS
    assert running.value.run_id == handle.run_id
    app = create_app(settings(database_engine))
    app.state.agent_service = AgentService(factory, service._runtime)
    with TestClient(app) as client:
        reconnect = client.post(
            STREAM.format(conversation_id=conversation),
            json={"message": MESSAGE, "operation_key": "one-attempt"},
            headers=headers(user),
        )
    assert reconnect.status_code == 409
    assert reconnect.json()["error"]["code"] == "operation_in_progress"
    assert reconnect.json()["error"]["run_id"] == str(handle.run_id)
    assert "text/event-stream" not in reconnect.headers["content-type"]
    assert provider.calls == 0
    handle.cancel_if_running()
    with pytest.raises(AgentServiceError) as failed:
        asyncio.run(service.execute(**body))
    assert failed.value.code == AgentServiceErrorCode.OPERATION_FAILED
    assert failed.value.run_id == handle.run_id
    assert provider.calls == 0
    messages, runs = persisted(database_engine, conversation)
    assert [item.role for item in messages] == ["user"]
    assert len(runs) == 1 and runs[0].failure_code == "client_disconnected"


def test_runtime_failure_replay_keeps_category_and_run_id(database_engine, monkeypatch):
    user, conversation, _ = scope(database_engine)
    provider = MockLLMProvider()
    monkeypatch.setattr("app.api.dependencies.create_llm_provider", lambda _settings: provider)
    body = {"message": MESSAGE, "operation_key": "failed-once"}
    with TestClient(create_app(settings(database_engine))) as client:
        first = client.post(
            SYNC.format(conversation_id=conversation), json=body, headers=headers(user)
        )
        retry = client.post(
            SYNC.format(conversation_id=conversation), json=body, headers=headers(user)
        )
    assert first.status_code == retry.status_code == 502
    assert first.json() == retry.json()
    assert first.json()["error"]["code"] == "agent_failure"
    messages, runs = persisted(database_engine, conversation)
    assert [item.role for item in messages] == ["user"]
    assert len(runs) == 1 and runs[0].status == "failed"


def test_unresolved_result_fails_closed(database_engine, monkeypatch):
    user, conversation, _ = scope(database_engine)
    provider = CountingSafety()
    monkeypatch.setattr("app.api.dependencies.create_llm_provider", lambda _settings: provider)
    body = {"message": MESSAGE, "operation_key": "unresolved"}
    app = create_app(settings(database_engine))
    with TestClient(app) as client:
        first = client.post(
            SYNC.format(conversation_id=conversation), json=body, headers=headers(user)
        )
        assert first.status_code == 200
        with sessionmaker(bind=database_engine)() as db, db.begin():
            run = db.get(AgentRun, UUID(first.json()["run_id"]))
            run.memory_status = None
        retry = client.post(
            SYNC.format(conversation_id=conversation), json=body, headers=headers(user)
        )
    assert retry.status_code == 409
    assert retry.json()["error"]["code"] == "operation_unresolved"
    assert retry.json()["error"]["run_id"] == first.json()["run_id"]
    assert provider.calls == 1
    assert len(persisted(database_engine, conversation)[1]) == 1


def test_running_unknown_retry_is_blocked_without_second_execution(database_engine, monkeypatch):
    user, conversation, _ = scope(database_engine)
    provider = CountingSafety()
    monkeypatch.setattr("app.api.dependencies.create_llm_provider", lambda _settings: provider)
    original_create = records.create_message
    original_finish = records.finish_agent_run

    def fail_assistant(db, user_id, conversation_id, role, content, speaker=None):
        if role == "assistant":
            raise RuntimeError("private database failure")
        return original_create(db, user_id, conversation_id, role, content, speaker)

    def fail_recovery(db, user_id, conversation_id, run_id, status, failure_code=None, **kwargs):
        if status == "failed":
            raise RuntimeError("private recovery failure")
        return original_finish(db, user_id, conversation_id, run_id, status, failure_code, **kwargs)

    monkeypatch.setattr(records, "create_message", fail_assistant)
    monkeypatch.setattr(records, "finish_agent_run", fail_recovery)
    body = {"message": MESSAGE, "operation_key": "unknown-commit"}
    with TestClient(create_app(settings(database_engine))) as client:
        first = client.post(
            SYNC.format(conversation_id=conversation), json=body, headers=headers(user)
        )
        retry = client.post(
            SYNC.format(conversation_id=conversation), json=body, headers=headers(user)
        )
    assert first.status_code == 503
    assert first.json()["error"]["recovery_status"] == "running_unknown"
    assert retry.status_code == 409
    assert retry.json()["error"]["code"] == "operation_in_progress"
    assert retry.json()["error"]["run_id"] == first.json()["error"]["run_id"]
    assert provider.calls == 1
    messages, runs = persisted(database_engine, conversation)
    assert [item.role for item in messages] == ["user"]
    assert len(runs) == 1 and runs[0].status == "running"


def test_memory_failure_stays_completed_on_cross_transport_replay(database_engine, monkeypatch):
    user, conversation, person = scope(database_engine, relationship=True)
    provider = CaptureMock()
    queue_run(provider, first=True, person_id=person)
    monkeypatch.setattr("app.api.dependencies.create_llm_provider", lambda _settings: provider)

    def fail_save(self, _record):
        raise RuntimeError("private memory error")

    monkeypatch.setattr(SQLAlchemyMemoryStore, "save_record", fail_save)
    body = {
        "message": "关于对象A：我们已确认关系。我明确同意把这项稳定信息存入长期关系档案。",
        "operation_key": "memory-failure",
    }
    with TestClient(create_app(settings(database_engine))) as client:
        first = client.post(
            STREAM.format(conversation_id=conversation), json=body, headers=headers(user)
        )
        replay = client.post(
            SYNC.format(conversation_id=conversation), json=body, headers=headers(user)
        )
    stream_events = events(first)
    assert [item.event for item in stream_events][-2:] == ["memory_status", "completed"]
    assert stream_events[-1].data.memory_status == "failed"
    assert replay.status_code == 200
    assert replay.json()["run_id"] == str(stream_events[0].run_id)
    assert replay.json()["memory_status"] == "failed"
    assert replay.json()["warnings"]
    assert "private memory error" not in replay.text
    assert len(persisted(database_engine, conversation)[1]) == 1


def test_memory_write_is_not_repeated_by_http_retry(database_engine, monkeypatch):
    user, conversation, person = scope(database_engine, relationship=True)
    provider = CaptureMock()
    queue_run(provider, first=True, person_id=person)
    monkeypatch.setattr("app.api.dependencies.create_llm_provider", lambda _settings: provider)
    body = {
        "message": "关于对象A：我们已确认关系。我明确同意把这项稳定信息存入长期关系档案。",
        "operation_key": "one-memory-write",
    }
    with TestClient(create_app(settings(database_engine))) as client:
        first = client.post(
            SYNC.format(conversation_id=conversation), json=body, headers=headers(user)
        )
        retry = client.post(
            SYNC.format(conversation_id=conversation), json=body, headers=headers(user)
        )
    assert first.status_code == retry.status_code == 200
    assert first.json() == retry.json()
    assert first.json()["memory_status"] == "saved"
    with sessionmaker(bind=database_engine)() as db:
        count = db.scalar(
            select(func.count())
            .select_from(MemoryRecordRow)
            .where(MemoryRecordRow.owner_user_id == user)
        )
    assert count == 1
    assert len(persisted(database_engine, conversation)[1]) == 1


def test_eight_concurrent_duplicates_execute_once_and_other_key_is_busy(database_engine):
    user, conversation, _ = scope(database_engine)
    factory = sessionmaker(bind=database_engine)
    provider = CountingSafety()
    runtime = AgentRuntime(dependencies=RuntimeDependencies(llm_provider=provider))

    class BlockingRuntime:
        def __init__(self):
            self.calls = 0
            self.lock = threading.Lock()
            self.entered = threading.Event()
            self.release = threading.Event()

        async def run(self, request):
            with self.lock:
                self.calls += 1
            self.entered.set()
            await asyncio.to_thread(self.release.wait, 5)
            return await runtime.run(request)

    spy = BlockingRuntime()
    barrier = threading.Barrier(8)
    actor = actor_from_verified_identity(user)

    def worker(_index):
        barrier.wait(timeout=5)
        try:
            return asyncio.run(
                AgentService(factory, spy).execute(
                    actor=actor,
                    conversation_id=conversation,
                    message=MESSAGE,
                    operation_key="race-key",
                )
            )
        except AgentServiceError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(worker, index) for index in range(8)]
        assert spy.entered.wait(5)
        with pytest.raises(AgentServiceError) as different:
            asyncio.run(
                AgentService(factory, spy).execute(
                    actor=actor,
                    conversation_id=conversation,
                    message=MESSAGE,
                    operation_key="different-key",
                )
            )
        assert different.value.code == AgentServiceErrorCode.CONVERSATION_BUSY
        spy.release.set()
        outcomes = [future.result(timeout=10) for future in futures]
    assert spy.calls == provider.calls == 1
    results = [item for item in outcomes if not isinstance(item, AgentServiceError)]
    assert results
    assert all(item.run_id == results[0].run_id for item in results)
    assert all(
        item.code == AgentServiceErrorCode.OPERATION_IN_PROGRESS
        for item in outcomes
        if isinstance(item, AgentServiceError)
    )
    messages, runs = persisted(database_engine, conversation)
    assert [item.role for item in messages] == ["user", "assistant"]
    assert len(runs) == 1 and runs[0].id == results[0].run_id


def test_operation_key_validation_and_openapi(database_engine, monkeypatch):
    user, conversation, _ = scope(database_engine)
    provider = CountingSafety()
    monkeypatch.setattr("app.api.dependencies.create_llm_provider", lambda _settings: provider)
    with TestClient(create_app(settings(database_engine))) as client:
        for key in ("space key", "line\nkey", "bad\x00key", "x" * 129):
            response = client.post(
                SYNC.format(conversation_id=conversation),
                json={"message": MESSAGE, "operation_key": key},
                headers=headers(user),
            )
            assert response.status_code == 422
        schema = client.get("/openapi.json").json()
        valid = client.post(
            SYNC.format(conversation_id=conversation),
            json={"message": MESSAGE, "operation_key": "随机-🔑"},
            headers=headers(user),
        )
    request = schema["components"]["schemas"]["CreateAgentRunRequest"]["properties"][
        "operation_key"
    ]
    assert "client-generated" in request["description"]
    assert "retry" in request["description"]
    assert valid.status_code == 200 and provider.calls == 1
