"""Offline signed-JWT REST demo over a real local Uvicorn socket and PostgreSQL."""

import json
import os
import socket
import threading
import time
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

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
from app.services.agent_service import AgentService

DEMO_SECRET = "phase4b-offline-demo-secret-with-at-least-32-bytes"


def main() -> None:
    raw_url = os.environ.get("TEST_DATABASE_URL")
    if not raw_url:
        raise RuntimeError("TEST_DATABASE_URL is required")
    url = make_url(raw_url)
    if url.drivername != "postgresql+psycopg" or not (url.database or "").endswith("_test"):
        raise RuntimeError("A separate psycopg _test database namespace is required")
    isolated_name = f"{url.database}_{uuid4().hex[:12]}"
    isolated_url = url.set(database=isolated_name)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    engine = None
    server = None
    server_thread = None
    listen_socket = None
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{isolated_name}"'))
        alembic = Config("alembic.ini")
        alembic.attributes["database_url"] = isolated_url.render_as_string(hide_password=False)
        command.upgrade(alembic, "head")
        engine = create_engine(isolated_url, hide_parameters=True)
        make_session = sessionmaker(bind=engine, expire_on_commit=False)
        with make_session() as db, db.begin():
            user = records.create_user(db)
            conversation = records.create_conversation(db, user.id)
            user_id, conversation_id = user.id, conversation.id

        settings = Settings(
            app_env="test",
            database_url=isolated_url.render_as_string(hide_password=False),
            auth_jwt_secret=DEMO_SECRET,
            auth_jwt_issuer="phase4b-demo",
            auth_jwt_audience="phase4b-api",
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
            "iss": "phase4b-demo",
            "aud": "phase4b-api",
        }
        token = jwt.encode(claims, DEMO_SECRET, algorithm="HS256")
        wrong_token = jwt.encode(
            claims, "different-synthetic-demo-secret-with-32-bytes", algorithm="HS256"
        )
        listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen_socket.bind(("127.0.0.1", 0))
        listen_socket.listen(128)
        port = listen_socket.getsockname()[1]
        server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=port, log_config=None, access_log=False)
        )
        server_thread = threading.Thread(
            target=server.run, kwargs={"sockets": [listen_socket]}, daemon=True
        )
        server_thread.start()
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            if not server_thread.is_alive():
                raise RuntimeError("Uvicorn exited before startup")
            time.sleep(0.05)
        if not server.started:
            raise RuntimeError("Uvicorn did not start")
        endpoint = f"http://127.0.0.1:{port}/api/v1/conversations/{conversation_id}/agent-runs"
        rejected = httpx.post(
            endpoint,
            headers={"Authorization": f"Bearer {wrong_token}"},
            json={"message": "Synthetic rejected request"},
            timeout=10,
        )
        if rejected.status_code != 401:
            raise RuntimeError("An invalid signature was not rejected")
        response = httpx.post(
            endpoint,
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "有人正在伤害我"},
            timeout=10,
        )
        if response.status_code != 200:
            raise RuntimeError(f"Agent REST request failed with HTTP {response.status_code}")
        payload = response.json()
        with make_session() as db:
            messages = list(
                db.scalars(
                    select(Message)
                    .where(Message.conversation_id == conversation_id)
                    .order_by(Message.created_at, Message.id)
                )
            )
            run = db.get(AgentRun, UUID(payload["run_id"]))
            if (
                run is None
                or run.status != "completed"
                or [item.role for item in messages] != ["user", "assistant"]
                or payload["assistant_message"]["content"] != messages[1].content
            ):
                raise RuntimeError("REST result was not persisted")
            print(
                json.dumps(
                    {
                        "http_status": response.status_code,
                        "invalid_signature_status": rejected.status_code,
                        "run_id": payload["run_id"],
                        "verified_subject": str(user_id),
                        "persisted_roles": [item.role for item in messages],
                        "answer_persisted": True,
                    }
                )
            )
    finally:
        if server is not None:
            server.should_exit = True
        if server_thread is not None:
            server_thread.join(timeout=10)
        if listen_socket is not None:
            listen_socket.close()
        if engine is not None:
            engine.dispose()
        with admin.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :database AND pid <> pg_backend_pid()"
                ),
                {"database": isolated_name},
            )
            connection.execute(text(f'DROP DATABASE IF EXISTS "{isolated_name}"'))
        admin.dispose()


if __name__ == "__main__":
    main()
