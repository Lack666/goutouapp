"""Phase 5C disposable PostgreSQL demo with persistence and idempotent replay."""

import json
import os
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.chat_import import ChatImportSource, ImportOptions, WeChatMarkdownParser
from app.db.models import Message, RelationshipMessage
from app.db.repositories import records
from app.services.agent_service import actor_from_verified_identity
from app.services.import_jobs import ImportJobService, SpeakerBinding
from app.services.import_merge import ImportMergeService, list_relationship_messages

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).parent / "tests" / "fixtures" / "wechat_markdown_v1.md"


def source() -> ChatImportSource:
    return ChatImportSource([FIXTURE.read_bytes()])


def main() -> None:
    raw = os.getenv("TEST_DATABASE_URL")
    if not raw:
        raise RuntimeError("TEST_DATABASE_URL is required")
    url = make_url(raw)
    if url.drivername != "postgresql+psycopg" or not (url.database or "").endswith("_test"):
        raise RuntimeError("TEST_DATABASE_URL must target a separate psycopg _test namespace")
    dev = os.getenv("DATABASE_URL")
    if dev and make_url(dev).database == url.database:
        raise RuntimeError("TEST_DATABASE_URL must differ from DATABASE_URL")
    name = f"{url.database}_{uuid4().hex[:12]}"
    isolated = url.set(database=name)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    engine = None
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
        config = Config(str(ROOT / "alembic.ini"))
        config.attributes["database_url"] = isolated.render_as_string(hide_password=False)
        command.upgrade(config, "head")
        engine = create_engine(isolated, hide_parameters=True)
        make_session = sessionmaker(bind=engine, expire_on_commit=False)
        parsed = WeChatMarkdownParser().parse(
            source(), ImportOptions(source_timezone="Asia/Shanghai", include_messages=False)
        )
        with make_session() as db, db.begin():
            user = records.create_user(db)
            actor = actor_from_verified_identity(user.id)
            person = records.create_person(db, user.id, "synthetic person")
            relationship = records.create_relationship(db, user.id, person.id, "dating", "active")
            service = ImportJobService(db)
            job = service.create(actor, parsed)
            service.set_speaker_binding(actor, job.id, "我", SpeakerBinding.SELF)
            service.set_speaker_binding(actor, job.id, "怡宝🥰", SpeakerBinding.PERSON, person.id)
            service.set_relationship_binding(actor, job.id, relationship.id)
            revision = service.mark_ready(actor, job.id).binding_revision
            job_id, relationship_id = job.id, relationship.id
        merge_service = ImportMergeService(make_session)
        first = merge_service.merge(
            actor=actor, job_id=job_id, expected_revision=revision, source=source()
        )
        with make_session() as db:
            ordered = list_relationship_messages(db, actor, relationship_id)
            formal_count = db.scalar(select(func.count()).select_from(RelationshipMessage))
            agent_count = db.scalar(select(func.count()).select_from(Message))
            assert len(ordered) == formal_count == first.imported_message_count == 4
            assert agent_count == 0
        replay = ImportMergeService(make_session).merge(
            actor=actor, job_id=job_id, expected_revision=revision, source=source()
        )
        assert replay.new_message_count == 0
        print(
            json.dumps(
                {
                    "job_id": str(job_id),
                    "status": first.status.value,
                    "imported_count": first.imported_message_count,
                    "ignored_count": first.ignored_message_count,
                    "first_timestamp_utc": first.first_timestamp_utc.isoformat(),
                    "last_timestamp_utc": first.last_timestamp_utc.isoformat(),
                    "persisted_after_new_session": True,
                    "agent_message_count": agent_count,
                    "replay_status": replay.status.value,
                    "replay_duplicate_writes": replay.new_message_count,
                }
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
                {"database": name},
            )
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        admin.dispose()


if __name__ == "__main__":
    main()
