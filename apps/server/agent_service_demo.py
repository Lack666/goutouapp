"""Phase 4A keyless AgentService demo in a disposable PostgreSQL database."""

import asyncio
import json
import os
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.agent.dependencies import RuntimeDependencies
from app.agent.runtime import AgentRuntime
from app.db.models import AgentRun, Message
from app.db.repositories import records
from app.llm.mock import MockLLMProvider
from app.services.agent_service import AgentService, actor_from_verified_identity


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
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{isolated_name}"'))
        config = Config("alembic.ini")
        config.attributes["database_url"] = isolated_url.render_as_string(hide_password=False)
        command.upgrade(config, "head")
        engine = create_engine(isolated_url, hide_parameters=True)
        make_session = sessionmaker(bind=engine, expire_on_commit=False)
        with make_session() as db, db.begin():
            user = records.create_user(db)
            conversation = records.create_conversation(db, user.id)
            user_id, conversation_id = user.id, conversation.id
        provider = MockLLMProvider()
        provider.queue_structured(
            {"risk_level": "high", "safety_route_required": True, "risk_categories": ["violence"]}
        )
        service = AgentService(
            make_session, AgentRuntime(dependencies=RuntimeDependencies(llm_provider=provider))
        )
        result = asyncio.run(
            service.execute(
                actor=actor_from_verified_identity(user_id),
                conversation_id=conversation_id,
                message="有人正在伤害我",
            )
        )
        with make_session() as db:
            messages = list(
                db.scalars(select(Message).where(Message.conversation_id == conversation_id))
            )
            run = db.get(AgentRun, result.run_id)
            if run is None or run.status != "completed" or len(messages) != 2:
                raise RuntimeError("AgentService did not persist a complete run")
            print(
                json.dumps(
                    {
                        "run_id": str(result.run_id),
                        "conversation_id": str(conversation_id),
                        "status": run.status,
                        "persisted_roles": [row.role for row in messages],
                        "answer_persisted": messages[1].content == result.assistant_message.content,
                    },
                    ensure_ascii=False,
                )
            )
    finally:
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
