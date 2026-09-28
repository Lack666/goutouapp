"""Phase 5B disposable PostgreSQL demo; no product Message is imported."""

import json
import os
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.chat_import import ChatImportSource, ImportOptions, WeChatMarkdownParser
from app.db.models import Message
from app.db.repositories import records
from app.services.agent_service import actor_from_verified_identity
from app.services.import_jobs import ImportJobService, SpeakerBinding

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).parent / "tests" / "fixtures" / "wechat_markdown_v1.md"


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
        with FIXTURE.open("rb") as stream:
            result = WeChatMarkdownParser().parse(
                ChatImportSource(stream),
                ImportOptions(source_timezone="Asia/Shanghai", include_messages=False),
            )
        with Session(engine) as db:
            user = records.create_user(db)
            actor = actor_from_verified_identity(user.id)
            person = records.create_person(db, user.id, "synthetic person")
            relationship = records.create_relationship(db, user.id, person.id, "dating", "active")
            service = ImportJobService(db)
            job = service.create(actor, result)
            inventory = [
                {"label": speaker.raw_speaker_label, "count": speaker.message_count}
                for speaker in service.list_speakers(actor, job.id)
            ]
            service.set_speaker_binding(actor, job.id, "我", SpeakerBinding.SELF)
            service.set_speaker_binding(actor, job.id, "怡宝🥰", SpeakerBinding.PERSON, person.id)
            service.set_relationship_binding(actor, job.id, relationship.id)
            service.mark_ready(actor, job.id)
            db.commit()
        with Session(engine) as db:
            persisted = ImportJobService(db).inspect(actor, job.id)
            message_count = db.scalar(select(func.count()).select_from(Message))
            assert persisted.status.value == "ready" and message_count == 0
            print(
                json.dumps(
                    {
                        "status": persisted.status.value,
                        "speaker_inventory": inventory,
                        "binding_revision": persisted.binding_revision,
                        "persisted_after_new_session": True,
                        "formal_message_count": message_count,
                    },
                    ensure_ascii=True,
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
