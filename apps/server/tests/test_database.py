"""PostgreSQL integration tests; require an isolated TEST_DATABASE_URL."""

from datetime import timedelta
from typing import Annotated
from uuid import UUID, uuid4

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.config import Settings
from app.db.models import Conversation, Message, Person, Relationship, User
from app.db.repositories import records
from app.main import create_app
from app.services.conversation import ConversationService


def test_schema_and_utc_timestamps(db_session: Session) -> None:
    user = records.create_user(db_session)
    db_session.commit()
    db_session.refresh(user)
    assert user.created_at.utcoffset() == timedelta(0)
    assert user.updated_at.utcoffset() == timedelta(0)
    assert user.id is not None


def test_conversation_and_message_owner_scope(db_session: Session) -> None:
    owner = records.create_user(db_session)
    outsider = records.create_user(db_session)
    service = ConversationService(db_session)
    conversation = service.create(owner.id)
    message = service.add_message(owner.id, conversation.id, "user", "private", "me")
    assert message is not None
    assert service.get(owner.id, conversation.id) is not None
    assert [item.id for item in service.list_for_owner(owner.id)] == [conversation.id]
    assert [item.id for item in service.list_messages(owner.id, conversation.id)] == [message.id]
    assert service.get(outsider.id, conversation.id) is None
    assert service.list_for_owner(outsider.id) == []
    assert service.list_messages(outsider.id, conversation.id) == []
    assert service.add_message(outsider.id, conversation.id, "user", "cross owner") is None
    assert not service.delete(outsider.id, conversation.id)
    assert service.delete(owner.id, conversation.id)
    assert db_session.scalar(select(Message).where(Message.id == message.id)) is None


def test_person_and_relationship_owner_scope(db_session: Session) -> None:
    owner = records.create_user(db_session)
    outsider = records.create_user(db_session)
    person = records.create_person(db_session, owner.id, "A")
    relationship = records.create_relationship(db_session, owner.id, person.id, "dating", "active")
    assert records.get_person(db_session, owner.id, person.id) is not None
    assert records.get_person(db_session, outsider.id, person.id) is None
    assert records.get_relationship(db_session, owner.id, relationship.id) is not None
    assert records.get_relationship(db_session, outsider.id, relationship.id) is None


def test_cross_owner_foreign_keys_rejected(db_session: Session) -> None:
    owner = records.create_user(db_session)
    outsider = records.create_user(db_session)
    person = records.create_person(db_session, owner.id, "A")
    with pytest.raises(IntegrityError), db_session.begin_nested():
        records.create_relationship(db_session, outsider.id, person.id, "dating", "active")
    relationship = records.create_relationship(db_session, owner.id, person.id, "dating", "active")
    with pytest.raises(IntegrityError), db_session.begin_nested():
        records.create_conversation(db_session, outsider.id, relationship.id)
    conversation = records.create_conversation(db_session, owner.id, relationship.id)
    with pytest.raises(IntegrityError), db_session.begin_nested():
        records.create_agent_run(db_session, outsider.id, conversation.id)


def test_fk_and_delete_semantics(db_session: Session) -> None:
    owner = records.create_user(db_session)
    person = records.create_person(db_session, owner.id, "A")
    relationship = records.create_relationship(db_session, owner.id, person.id, "dating", "active")
    conversation = records.create_conversation(db_session, owner.id, relationship.id)
    message = records.create_message(db_session, owner.id, conversation.id, "user", "hello")
    assert message is not None
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(delete(User).where(User.id == owner.id))
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(delete(Person).where(Person.id == person.id))
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(delete(Relationship).where(Relationship.id == relationship.id))
    run = records.create_agent_run(db_session, owner.id, conversation.id)
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(delete(Conversation).where(Conversation.id == conversation.id))
    db_session.delete(run)
    db_session.flush()
    assert records.delete_conversation(db_session, owner.id, conversation.id)
    assert db_session.scalar(select(Message).where(Message.id == message.id)) is None


def test_missing_foreign_key_rejected(db_session: Session) -> None:
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(Person(user_id=uuid4(), display_name="orphan"))
        db_session.flush()


def test_request_transaction_commit_and_rollback(database_engine) -> None:
    settings = Settings(
        database_url=SecretStr(database_engine.url.render_as_string(hide_password=False))
    )
    app = create_app(settings)

    @app.post("/test/commit")
    def commit(db: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
        user = records.create_user(db)
        return {"id": str(user.id)}

    @app.post("/test/fail")
    def fail(db: Annotated[Session, Depends(get_db)]) -> None:
        records.create_user(db)
        raise RuntimeError("private database context")

    committed_id = None
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            result = client.post("/test/commit")
            assert result.status_code == 200
            committed_id = UUID(result.json()["id"])
            with database_engine.connect() as connection:
                before = connection.scalar(text("SELECT count(*) FROM users"))
            failure = client.post("/test/fail")
            assert failure.status_code == 500
            assert "private database context" not in failure.text
            with database_engine.connect() as connection:
                assert connection.scalar(text("SELECT count(*) FROM users")) == before
    finally:
        if committed_id is not None:
            with database_engine.begin() as connection:
                connection.execute(delete(User).where(User.id == committed_id))
        app.state.database.dispose()


def test_readiness_up_and_down(database_engine) -> None:
    app = create_app(
        Settings(database_url=SecretStr(database_engine.url.render_as_string(hide_password=False)))
    )
    with TestClient(app) as client:
        assert client.get("/ready").status_code == 200
    app.state.database.dispose()

    unavailable = create_app(
        Settings(
            database_url=SecretStr("postgresql+psycopg://user:supersecret@127.0.0.1:1/missing")
        )
    )
    with TestClient(unavailable) as client:
        assert client.get("/health").status_code == 200
        down = client.get("/ready")
        assert down.status_code == 503
        assert down.json() == {
            "error": {"code": "database_unavailable", "message": "Database unavailable"}
        }
        assert "supersecret" not in down.text
    unavailable.state.database.dispose()
