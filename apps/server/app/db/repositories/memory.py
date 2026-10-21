"""PostgreSQL adapter for the Agent-owned MemoryStore protocol."""

from collections.abc import Callable
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.agent.contracts import MemoryControl, MemoryRecord, MemoryWriteStatus
from app.agent.memory import MAX_OPERATIONS, MAX_TOTAL, MemoryWriteBlocked, content_key
from app.db.models import (
    MemoryControlRow,
    MemoryOperationRow,
    MemoryRecordRow,
    Person,
    Relationship,
    User,
)
from app.retention import RetentionPolicy, as_utc, utc_now


class SQLAlchemyMemoryStore:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        *,
        policy: RetentionPolicy | None = None,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._session_factory = session_factory
        self.policy = policy or RetentionPolicy()
        self.clock = clock

    def get_control(self, user_id: UUID) -> MemoryControl:
        return self.control_state(user_id)[0]

    def control_state(self, user_id: UUID) -> tuple[MemoryControl, datetime | None]:
        with self._session_factory() as db:
            row = db.scalar(select(MemoryControlRow).where(MemoryControlRow.user_id == user_id))
            return (
                (
                    MemoryControl(consent_enabled=row.consent_enabled, paused=row.paused),
                    row.updated_at,
                )
                if row is not None
                else (MemoryControl(), None)
            )

    def owner_exists(self, user_id: UUID) -> bool:
        with self._session_factory() as db:
            return (
                db.scalar(select(User.id).where(User.id == user_id, User.deleted_at.is_(None)))
                is not None
            )

    def person_exists(self, user_id: UUID, person_id: UUID) -> bool:
        with self._session_factory() as db:
            return (
                db.scalar(
                    select(Person.id).where(
                        Person.user_id == user_id,
                        Person.id == person_id,
                        Person.deleted_at.is_(None),
                    )
                )
                is not None
            )

    def relationship_person(self, user_id: UUID, relationship_id: UUID) -> UUID | None:
        return self.resolve_person(user_id, relationship_id)

    def set_control(self, user_id: UUID, control: MemoryControl) -> None:
        with self._session_factory() as db:
            if (
                db.scalar(
                    select(User.id)
                    .where(User.id == user_id, User.deleted_at.is_(None))
                    .with_for_update()
                )
                is None
            ):
                raise LookupError("memory owner not found")
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

    def change_control(self, user_id: UUID, decision: str) -> MemoryControl | None:
        if decision not in {"grant", "revoke", "pause", "resume"}:
            raise ValueError("invalid memory control decision")
        with self._session_factory() as db:
            if (
                db.scalar(
                    select(User.id)
                    .where(User.id == user_id, User.deleted_at.is_(None))
                    .with_for_update()
                )
                is None
            ):
                raise LookupError("memory owner not found")
            row = db.scalar(select(MemoryControlRow).where(MemoryControlRow.user_id == user_id))
            current = MemoryControl(
                consent_enabled=row.consent_enabled if row is not None else False,
                paused=row.paused if row is not None else False,
            )
            if decision in {"pause", "resume"} and not current.consent_enabled:
                return None
            target = current.model_copy()
            if decision == "grant":
                target.consent_enabled = True
            elif decision == "revoke":
                target.consent_enabled = False
                target.paused = True
            else:
                target.paused = decision == "pause"
            if row is None:
                db.add(
                    MemoryControlRow(
                        id=uuid4(),
                        user_id=user_id,
                        consent_enabled=target.consent_enabled,
                        paused=target.paused,
                    )
                )
            elif target != current:
                row.consent_enabled = target.consent_enabled
                row.paused = target.paused
            db.commit()
            return target

    def page_records(
        self,
        user_id: UUID,
        *,
        person_id: UUID | None,
        relationship_id: UUID | None,
        after: tuple[datetime, UUID] | None,
        limit: int,
    ) -> list[MemoryRecord]:
        with self._session_factory() as db:
            query = select(MemoryRecordRow).where(
                MemoryRecordRow.owner_user_id == user_id,
                MemoryRecordRow.expires_at > as_utc(self.clock()),
            )
            if person_id is not None:
                query = query.where(MemoryRecordRow.person_id == person_id)
            if relationship_id is not None:
                query = query.where(MemoryRecordRow.relationship_id == relationship_id)
            if after is not None:
                created_at, record_id = after
                query = query.where(
                    or_(
                        MemoryRecordRow.created_at < created_at,
                        and_(
                            MemoryRecordRow.created_at == created_at,
                            MemoryRecordRow.id < record_id,
                        ),
                    )
                )
            rows = db.scalars(
                query.order_by(MemoryRecordRow.created_at.desc(), MemoryRecordRow.id.desc()).limit(
                    limit
                )
            ).all()
            return [self._record(row) for row in rows]

    def get_record(self, user_id: UUID, memory_id: UUID) -> MemoryRecord | None:
        with self._session_factory() as db:
            row = db.scalar(
                select(MemoryRecordRow).where(
                    MemoryRecordRow.owner_user_id == user_id,
                    MemoryRecordRow.id == memory_id,
                )
            )
            return self._record(row) if row is not None else None

    @staticmethod
    def _record(row: MemoryRecordRow) -> MemoryRecord:
        return MemoryRecord(
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
            expires_at=row.expires_at,
        )

    def resolve_person(self, user_id: UUID, relationship_id: UUID) -> UUID | None:
        with self._session_factory() as db:
            return db.scalar(
                select(Relationship.person_id).where(
                    Relationship.user_id == user_id,
                    Relationship.id == relationship_id,
                    Relationship.deleted_at.is_(None),
                )
            )

    def list_records(self, user_id: UUID, person_id: UUID | None = None) -> list[MemoryRecord]:
        with self._session_factory() as db:
            query = select(MemoryRecordRow).where(
                MemoryRecordRow.owner_user_id == user_id,
                MemoryRecordRow.expires_at > as_utc(self.clock()),
            )
            if person_id is not None:
                query = query.where(MemoryRecordRow.subject_id.in_([user_id, person_id]))
            rows = db.scalars(
                query.order_by(MemoryRecordRow.created_at.desc(), MemoryRecordRow.id)
            ).all()
            return [self._record(row) for row in rows]

    def save_record(self, record: MemoryRecord) -> bool:
        with self._session_factory() as db:
            # Serialize the final write gate with API and Agent control changes.
            if (
                db.scalar(
                    select(User.id)
                    .where(User.id == record.owner_user_id, User.deleted_at.is_(None))
                    .with_for_update()
                )
                is None
            ):
                raise MemoryWriteBlocked(MemoryWriteStatus.SKIPPED_NO_CONSENT)
            control = db.scalar(
                select(MemoryControlRow).where(MemoryControlRow.user_id == record.owner_user_id)
            )
            if control is None or not control.consent_enabled:
                raise MemoryWriteBlocked(MemoryWriteStatus.SKIPPED_NO_CONSENT)
            if control.paused:
                raise MemoryWriteBlocked(MemoryWriteStatus.SKIPPED_PAUSED)
            if record.person_id is not None:
                valid = db.scalar(
                    select(Relationship.id).where(
                        Relationship.user_id == record.owner_user_id,
                        Relationship.id == record.relationship_id,
                        Relationship.person_id == record.person_id,
                        Relationship.deleted_at.is_(None),
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
            existing = db.execute(
                select(MemoryRecordRow.id, MemoryRecordRow.expires_at).where(
                    MemoryRecordRow.owner_user_id == record.owner_user_id,
                    MemoryRecordRow.subject_id == record.subject_id,
                    MemoryRecordRow.type == record.type,
                    MemoryRecordRow.content_hash == key,
                )
            ).one_or_none()
            if existing is not None:
                if existing.expires_at > as_utc(self.clock()):
                    return False
                # A fresh, authorized save replaces only this expired collision.
                # FK cascade invalidates its old undo operation; rollback restores both.
                db.execute(delete(MemoryRecordRow).where(MemoryRecordRow.id == existing.id))
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
                    expires_at=record.expires_at,
                )
                .on_conflict_do_nothing(constraint="uq_memory_records_owner_user_id")
            )
            inserted = (
                db.execute(statement.returning(MemoryRecordRow.id)).scalar_one_or_none() is not None
            )
            if not inserted and existing is not None:
                db.rollback()
                return False
            if inserted:
                db.add(
                    MemoryOperationRow(
                        id=uuid4(),
                        owner_user_id=record.owner_user_id,
                        record_id=record.id,
                        created_at=record.created_at,
                        updated_at=record.updated_at,
                    )
                )
                db.flush()
                old_ids = db.scalars(
                    select(MemoryOperationRow.id)
                    .where(MemoryOperationRow.owner_user_id == record.owner_user_id)
                    .order_by(MemoryOperationRow.created_at.desc(), MemoryOperationRow.id.desc())
                    .offset(MAX_OPERATIONS)
                ).all()
                if old_ids:
                    db.execute(delete(MemoryOperationRow).where(MemoryOperationRow.id.in_(old_ids)))
            db.commit()
            return inserted

    def undo_last(self, user_id: UUID) -> bool:
        with self._session_factory() as db:
            if (
                db.scalar(
                    select(User.id)
                    .where(User.id == user_id, User.deleted_at.is_(None))
                    .with_for_update()
                )
                is None
            ):
                return False
            operation = db.scalar(
                select(MemoryOperationRow)
                .where(MemoryOperationRow.owner_user_id == user_id)
                .order_by(MemoryOperationRow.created_at.desc(), MemoryOperationRow.id.desc())
                .limit(1)
                .with_for_update()
            )
            if operation is None:
                return False
            deleted = db.execute(
                delete(MemoryRecordRow).where(
                    MemoryRecordRow.owner_user_id == user_id,
                    MemoryRecordRow.id == operation.record_id,
                )
            ).rowcount
            if deleted != 1:
                raise ValueError("memory undo history is inconsistent")
            db.commit()
            return True

    def delete_one(self, user_id: UUID, memory_id: UUID, person_id: UUID | None) -> bool:
        with self._session_factory() as db:
            if (
                db.scalar(
                    select(User.id)
                    .where(User.id == user_id, User.deleted_at.is_(None))
                    .with_for_update()
                )
                is None
            ):
                return False
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
            if (
                db.scalar(
                    select(User.id)
                    .where(User.id == user_id, User.deleted_at.is_(None))
                    .with_for_update()
                )
                is None
            ):
                return 0
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
            if (
                db.scalar(
                    select(User.id)
                    .where(User.id == user_id, User.deleted_at.is_(None))
                    .with_for_update()
                )
                is None
            ):
                return 0
            result = db.execute(
                delete(MemoryRecordRow).where(MemoryRecordRow.owner_user_id == user_id)
            )
            db.commit()
            return result.rowcount
