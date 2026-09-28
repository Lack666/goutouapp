"""A real Uvicorn socket proves disconnect cancellation and terminal DB state."""

import asyncio
import socket
import threading
import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import httpx
import jwt
import uvicorn
from agent_demo import CaptureMock, queue_run
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.models import AgentRun, MemoryRecordRow, Message
from app.db.repositories import records
from app.llm.mock import MockLLMProvider
from app.main import create_app

SECRET = "phase4c-disconnect-synthetic-secret-more-than-32-bytes"
MEMORY_MESSAGE = "关于对象A：我们已确认关系。我明确同意把这项稳定信息存入长期关系档案。"


def context(engine: Engine, *, relationship=False):
    with sessionmaker(bind=engine, expire_on_commit=False)() as db, db.begin():
        user = records.create_user(db)
        relation_id = person_id = None
        if relationship:
            person = records.create_person(db, user.id, "Synthetic person")
            relation = records.create_relationship(db, user.id, person.id, "dating", "active")
            relation_id, person_id = relation.id, person.id
        conversation = records.create_conversation(db, user.id, relation_id)
        return user.id, conversation.id, person_id


def token(user_id):
    return jwt.encode(
        {
            "sub": str(user_id),
            "exp": datetime.now(UTC) + timedelta(minutes=5),
            "iss": "disconnect-issuer",
            "aud": "disconnect-api",
        },
        SECRET,
        algorithm="HS256",
    )


