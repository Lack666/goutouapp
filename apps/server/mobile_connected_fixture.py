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
from tempfile import TemporaryDirectory
from uuid import UUID

import jwt
import uvicorn
from memory_control_demo import disposable_database
from memory_phase6_support import Phase6Mock
from resource_demo_support import create_owners
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent.dependencies import RuntimeDependencies
from app.agent.memory import MemoryService
from app.agent.runtime import AgentRuntime
from app.core.config import Settings
from app.db.models import (
    AgentRun,
    ChatImportArtifact,
    ChatImportJob,
    Conversation,
    MemoryConfirmationRow,
    MemoryControlRow,
    MemoryMutationRow,
    MemoryRecordRow,
    Message,
    Person,
    Relationship,
    RelationshipMessage,
)
from app.db.repositories.memory import SQLAlchemyMemoryStore
from app.llm.mock import MockLLMProvider
from app.main import create_app
from app.retention import RetentionPolicy
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
    with (
        disposable_database() as engine,
        TemporaryDirectory(prefix="goutou-mobile-artifacts-") as artifacts,
    ):
        final_mode = os.environ.get("GOUTOU_FINAL_E2E") == "1"
        native_mode = os.environ.get("GOUTOU_NATIVE_ACCEPTANCE") == "1"
        agent_mode = os.environ.get("GOUTOU_AGENT_E2E") == "1"
        import_mode = final_mode or os.environ.get("GOUTOU_IMPORT_E2E") == "1"
        memory_mode = final_mode or os.environ.get("GOUTOU_MEMORY_E2E") == "1"
        port = (
            8023
            if final_mode
            else int(os.environ.get("GOUTOU_MEMORY_PORT", "8022"))
            if memory_mode
            else int(os.environ.get("GOUTOU_IMPORT_PORT", "8020"))
            if import_mode
            else 8019
            if agent_mode
            else 8018
        )
        owner, other = create_owners(engine)
        secret = os.urandom(48).hex()
        settings = Settings(
            _env_file=None,
            app_env="development",
            database_url=engine.url.render_as_string(hide_password=False),
            auth_jwt_secret=secret,
            dev_cors_origins=[
                "http://localhost:8094"
                if final_mode
                else "http://localhost:8091"
                if memory_mode
                else "http://localhost:8090"
                if import_mode
                else "http://localhost:8089"
                if agent_mode
                else "http://localhost:8088"
            ],
            chat_import_artifact_root=artifacts,
            memory_retention_days=37 if memory_mode else 180,
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
        provider = Phase6Mock() if memory_mode else ChatDemoMock() if agent_mode else None
        if native_mode:
            from native_acceptance_support import NativeAcceptanceMock, NativeAcceptanceWire

            provider = NativeAcceptanceMock()
        if provider:
            app.state.agent_service = AgentService(
                app.state.database.session,
                AgentRuntime(
                    dependencies=RuntimeDependencies(
                        llm_provider=provider,
                        memory_service=MemoryService(
                            SQLAlchemyMemoryStore(
                                app.state.database.session,
                                policy=RetentionPolicy.from_settings(settings),
                            )
                        ),
                    )
                ),
            )
        listen = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen.bind(("127.0.0.1", port))
        listen.listen(128)
        wire = (
            NativeAcceptanceWire(app, {str(owner): "a", str(other): "b"}) if native_mode else None
        )
        server = uvicorn.Server(uvicorn.Config(wire or app, log_config=None, access_log=False))
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
                if native_mode and command.startswith("fault "):
                    fault = command.strip().split()[1]
                    if fault == "provider_failed":
                        provider.fail_next = True
                    elif fault == "slow_run":
                        provider.delay = 5
                    elif fault == "normal_run":
                        provider.delay = 0.8
                    elif fault == "hold_final":
                        provider.response_release.clear()
                    elif fault == "release_final":
                        provider.response_release.set()
                    elif fault == "hold_memory":
                        wire.hold("/api/v1/memories")
                    elif fault == "hold_history":
                        wire.hold("/messages")
                    elif fault == "release_get":
                        wire.release.set()
                    else:
                        wire.arm(fault)
                    print(json.dumps({"armed": fault}), flush=True)
                if native_mode and command.strip() == "wire_evidence":
                    print(json.dumps(wire.evidence()), flush=True)
                if native_mode and command.startswith("stale_memory "):
                    with Session(engine) as db, db.begin():
                        row = db.get(MemoryRecordRow, UUID(command.strip().split()[1]))
                        if row is None:
                            raise ValueError("Synthetic stale target not found")
                        row.updated_at = datetime.now(UTC) + timedelta(seconds=1)
                    print(json.dumps({"stale": True}), flush=True)
                if command.strip() in {"renew_token a", "renew_token b"}:
                    user = owner if command.strip().endswith(" a") else other
                    # This response is private pipe data, never reporter output.
                    renewed = subprocess.check_output(
                        [
                            sys.executable,
                            "apps/server/dev_auth_cli.py",
                            "token",
                            "--user-id",
                            str(user),
                        ],
                        env=env,
                        text=True,
                    ).strip()
                    print(json.dumps({"credential": renewed}), flush=True)
                if memory_mode and command.startswith(("expire_memory ", "expire_confirmation ")):
                    kind, identifier = command.strip().split()
                    model = MemoryRecordRow if kind == "expire_memory" else MemoryConfirmationRow
                    with Session(engine) as db, db.begin():
                        row = db.get(model, UUID(identifier))
                        if row is None:
                            raise ValueError("Synthetic expiry target not found")
                        row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
                    print(json.dumps({"expired": True}), flush=True)
                if memory_mode and command.strip() == "memory_evidence":
                    with Session(engine) as db:
                        print(
                            json.dumps(
                                {
                                    "memories": db.scalar(
                                        select(func.count()).select_from(MemoryRecordRow)
                                    ),
                                    "receipts": db.scalar(
                                        select(func.count()).select_from(MemoryMutationRow)
                                    ),
                                    "records": [
                                        {
                                            "id": str(row.id),
                                            "owner": str(row.owner_user_id),
                                            "person": str(row.person_id),
                                            "relationship": str(row.relationship_id),
                                        }
                                        for row in db.scalars(
                                            select(MemoryRecordRow).order_by(MemoryRecordRow.id)
                                        )
                                    ],
                                    "mutations": [
                                        {
                                            "id": str(row.id),
                                            "owner": str(row.owner_user_id),
                                            "key": row.operation_key,
                                            "action": row.action,
                                            "status": row.status,
                                            "affected": row.affected_count,
                                            "target": str(row.target_id),
                                        }
                                        for row in db.scalars(
                                            select(MemoryMutationRow).order_by(
                                                MemoryMutationRow.performed_at
                                            )
                                        )
                                    ],
                                    "agent_messages": db.scalar(
                                        select(func.count()).select_from(Message)
                                    ),
                                    "relationship_messages": db.scalar(
                                        select(func.count()).select_from(RelationshipMessage)
                                    ),
                                    "recall_counts": [
                                        len(value.get("historical_memory", []))
                                        for value in provider.analysis_payloads
                                    ],
                                    "calls": len(provider.calls),
                                    "controls": [
                                        {
                                            "owner": str(row.user_id),
                                            "consent_enabled": row.consent_enabled,
                                            "paused": row.paused,
                                        }
                                        for row in db.scalars(select(MemoryControlRow))
                                    ],
                                }
                            ),
                            flush=True,
                        )
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
                if command.strip() == "import_evidence":
                    with Session(engine) as db:
                        print(
                            json.dumps(
                                {
                                    "jobs": [
                                        {
                                            "id": str(row.id),
                                            "status": row.status,
                                            "revision": row.binding_revision,
                                        }
                                        for row in db.scalars(select(ChatImportJob))
                                    ],
                                    "messages": db.scalar(
                                        select(func.count()).select_from(RelationshipMessage)
                                    ),
                                    "agent_messages": db.scalar(
                                        select(func.count()).select_from(Message)
                                    ),
                                    "memories": db.scalar(
                                        select(func.count()).select_from(MemoryRecordRow)
                                    ),
                                    "active_artifacts": db.scalar(
                                        select(func.count())
                                        .select_from(ChatImportArtifact)
                                        .where(ChatImportArtifact.state == "active")
                                    ),
                                }
                            ),
                            flush=True,
                        )
        finally:
            if wire:
                wire.release.set()
                provider.response_release.set()
            server.should_exit = True
            thread.join(timeout=10)
            listen.close()
            if thread.is_alive():
                raise RuntimeError("Fixture did not stop")


if __name__ == "__main__":
    main()
