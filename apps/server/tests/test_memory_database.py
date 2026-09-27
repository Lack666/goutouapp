"""Real PostgreSQL memory persistence, ownership and transaction checks."""

from uuid import uuid4

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.agent.contracts import Fact, MemoryCandidate, MemoryDecision, MemoryWriteStatus
from app.agent.memory import MemoryService
from app.db.models import MemoryRecordRow, Message
from app.db.repositories import records
from app.db.repositories.memory import SQLAlchemyMemoryStore


def setup_records(engine: Engine):
    with Session(engine) as db:
        owner, outsider = records.create_user(db), records.create_user(db)
        person_a = records.create_person(db, owner.id, "A")
        person_b = records.create_person(db, owner.id, "B")
        relation_a = records.create_relationship(db, owner.id, person_a.id, "dating", "active")
        relation_b = records.create_relationship(db, owner.id, person_b.id, "dating", "active")
        conversation = records.create_conversation(db, owner.id, relation_a.id)
        message = records.create_message(db, owner.id, conversation.id, "user", "Synthetic chat")
        assert message is not None
        ids = (
            owner.id,
            outsider.id,
            person_a.id,
            person_b.id,
            relation_a.id,
            relation_b.id,
            conversation.id,
            message.id,
        )
        db.commit()
    return ids


def save(service, owner, person, relationship, content="我们已确认关系"):
    return service.persist_candidates(
        user_id=owner,
        relationship_id=relationship,
        run_id=uuid4(),
        candidates=[
            MemoryCandidate(
                subject_id=person,
                type="relationship",
                content=content,
                source="user_explicit",
                evidence="F1",
            )
        ],
        facts=[Fact(statement=content, source="user_explicit")],
        message=f"我明确同意记住：{content}",
        explicit_consent=True,
    )


def test_postgres_memory_survives_new_session_and_is_owner_person_scoped(database_engine: Engine):
    owner, outsider, person_a, person_b, relation_a, relation_b, conversation, message = (
        setup_records(database_engine)
    )

    def factory():
        return Session(database_engine)

    service = MemoryService(SQLAlchemyMemoryStore(factory))
    receipt = save(service, owner, person_a, relation_a)
    assert receipt.status == MemoryWriteStatus.SAVED and receipt.saved_count == 1
    # A new store and session simulate a new process lifecycle.
    fresh = MemoryService(SQLAlchemyMemoryStore(factory))
    a = fresh.load_for_context(owner, relation_a, enabled=True)
    assert len(a) == 1 and a[0].content == "我们已确认关系"
    assert fresh.load_for_context(owner, relation_b, enabled=True) == []
    assert fresh.load_for_context(outsider, relation_a, enabled=True) == []
    assert fresh.list_for_user(outsider) == []
    assert fresh.resolve_person(outsider, relation_a) is None
    duplicate = save(fresh, owner, person_a, relation_a)
    assert duplicate.status == MemoryWriteStatus.DUPLICATE
    save(fresh, owner, person_b, relation_b, "我们计划明年见面")
    assert [
        record.subject_id for record in fresh.load_for_context(owner, relation_b, enabled=True)
    ] == [person_b]
    assert not fresh.delete_one(outsider, a[0].id, person_id=person_a)
    assert not fresh.delete_one(owner, a[0].id, person_id=person_b)
    assert fresh.delete_one(owner, a[0].id, person_id=person_a)
    assert not fresh.delete_one(owner, a[0].id, person_id=person_a)
    save(fresh, owner, person_a, relation_a)
    assert fresh.delete_person(owner, person_a, confirmed=False) == 0
    assert fresh.delete_person(owner, person_a, confirmed=True) == 1
    assert len(fresh.list_for_user(owner)) == 1
    assert fresh.delete_all(owner, confirmed=False) == 0
    assert fresh.delete_all(owner, confirmed=True, revoke=True) == 1
    assert fresh.list_for_user(owner) == []
    assert not fresh.control(owner).consent_enabled
    with factory() as db:
        assert db.scalar(select(Message).where(Message.id == message)) is not None
        assert (
            db.scalar(select(MemoryRecordRow).where(MemoryRecordRow.owner_user_id == owner)) is None
        )


def test_postgres_pause_resume_and_fk_rollback(database_engine: Engine):
    owner, outsider, person_a, person_b, relation_a, _relation_b, *_ = setup_records(
        database_engine
    )

    def factory():
        return Session(database_engine)

    service = MemoryService(SQLAlchemyMemoryStore(factory))
    save(service, owner, person_a, relation_a)
    service.apply_control(owner, MemoryDecision.PAUSE)
    assert service.load_for_context(owner, relation_a, enabled=True) == []
    assert len(service.list_for_user(owner)) == 1
    assert (
        service.apply_control(owner, MemoryDecision.RESUME).status
        == MemoryWriteStatus.CONTROL_UPDATED
    )
    assert len(service.load_for_context(owner, relation_a, enabled=True)) == 1
    # Direct ORM bypass remains blocked by composite owner/person/relationship FKs.
    with factory() as db:
        db.add(
            MemoryRecordRow(
                id=uuid4(),
                owner_user_id=outsider,
                subject_id=person_a,
                person_id=person_a,
                relationship_id=relation_a,
                type="relationship",
                content="Invalid cross-owner row",
                content_hash="0" * 64,
                source="user_explicit",
                evidence=f"{uuid4()}: F1",
                first_run_id=uuid4(),
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    with factory() as db:
        assert (
            db.scalar(select(MemoryRecordRow).where(MemoryRecordRow.owner_user_id == outsider))
            is None
        )
    assert service.resolve_person(owner, relation_a) == person_a
    assert service.resolve_person(outsider, relation_a) is None


def test_postgres_same_person_relationship_scope_dedup(database_engine: Engine):
    owner, _outsider, person, _person_b, relation_a, _relation_b, *_ = setup_records(
        database_engine
    )
    with Session(database_engine) as db:
        relation_b = records.create_relationship(db, owner, person, "dating", "renewed")
        relation_b_id = relation_b.id
        db.commit()

    def factory():
        return Session(database_engine)

    service = MemoryService(SQLAlchemyMemoryStore(factory))
    assert save(service, owner, person, relation_a).status == MemoryWriteStatus.SAVED
    assert save(service, owner, person, relation_b_id).status == MemoryWriteStatus.SAVED
    assert save(service, owner, person, relation_b_id).status == MemoryWriteStatus.DUPLICATE
    assert len(service.load_for_context(owner, relation_a, enabled=True)) == 1
    assert len(service.load_for_context(owner, relation_b_id, enabled=True)) == 1
    assert len(service.list_for_user(owner)) == 2