@contextmanager
def server(engine: Engine, monkeypatch, provider):
    monkeypatch.setattr("app.api.dependencies.create_llm_provider", lambda _settings: provider)
    app = create_app(
        Settings(
            app_env="test",
            database_url=engine.url.render_as_string(hide_password=False),
            auth_jwt_secret=SECRET,
            auth_jwt_issuer="disconnect-issuer",
            auth_jwt_audience="disconnect-api",
            llm_provider="mock",
            _env_file=None,
        )
    )
    listen = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen.bind(("127.0.0.1", 0))
    listen.listen(128)
    port = listen.getsockname()[1]
    instance = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_config=None, access_log=False)
    )
    thread = threading.Thread(target=instance.run, kwargs={"sockets": [listen]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not instance.started and time.monotonic() < deadline:
            assert thread.is_alive(), "Uvicorn exited before startup"
            time.sleep(0.02)
        assert instance.started
        yield f"http://127.0.0.1:{port}"
    finally:
        instance.should_exit = True
        thread.join(timeout=10)
        listen.close()


def wait_for(predicate, seconds=5):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.03)
    return False


def state(engine: Engine, conversation_id):
    with sessionmaker(bind=engine)() as db:
        run = db.scalar(select(AgentRun).where(AgentRun.conversation_id == conversation_id))
        messages = list(
            db.scalars(select(Message).where(Message.conversation_id == conversation_id))
        )
        memories = (
            db.scalar(
                select(func.count())
                .select_from(MemoryRecordRow)
                .where(MemoryRecordRow.owner_user_id == run.user_id)
            )
            if run is not None
            else 0
        )
        return run, messages, memories


class BlockingSafety(MockLLMProvider):
    def __init__(self):
        super().__init__()
        self.entered = threading.Event()
        self.cancelled = threading.Event()

    async def structured_output(self, messages, schema, **kwargs):
        self.entered.set()
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            self.cancelled.set()
            raise


class BlockingMemory(CaptureMock):
    def __init__(self):
        super().__init__()
        self.entered = threading.Event()
        self.cancelled = threading.Event()

    async def structured_output(self, messages, schema, **kwargs):
        if schema.__name__ == "MemoryCandidateBatch":
            self.entered.set()
            try:
                await asyncio.Future()
            except asyncio.CancelledError:
                self.cancelled.set()
                raise
        return await super().structured_output(messages, schema, **kwargs)


def close_after_event(
    base_url, conversation_id, user_id, message, event_name, entered, operation_key=None
):
    url = f"{base_url}/api/v1/conversations/{conversation_id}/agent-runs/stream"
    with httpx.Client(timeout=10) as client:
        with client.stream(
            "POST",
            url,
            json={"message": message, "operation_key": operation_key},
            headers={"Authorization": f"Bearer {token(user_id)}"},
        ) as response:
            assert response.status_code == 200
            observed = []
            for line in response.iter_lines():
                if line.startswith("event: "):
                    observed.append(line[7:])
                if line == f"event: {event_name}":
                    assert entered.wait(5), "Runtime did not reach the blocked operation"
                    break
            assert event_name in observed
    return observed


def test_disconnect_before_final_cancels_runtime_and_fails_run(database_engine, monkeypatch):
    user, conversation, _ = context(database_engine)
    provider = BlockingSafety()
    with server(database_engine, monkeypatch, provider) as base_url:
        observed = close_after_event(
            base_url, conversation, user, "private input", "status", provider.entered
        )
        assert "final_response" not in observed
        assert provider.cancelled.wait(5)
        assert wait_for(
            lambda: (
                (run := state(database_engine, conversation)[0]) is not None
                and run.status == "failed"
            )
        )
    run, messages, memories = state(database_engine, conversation)
    assert run.failure_code == "client_disconnected"
    assert [message.role for message in messages] == ["user"]
    assert memories == 0


def test_disconnect_after_final_keeps_committed_run_and_cancels_memory(
    database_engine, monkeypatch
):
    user, conversation, person = context(database_engine, relationship=True)
    provider = BlockingMemory()
    queue_run(provider, first=True, person_id=person)
    with server(database_engine, monkeypatch, provider) as base_url:
        observed = close_after_event(
            base_url,
            conversation,
            user,
            "关于对象A：我们已确认关系。我明确同意把这项稳定信息存入长期关系档案。",
            "final_response",
            provider.entered,
            operation_key="after-final-key",
        )
        assert "completed" not in observed
        assert provider.cancelled.wait(5)
        with httpx.Client(timeout=10) as client:
            replay = client.post(
                f"{base_url}/api/v1/conversations/{conversation}/agent-runs/stream",
                json={
                    "message": MEMORY_MESSAGE,
                    "operation_key": "after-final-key",
                },
                headers={"Authorization": f"Bearer {token(user)}"},
            )
        assert replay.status_code == 200
        assert [
            line.removeprefix("event: ")
            for line in replay.text.splitlines()
            if line.startswith("event: ")
        ] == ["final_response", "completed"]
    run, messages, memories = state(database_engine, conversation)
    assert run.status == "completed" and run.failure_code is None
    assert [message.role for message in messages] == ["user", "assistant"]
    assert memories == 0
    assert str(run.id) in replay.text


def test_keyed_precommit_disconnect_replays_failure_without_new_run(database_engine, monkeypatch):
    user, conversation, _ = context(database_engine)
    provider = BlockingSafety()
    with server(database_engine, monkeypatch, provider) as base_url:
        close_after_event(
            base_url,
            conversation,
            user,
            "private input",
            "status",
            provider.entered,
            operation_key="before-final-key",
        )
        assert provider.cancelled.wait(5)
        assert wait_for(
            lambda: (
                (run := state(database_engine, conversation)[0]) is not None
                and run.status == "failed"
            )
        )
        with httpx.Client(timeout=10) as client:
            retry = client.post(
                f"{base_url}/api/v1/conversations/{conversation}/agent-runs",
                json={"message": "private input", "operation_key": "before-final-key"},
                headers={"Authorization": f"Bearer {token(user)}"},
            )
        assert retry.status_code == 409
        assert retry.json()["error"]["code"] == "operation_failed"
    run, messages, memories = state(database_engine, conversation)
    assert retry.json()["error"]["run_id"] == str(run.id)
    assert [message.role for message in messages] == ["user"]
    assert memories == 0
