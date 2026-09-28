"""Offline signed-JWT SSE demo over a real Uvicorn socket and PostgreSQL."""

import json
import os
import socket
import threading
import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import jwt
import uvicorn
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.agent.dependencies import RuntimeDependencies
from app.agent.memory import MemoryService
from app.agent.runtime import AgentRuntime
from app.core.config import Settings
from app.db.models import AgentRun, Message
from app.db.repositories import records
from app.db.repositories.memory import SQLAlchemyMemoryStore
from app.llm.mock import MockLLMProvider
from app.main import create_app
from app.schemas.stream_event import NETWORK_EVENT_ADAPTER
from app.services.agent_service import AgentService

DEMO_SECRET = "phase4c-offline-stream-demo-secret-over-32-bytes"


def main() -> None:
    raw_url = os.environ.get("TEST_DATABASE_URL")
    if not raw_url:
        raise RuntimeError("TEST_DATABASE_URL is required")
    url = make_url(raw_url)
    if url.drivername != "postgresql+psycopg" or not (url.database or "").endswith("_test"):
        raise RuntimeError("A separate psycopg _test database namespace is required")
    name = f"{url.database}_{uuid4().hex[:12]}"
    isolated_url = url.set(database=name)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    engine = None
    server = None
    thread = None
    listen = None
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
        alembic = Config("alembic.ini")
        alembic.attributes["database_url"] = isolated_url.render_as_string(hide_password=False)
        command.upgrade(alembic, "head")
        engine = create_engine(isolated_url, hide_parameters=True)
        factory = sessionmaker(bind=engine, expire_on_commit=False)
        with factory() as db, db.begin():
            user = records.create_user(db)
            conversation = records.create_conversation(db, user.id)
            user_id, conversation_id = user.id, conversation.id

        settings = Settings(
            app_env="test",
            database_url=isolated_url.render_as_string(hide_password=False),
            auth_jwt_secret=DEMO_SECRET,
            auth_jwt_issuer="phase4c-demo",
            auth_jwt_audience="phase4c-api",
            llm_provider="mock",
            _env_file=None,
        )
        app = create_app(settings)
        provider = MockLLMProvider()
        provider.queue_structured(
            {"risk_level": "high", "safety_route_required": True, "risk_categories": ["violence"]}
        )
        database = app.state.database
        app.state.agent_service = AgentService(
            database.session,
            AgentRuntime(
                dependencies=RuntimeDependencies(
                    llm_provider=provider,
                    memory_service=MemoryService(SQLAlchemyMemoryStore(database.session)),
                )
            ),
        )
        claims = {
            "sub": str(user_id),
            "exp": datetime.now(UTC) + timedelta(minutes=5),
            "iss": "phase4c-demo",
            "aud": "phase4c-api",
        }
        token = jwt.encode(claims, DEMO_SECRET, algorithm="HS256")
        listen = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen.bind(("127.0.0.1", 0))
        listen.listen(128)
        port = listen.getsockname()[1]
        server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=port, log_config=None, access_log=False)
        )
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listen]}, daemon=True)
        thread.start()
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            if not thread.is_alive():
                raise RuntimeError("Uvicorn exited before startup")
            time.sleep(0.05)
        if not server.started:
            raise RuntimeError("Uvicorn did not start")

        endpoint = (
            f"http://127.0.0.1:{port}/api/v1/conversations/{conversation_id}/agent-runs/stream"
        )
        sync_endpoint = endpoint.removesuffix("/stream")
        request_body = {"message": "有人正在伤害我", "operation_key": "phase4-demo-stream"}
        names = []
        observed_run = None
        with httpx.Client(timeout=10) as client:
            with client.stream(
                "POST",
                endpoint,
                json=request_body,
                headers={"Authorization": f"Bearer {token}"},
            ) as response:
                if response.status_code != 200:
                    raise RuntimeError(f"Stream failed with HTTP {response.status_code}")
                pending_name = None
                for line in response.iter_lines():
                    if line.startswith("event: "):
                        pending_name = line[7:]
                    elif line.startswith("data: "):
                        event = NETWORK_EVENT_ADAPTER.validate_json(line[6:])
                        if event.event != pending_name:
                            raise RuntimeError("Invalid SSE event framing")
                        if observed_run is None:
                            observed_run = event.run_id
                        if event.run_id != observed_run:
                            raise RuntimeError("Run ID changed mid-stream")
                        names.append(event.event)
                        print(f"received_event={event.event}", flush=True)
                        if event.event == "completed":
                            # Query immediately while the network response is open.
                            with factory() as db:
                                messages = list(
                                    db.scalars(
                                        select(Message)
                                        .where(Message.conversation_id == conversation_id)
                                        .order_by(Message.created_at, Message.id)
                                    )
                                )
                                run = db.get(AgentRun, observed_run)
                                if (
                                    run is None
                                    or run.status != "completed"
                                    or [item.role for item in messages] != ["user", "assistant"]
                                ):
                                    raise RuntimeError("Completed event preceded persistence")
        if not (
            names[0] == "run_started"
            and "status" in names
            and names[-2:] == ["final_response", "completed"]
        ):
            raise RuntimeError("Unexpected network event order")
        with httpx.Client(timeout=10) as client:
            stream_to_sync = client.post(
                sync_endpoint,
                json=request_body,
                headers={"Authorization": f"Bearer {token}"},
            )
            if stream_to_sync.status_code != 200 or stream_to_sync.json()["run_id"] != str(
                observed_run
            ):
                raise RuntimeError("Stream-to-sync replay did not reuse the run")
            replay_names = []
            with client.stream(
                "POST",
                endpoint,
                json=request_body,
                headers={"Authorization": f"Bearer {token}"},
            ) as replay:
                if replay.status_code != 200:
                    raise RuntimeError("Stream replay failed")
                for line in replay.iter_lines():
                    if line.startswith("data: "):
                        event = NETWORK_EVENT_ADAPTER.validate_json(line[6:])
                        if event.run_id != observed_run:
                            raise RuntimeError("Stream replay changed run ID")
                        replay_names.append(event.event)
                        print(f"replay_event={event.event}", flush=True)
            if replay_names != ["final_response", "completed"]:
                raise RuntimeError("Stream replay invented progress or missed completion")

            with factory() as db, db.begin():
                sync_conversation_id = records.create_conversation(db, user_id).id
            provider.queue_structured(
                {
                    "risk_level": "high",
                    "safety_route_required": True,
                    "risk_categories": ["violence"],
                }
            )
            sync_url = (
                f"http://127.0.0.1:{port}/api/v1/conversations/{sync_conversation_id}/agent-runs"
            )
            sync_body = {"message": "有人正在伤害我", "operation_key": "phase4-demo-sync"}
            sync_first = client.post(
                sync_url, json=sync_body, headers={"Authorization": f"Bearer {token}"}
            )
            sync_retry = client.post(
                sync_url, json=sync_body, headers={"Authorization": f"Bearer {token}"}
            )
            if sync_first.status_code != 200 or sync_first.json() != sync_retry.json():
                raise RuntimeError("Sync retry did not return the persisted response")
            sync_to_stream_names = []
            with client.stream(
                "POST",
                sync_url + "/stream",
                json=sync_body,
                headers={"Authorization": f"Bearer {token}"},
            ) as replay:
                if replay.status_code != 200:
                    raise RuntimeError("Sync-to-stream replay failed")
                for line in replay.iter_lines():
                    if line.startswith("data: "):
                        event = NETWORK_EVENT_ADAPTER.validate_json(line[6:])
                        if str(event.run_id) != sync_first.json()["run_id"]:
                            raise RuntimeError("Sync-to-stream replay changed run ID")
                        sync_to_stream_names.append(event.event)
            if sync_to_stream_names != ["final_response", "completed"]:
                raise RuntimeError("Sync-to-stream replay did not use persisted facts")

        with factory() as db:
            original_runs = list(
                db.scalars(select(AgentRun).where(AgentRun.conversation_id == conversation_id))
            )
            sync_runs = list(
                db.scalars(select(AgentRun).where(AgentRun.conversation_id == sync_conversation_id))
            )
            sync_messages = list(
                db.scalars(select(Message).where(Message.conversation_id == sync_conversation_id))
            )
        if len(original_runs) != 1 or len(sync_runs) != 1 or len(sync_messages) != 2:
            raise RuntimeError("A retry created duplicate database side effects")
        print(
            json.dumps(
                {
                    "http_status": 200,
                    "run_id": str(observed_run),
                    "event_types": names,
                    "completed_was_persisted_when_received": True,
                    "stream_replay_events": replay_names,
                    "sync_retry_same_response": True,
                    "sync_to_stream_replay_events": sync_to_stream_names,
                    "one_run_per_operation": True,
                }
            )
        )
    finally:
        if server is not None:
            server.should_exit = True
        if thread is not None:
            thread.join(timeout=10)
        if listen is not None:
            listen.close()
        if engine is not None:
            engine.dispose()
        with admin.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :database AND pid <> pg_backend_pid()"
                ),
                {"database": name},
            )
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        admin.dispose()


if __name__ == "__main__":
    main()
