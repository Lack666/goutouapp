"""Disposable real HTTP/PostgreSQL fixture; credentials travel only over a private pipe.

Invoked by Playwright, never emits credentials into test reporters or files.
The development CLI is the actual issuer. No authentication override. The optional
8C mode composes a deterministic keyless MockLLM behind the unchanged runtime.
"""

import asyncio
import json
import os
import socket
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime, timedelta

import jwt
import uvicorn
from memory_control_demo import disposable_database
from resource_demo_support import create_owners
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent.dependencies import RuntimeDependencies
from app.agent.memory import MemoryService
from app.agent.runtime import AgentRuntime
from app.core.config import Settings
from app.db.models import AgentRun, Conversation, MemoryRecordRow, Message, Person, Relationship
from app.db.repositories.memory import SQLAlchemyMemoryStore
from app.llm.mock import MockLLMProvider
from app.main import create_app
from app.services.agent_service import AgentService


class ChatDemoMock(MockLLMProvider):
    """Only synthetic violence prompts are used by this disposable test fixture."""

    def __init__(self):
        super().__init__()
        self.calls = 0
        for _ in range(100):
            self.queue_structured(
                {
                    "risk_level": "high",
                    "safety_route_required": True,
                    "risk_categories": ["violence"],
                }
            )

    async def structured_output(self, messages, schema, **kwargs):
        self.calls += 1
        await asyncio.sleep(0.1)
        return await super().structured_output(messages, schema, **kwargs)


def main():
    with disposable_database() as engine:
        agent_mode = os.environ.get("GOUTOU_AGENT_E2E") == "1"
        port = 8019 if agent_mode else 8018
        owner, other = create_owners(engine)
        secret = os.urandom(48).hex()
        settings = Settings(
            _env_file=None,
            app_env="development",
            database_url=engine.url.render_as_string(hide_password=False),
            auth_jwt_secret=secret,
            dev_cors_origins=["http://localhost:8089" if agent_mode else "http://localhost:8088"],
        )
        env = {
            **os.environ,
            "APP_ENV": "development",
            "DATABASE_URL": engine.url.render_as_string(hide_password=False),
            "AUTH_JWT_SECRET": secret,
            "AUTH_JWT_ISSUER": settings.auth_jwt_issuer,
            "AUTH_JWT_AUDIENCE": settings.auth_jwt_audience,
        }
        tokens = [
            subprocess.check_output(
                [sys.executable, "apps/server/dev_auth_cli.py", "token", "--user-id", str(user)],
                env=env,
                text=True,
            ).strip()
            for user in (owner, other)
        ]
        expired = jwt.encode(
            {
                "sub": str(owner),
                "exp": datetime.now(UTC) - timedelta(seconds=1),
                "iss": settings.auth_jwt_issuer,
                "aud": settings.auth_jwt_audience,
            },
            secret,
            algorithm="HS256",
        )
        app = create_app(settings)
        provider = ChatDemoMock() if agent_mode else None
        if provider:
            app.state.agent_service = AgentService(
                app.state.database.session,
                AgentRuntime(
                    dependencies=RuntimeDependencies(
                        llm_provider=provider,
                        memory_service=MemoryService(
                            SQLAlchemyMemoryStore(app.state.database.session)
                        ),
                    )
                ),
            )
        listen = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen.bind(("127.0.0.1", port))
        listen.listen(128)
        server = uvicorn.Server(uvicorn.Config(app, log_config=None, access_log=False))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listen]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started and time.monotonic() < deadline:
                if not thread.is_alive():
                    raise RuntimeError("Fixture server did not start")
                time.sleep(0.05)
            if not server.started:
                raise RuntimeError("Fixture startup timed out")
            # The caller captures this line; it must never be echoed or persisted.
            print(
                json.dumps(
                    {
                        "baseURL": f"http://127.0.0.1:{port}",
                        "a": tokens[0],
                        "b": tokens[1],
                        "expired": expired,
                    }
                ),
                flush=True,
            )
            for command in sys.stdin:
                if command.strip() == "stop":
                    break
                if command.strip() == "counts":
                    with Session(engine) as db:
                        counts = {
                            model.__tablename__: db.scalar(
                                select(func.count())
                                .select_from(model)
                                .where(model.user_id == owner)
                            )
                            for model in (Person, Relationship, Conversation)
                        }
                        print(json.dumps(counts), flush=True)
                if command.strip() == "agent_evidence":
                    with Session(engine) as db:
                        runs = list(db.scalars(select(AgentRun).order_by(AgentRun.id)))
                        messages = list(
                            db.scalars(select(Message).order_by(Message.created_at, Message.id))
                        )
                        print(
                            json.dumps(
                                {
                                    "calls": provider.calls if provider else 0,
                                    "runs": [
                                        {
                                            "id": str(row.id),
                                            "owner": str(row.user_id),
                                            "conversation": str(row.conversation_id),
                                            "status": row.status,
                                            "key": row.operation_key,
                                        }
                                        for row in runs
                                    ],
                                    "messages": [
                                        {
                                            "id": str(row.id),
                                            "conversation": str(row.conversation_id),
                                            "role": row.role,
                                        }
                                        for row in messages
                                    ],
                                    "memories": db.scalar(
                                        select(func.count()).select_from(MemoryRecordRow)
                                    ),
                                }
                            ),
                            flush=True,
                        )
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            listen.close()
            if thread.is_alive():
                raise RuntimeError("Fixture did not stop")


if __name__ == "__main__":
    main()
