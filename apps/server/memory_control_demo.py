"""Disposable PostgreSQL + MockLLM demonstration of Phase 6A controls."""

import asyncio
import json
import os
import sys
from contextlib import contextmanager
from uuid import uuid4

from agent_demo import CaptureMock, queue_run
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.agent.dependencies import RuntimeDependencies
from app.agent.memory import MemoryService
from app.agent.runtime import AgentRuntime
from app.db.repositories import records
from app.db.repositories.memory import SQLAlchemyMemoryStore
from app.services.agent_service import AgentService, actor_from_verified_identity
from app.services.memory_control import MemoryControlService


@contextmanager
def disposable_database():
    raw_url = os.environ.get("TEST_DATABASE_URL")
    if not raw_url:
        raise RuntimeError("TEST_DATABASE_URL is required")
    url = make_url(raw_url)
    if url.drivername != "postgresql+psycopg" or not (url.database or "").endswith("_test"):
        raise RuntimeError("A separate psycopg _test database namespace is required")
    name = f"{url.database}_{uuid4().hex[:12]}"
    isolated = url.set(database=name)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    engine = None
    try:
        with admin.connect() as db:
            db.execute(text(f'CREATE DATABASE "{name}"'))
        config = Config("alembic.ini")
        config.attributes["database_url"] = isolated.render_as_string(hide_password=False)
        command.upgrade(config, "head")
        engine = create_engine(isolated, hide_parameters=True)
        yield engine
    finally:
        if engine is not None:
            engine.dispose()
        with admin.connect() as db:
            db.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :name AND pid <> pg_backend_pid()"
                ),
                {"name": name},
            )
            db.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        admin.dispose()


def create_scope(engine):
    with Session(engine) as db:
        user = records.create_user(db)
        person = records.create_person(db, user.id, "Synthetic person")
        relationship = records.create_relationship(db, user.id, person.id, "dating", "active")
        conversation = records.create_conversation(db, user.id, relationship.id)
        ids = user.id, person.id, relationship.id, conversation.id
        db.commit()
        return ids


async def run_agent(engine, user, person, relationship, conversation, store, *, save):
    provider = CaptureMock()
    queue_run(provider, first=save, person_id=person)
    runtime = AgentRuntime(
        dependencies=RuntimeDependencies(llm_provider=provider, memory_service=MemoryService(store))
    )
    result = await AgentService(lambda: Session(engine), runtime).execute(
        actor=actor_from_verified_identity(user),
        conversation_id=conversation,
        relationship_id=relationship,
        person_id=person,
        message=(
            "请记住我们已确认关系，写入长期记忆。" if save else "请根据之前的关系背景分析现状。"
        ),
    )
    recalled = len(provider.analysis_payloads[0]["historical_memory"])
    return result.memory_status.value, recalled


async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    with disposable_database() as engine:
        user, person, relationship, conversation = create_scope(engine)
        store = SQLAlchemyMemoryStore(lambda: Session(engine))
        service = MemoryControlService(store)
        actor = actor_from_verified_identity(user)
        initial = service.inspect_control(actor)
        granted = service.grant_consent(actor)
        saved, _ = await run_agent(
            engine, user, person, relationship, conversation, store, save=True
        )
        inspected = service.inspect_memories(actor)
        paused = service.pause(actor)
        blocked, paused_recall = await run_agent(
            engine, user, person, relationship, conversation, store, save=True
        )
        resumed = service.resume(actor)
        _, resumed_recall = await run_agent(
            engine, user, person, relationship, conversation, store, save=False
        )
        revoked = service.revoke_consent(actor)
        rejected, revoked_recall = await run_agent(
            engine, user, person, relationship, conversation, store, save=True
        )
        if not (
            not initial.consent_enabled
            and granted.effective_write_enabled
            and saved == "saved"
            and len(inspected.items) == 1
            and paused.paused
            and blocked != "saved"
            and paused_recall == 0
            and resumed.effective_read_enabled
            and resumed_recall == 1
            and not revoked.consent_enabled
            and rejected != "saved"
            and revoked_recall == 0
            and len(service.inspect_memories(actor).items) == 1
        ):
            raise RuntimeError("Memory control demonstration failed")
        print(
            json.dumps(
                {
                    "initial_consent": initial.consent_enabled,
                    "grant_effective": granted.effective_write_enabled,
                    "agent_write": saved,
                    "inspect_count": len(inspected.items),
                    "pause_blocks_write_and_recall": blocked != "saved" and paused_recall == 0,
                    "resume_recall_count": resumed_recall,
                    "revoke_blocks_write_and_recall": rejected != "saved" and revoked_recall == 0,
                    "record_retained": len(service.inspect_memories(actor).items) == 1,
                }
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
