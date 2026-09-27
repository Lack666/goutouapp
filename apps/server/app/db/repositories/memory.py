"""PostgreSQL adapter for the Agent-owned MemoryStore protocol."""

from collections.abc import Callable
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.agent.contracts import MemoryControl, MemoryRecord
from app.agent.memory import MAX_TOTAL, content_key
from app.db.models import MemoryControlRow, MemoryRecordRow, Relationship


class SQLAlchemyMemoryStore:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def get_control(self, user_id: UUID) -> MemoryControl:
        with self._session_factory() as db:
            row = db.scalar(select(MemoryControlRow).where(MemoryControlRow.user_id == user_id))
            return (
                MemoryControl(consent_enabled=row.consent_enabled, paused=row.paused)
                if row
                else MemoryControl()
            )

    def set_control(self, user_id: UUID, control: MemoryControl) -> None:
        with self._session_factory() as db:
            row = db.scalar(select(MemoryControlRow).where(MemoryControlRow.user_id == user_id))
            if row is None:
                row = MemoryControlRow(
                    id=uuid4(),
                    user_id=user_id,
                    consent_enabled=control.consent_enabled,
                    paused=control.paused,
                )
                db.add(row)
            else:
                row.consent_enabled = control.consent_enabled
                row.paused = control.paused
            db.commit()

    def resolve_person(self, user_id: UUID, relationship_id: UUID) -> UUID | None:
        with self._session_factory() as db:
            return db.scalar(
                select(Relationship.person_id).where(
                    Relationship.user_id == user_id, Relationship.id == relationship_id
                )
            )

    def list_records(self, user_id: UUID, person_id: UUID | None = None) -> list[MemoryRecord]:
        with self._session_factory() as db:
            query = select(MemoryRecordRow).where(MemoryRecordRow.owner_user_id == user_id)
            if person_id is not None:
                query = query.where(MemoryRecordRow.subject_id.in_([user_id, person_id]))
            rows = db.scalars(
                query.order_by(MemoryRecordRow.created_at.desc(), MemoryRecordRow.id)
            ).all()
            return [
                MemoryRecord(
                    id=row.id,
                    owner_user_id=row.owner_user_id,
                    subject_id=row.subject_id,
                    person_id=row.person_id,
                    relationship_id=row.relationship_id,
                    type=row.type,
                    content=row.content,
                    source=row.source,
                    evidence=row.evidence,
                    confidence=row.confidence,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
                for row in rows
            ]

    def save_record(self, record: MemoryRecord) -> bool:
        with self._session_factory() as db:
            if record.person_id is not None:
                valid = db.scalar(
                    select(Relationship.id).where(
                        Relationship.user_id == record.owner_user_id,
                        Relationship.id == record.relationship_id,
                        Relationship.person_id == record.person_id,
                    )
                )
                if valid is None or record.subject_id != record.person_id or record.type == "user":
                    raise ValueError("memory scope is invalid")
            elif (
                record.type != "user"
                or record.subject_id != record.owner_user_id
                or record.relationship_id is not None
            ):
                raise ValueError("memory scope is invalid")
            key = content_key(record.content, record.relationship_id)
            existing = db.scalar(
                select(MemoryRecordRow.id).where(
                    MemoryRecordRow.owner_user_id == record.owner_user_id,
                    MemoryRecordRow.subject_id == record.subject_id,
                    MemoryRecordRow.type == record.type,
                    MemoryRecordRow.content_hash == key,
                )
            )
            if existing is not None:
                return False
            count = db.scalar(
                select(func.count())
                .select_from(MemoryRecordRow)
                .where(MemoryRecordRow.owner_user_id == record.owner_user_id)
            )
            if count >= MAX_TOTAL:
                raise ValueError("memory limit reached")
            statement = (
                insert(MemoryRecordRow)
                .values(
                    id=record.id,
                    owner_user_id=record.owner_user_id,
                    subject_id=record.subject_id,
                    person_id=record.person_id,
                    relationship_id=record.relationship_id,
                    type=record.type,
                    content=record.content,
                    content_hash=key,
                    source=record.source,
                    evidence=record.evidence,
                    confidence=record.confidence,
                    first_run_id=UUID(record.evidence.split(":", 1)[0]),
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                )
                .on_conflict_do_nothing(constraint="uq_memory_records_owner_user_id")
            )
            inserted = (
                db.execute(statement.returning(MemoryRecordRow.id)).scalar_one_or_none() is not None
            )
            db.commit()
            return inserted

    def delete_one(self, user_id: UUID, memory_id: UUID, person_id: UUID | None) -> bool:
        with self._session_factory() as db:
            result = db.execute(
                delete(MemoryRecordRow).where(
                    MemoryRecordRow.owner_user_id == user_id,
                    MemoryRecordRow.id == memory_id,
                    MemoryRecordRow.person_id == person_id,
                )
            )
            db.commit()
            return result.rowcount == 1

    def delete_person(self, user_id: UUID, person_id: UUID) -> int:
        with self._session_factory() as db:
            result = db.execute(
                delete(MemoryRecordRow).where(
                    MemoryRecordRow.owner_user_id == user_id,
                    MemoryRecordRow.person_id == person_id,
                )
            )
            db.commit()
            return result.rowcount

    def delete_all(self, user_id: UUID) -> int:
        with self._session_factory() as db:
            result = db.execute(
                delete(MemoryRecordRow).where(MemoryRecordRow.owner_user_id == user_id)
            )
            db.commit()
            return result.rowcount
