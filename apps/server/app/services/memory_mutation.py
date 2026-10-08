"""Authenticated, retry-safe memory undo and confirmed primary-store deletion."""

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import (
    MemoryConfirmationRow,
    MemoryControlRow,
    MemoryMutationRow,
    MemoryOperationRow,
    MemoryRecordRow,
    Person,
    User,
)
from app.services.agent_service import AuthenticatedActor, valid_operation_key

CONFIRMATION_LIFETIME = timedelta(minutes=5)


class MemoryMutationErrorCode(StrEnum):
    UNAUTHORIZED = "unauthorized"
    INVALID_OPERATION_KEY = "invalid_operation_key"
    MEMORY_NOT_FOUND = "memory_not_found"
    PERSON_NOT_FOUND = "person_not_found"
    CONFIRMATION_REQUIRED = "confirmation_required"
    CONFIRMATION_EXPIRED = "confirmation_expired"
    CONFIRMATION_STALE = "confirmation_stale"
    MUTATION_CONFLICT = "mutation_conflict"
    MUTATION_NOT_FOUND = "mutation_not_found"
    UNDO_UNAVAILABLE = "undo_unavailable"
    STALE_UNDO = "stale_undo"
    PERSISTENCE_FAILURE = "persistence_failure"


class MemoryMutationError(Exception):
    def __init__(self, code: MemoryMutationErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


class PublicModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class UndoPreview(PublicModel):
    available: bool
    latest_operation_id: UUID | None = None
    memory_id: UUID | None = None
    type: str | None = None
    person_id: UUID | None = None
    relationship_id: UUID | None = None
    created_at: datetime | None = None


class MemoryConfirmationChallenge(PublicModel):
    confirmation_id: UUID
    owner_user_id: UUID
    action: str
    target_id: UUID | None
    person_id: UUID | None
    relationship_id: UUID | None
    expected_count: int
    revoke_consent_after_delete: bool
    issued_at: datetime
    expires_at: datetime


class MemoryMutationReceipt(PublicModel):
    mutation_id: UUID
    operation_key: str
    action: str
    status: str
    affected_count: int
    target_id: UUID | None
    person_id: UUID | None
    relationship_id: UUID | None
    undone_memory_id: UUID | None
    performed_at: datetime
    replayed: bool
    primary_store_only: bool = True


def _fingerprint(action: str, token: UUID) -> str:
    return hashlib.sha256(f"{action}:{token}".encode()).hexdigest()


def _snapshot(rows: list[MemoryRecordRow]) -> str:
    items = sorted((str(row.id), row.updated_at.isoformat()) for row in rows)
    return hashlib.sha256(json.dumps(items, separators=(",", ":")).encode()).hexdigest()


class MemoryMutationService:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._clock = clock or (lambda: datetime.now(UTC))

    @staticmethod
    def _actor_id(actor: AuthenticatedActor) -> UUID:
        if not isinstance(actor, AuthenticatedActor):
            raise MemoryMutationError(MemoryMutationErrorCode.UNAUTHORIZED)
        return actor.user_id

    @staticmethod
    def _owner(db: Session, owner_id: UUID, *, lock: bool) -> None:
        query = select(User.id).where(User.id == owner_id)
        if lock:
            query = query.with_for_update()
        if db.scalar(query) is None:
            raise MemoryMutationError(MemoryMutationErrorCode.UNAUTHORIZED)

    @staticmethod
    def _operation_key(value: str) -> None:
        if not valid_operation_key(value):
            raise MemoryMutationError(MemoryMutationErrorCode.INVALID_OPERATION_KEY)

    @staticmethod
    def _latest(db: Session, owner_id: UUID) -> tuple[MemoryOperationRow, MemoryRecordRow] | None:
        return db.execute(
            select(MemoryOperationRow, MemoryRecordRow)
            .join(
                MemoryRecordRow,
                (MemoryRecordRow.owner_user_id == MemoryOperationRow.owner_user_id)
                & (MemoryRecordRow.id == MemoryOperationRow.record_id),
            )
            .where(MemoryOperationRow.owner_user_id == owner_id)
            .order_by(MemoryOperationRow.created_at.desc(), MemoryOperationRow.id.desc())
            .limit(1)
        ).first()

    @staticmethod
    def _receipt(row: MemoryMutationRow, *, replayed: bool) -> MemoryMutationReceipt:
        return MemoryMutationReceipt(
            mutation_id=row.id,
            operation_key=row.operation_key,
            action=row.action,
            status=row.status,
            affected_count=row.affected_count,
            target_id=row.target_id,
            person_id=row.person_id,
            relationship_id=row.relationship_id,
            undone_memory_id=row.undone_memory_id,
            performed_at=row.performed_at,
            replayed=replayed,
        )

    @staticmethod
    def _existing(
        db: Session, owner_id: UUID, operation_key: str, fingerprint: str
    ) -> MemoryMutationReceipt | None:
        row = db.scalar(
            select(MemoryMutationRow).where(
                MemoryMutationRow.owner_user_id == owner_id,
                MemoryMutationRow.operation_key == operation_key,
            )
        )
        if row is None:
            return None
        if row.request_fingerprint != fingerprint:
            raise MemoryMutationError(MemoryMutationErrorCode.MUTATION_CONFLICT)
        return MemoryMutationService._receipt(row, replayed=True)

    @staticmethod
    def _add_receipt(db: Session, row: MemoryMutationRow) -> None:
        db.add(row)
        db.flush()

    def preview_undo(self, actor: AuthenticatedActor) -> UndoPreview:
        owner_id = self._actor_id(actor)
        try:
            with self._session_factory() as db:
                self._owner(db, owner_id, lock=False)
                latest = self._latest(db, owner_id)
                if latest is None:
                    return UndoPreview(available=False)
                operation, record = latest
                if record.expires_at <= self._clock():
                    return UndoPreview(available=False)
                return UndoPreview(
                    available=True,
                    latest_operation_id=operation.id,
                    memory_id=record.id,
                    type=record.type,
                    person_id=record.person_id,
                    relationship_id=record.relationship_id,
                    created_at=operation.created_at,
                )
        except MemoryMutationError:
            raise
        except Exception:
            raise MemoryMutationError(MemoryMutationErrorCode.PERSISTENCE_FAILURE) from None

    def undo(
        self, actor: AuthenticatedActor, *, expected_operation_id: UUID, operation_key: str
    ) -> MemoryMutationReceipt:
        owner_id = self._actor_id(actor)
        self._operation_key(operation_key)
        fingerprint = _fingerprint("undo", expected_operation_id)
        try:
            with self._session_factory() as db, db.begin():
                self._owner(db, owner_id, lock=True)
                prior = self._existing(db, owner_id, operation_key, fingerprint)
                if prior is not None:
                    return prior
                latest = self._latest(db, owner_id)
                if latest is None:
                    raise MemoryMutationError(MemoryMutationErrorCode.UNDO_UNAVAILABLE)
                operation, record = latest
                if operation.id != expected_operation_id:
                    raise MemoryMutationError(MemoryMutationErrorCode.STALE_UNDO)
                if record.expires_at <= self._clock():
                    raise MemoryMutationError(MemoryMutationErrorCode.UNDO_UNAVAILABLE)
                removed = db.execute(
                    delete(MemoryRecordRow).where(
                        MemoryRecordRow.owner_user_id == owner_id,
                        MemoryRecordRow.id == record.id,
                    )
                ).rowcount
                if removed != 1:
                    raise MemoryMutationError(MemoryMutationErrorCode.STALE_UNDO)
                row = MemoryMutationRow(
                    id=uuid4(),
                    owner_user_id=owner_id,
                    operation_key=operation_key,
                    request_fingerprint=fingerprint,
                    action="undo",
                    status="undone",
                    affected_count=1,
                    target_id=record.id,
                    person_id=record.person_id,
                    relationship_id=record.relationship_id,
                    undone_memory_id=record.id,
                    performed_at=self._clock(),
                )
                self._add_receipt(db, row)
                return self._receipt(row, replayed=False)
        except MemoryMutationError:
            raise
        except Exception:
            raise MemoryMutationError(MemoryMutationErrorCode.PERSISTENCE_FAILURE) from None

    @staticmethod
    def _target_rows(
        db: Session, owner_id: UUID, action: str, target_id: UUID | None
    ) -> list[MemoryRecordRow]:
        query = select(MemoryRecordRow).where(MemoryRecordRow.owner_user_id == owner_id)
        if action == "delete_one":
            query = query.where(MemoryRecordRow.id == target_id)
        elif action == "delete_person":
            query = query.where(MemoryRecordRow.person_id == target_id)
        elif action != "delete_all":
            raise ValueError("invalid delete action")
        return list(db.scalars(query.order_by(MemoryRecordRow.id)).all())

    def _prepare(
        self,
        actor: AuthenticatedActor,
        *,
        action: str,
        target_id: UUID | None,
        person_id: UUID | None = None,
        relationship_id: UUID | None = None,
        revoke_consent_after_delete: bool = False,
    ) -> MemoryConfirmationChallenge:
        owner_id = self._actor_id(actor)
        try:
            with self._session_factory() as db, db.begin():
                self._owner(db, owner_id, lock=False)
                if (
                    action == "delete_person"
                    and db.scalar(
                        select(Person.id).where(Person.user_id == owner_id, Person.id == target_id)
                    )
                    is None
                ):
                    raise MemoryMutationError(MemoryMutationErrorCode.PERSON_NOT_FOUND)
                rows = self._target_rows(db, owner_id, action, target_id)
                if action == "delete_one":
                    if not rows or (
                        rows[0].person_id != person_id or rows[0].relationship_id != relationship_id
                    ):
                        raise MemoryMutationError(MemoryMutationErrorCode.MEMORY_NOT_FOUND)
                now = self._clock()
                row = MemoryConfirmationRow(
                    id=uuid4(),
                    owner_user_id=owner_id,
                    action=action,
                    target_id=target_id,
                    person_id=person_id,
                    relationship_id=relationship_id,
                    revoke_consent_after_delete=revoke_consent_after_delete,
                    expected_count=len(rows),
                    snapshot_hash=_snapshot(rows),
                    expires_at=now + CONFIRMATION_LIFETIME,
                )
                db.add(row)
                db.flush()
                return MemoryConfirmationChallenge(
                    confirmation_id=row.id,
                    owner_user_id=owner_id,
                    action=action,
                    target_id=target_id,
                    person_id=person_id,
                    relationship_id=relationship_id,
                    expected_count=len(rows),
                    revoke_consent_after_delete=revoke_consent_after_delete,
                    issued_at=now,
                    expires_at=row.expires_at,
                )
        except MemoryMutationError:
            raise
        except Exception:
            raise MemoryMutationError(MemoryMutationErrorCode.PERSISTENCE_FAILURE) from None

    def prepare_delete_one(
        self,
        actor: AuthenticatedActor,
        *,
        memory_id: UUID,
        person_id: UUID | None,
        relationship_id: UUID | None,
    ) -> MemoryConfirmationChallenge:
        return self._prepare(
            actor,
            action="delete_one",
            target_id=memory_id,
            person_id=person_id,
            relationship_id=relationship_id,
        )

    def prepare_delete_person(
        self, actor: AuthenticatedActor, *, person_id: UUID
    ) -> MemoryConfirmationChallenge:
        return self._prepare(
            actor, action="delete_person", target_id=person_id, person_id=person_id
        )

    def prepare_delete_all(
        self, actor: AuthenticatedActor, *, revoke_consent_after_delete: bool
    ) -> MemoryConfirmationChallenge:
        return self._prepare(
            actor,
            action="delete_all",
            target_id=None,
            revoke_consent_after_delete=revoke_consent_after_delete,
        )

    def execute_delete(
        self, actor: AuthenticatedActor, *, confirmation_id: UUID, operation_key: str
    ) -> MemoryMutationReceipt:
        owner_id = self._actor_id(actor)
        self._operation_key(operation_key)
        fingerprint = _fingerprint("delete", confirmation_id)
        try:
            with self._session_factory() as db, db.begin():
                self._owner(db, owner_id, lock=True)
                prior = self._existing(db, owner_id, operation_key, fingerprint)
                if prior is not None:
                    return prior
                challenge = db.scalar(
                    select(MemoryConfirmationRow)
                    .where(
                        MemoryConfirmationRow.owner_user_id == owner_id,
                        MemoryConfirmationRow.id == confirmation_id,
                    )
                    .with_for_update()
                )
                if challenge is None:
                    raise MemoryMutationError(MemoryMutationErrorCode.CONFIRMATION_REQUIRED)
                now = self._clock()
                if challenge.consumed_at is not None:
                    raise MemoryMutationError(MemoryMutationErrorCode.CONFIRMATION_STALE)
                if now >= challenge.expires_at:
                    raise MemoryMutationError(MemoryMutationErrorCode.CONFIRMATION_EXPIRED)
                if (
                    challenge.action == "delete_person"
                    and db.scalar(
                        select(Person.id).where(
                            Person.user_id == owner_id, Person.id == challenge.target_id
                        )
                    )
                    is None
                ):
                    raise MemoryMutationError(MemoryMutationErrorCode.CONFIRMATION_STALE)
                rows = self._target_rows(db, owner_id, challenge.action, challenge.target_id)
                if challenge.action == "delete_one" and (
                    not rows
                    or rows[0].person_id != challenge.person_id
                    or rows[0].relationship_id != challenge.relationship_id
                ):
                    raise MemoryMutationError(MemoryMutationErrorCode.CONFIRMATION_STALE)
                if (
                    len(rows) != challenge.expected_count
                    or _snapshot(rows) != challenge.snapshot_hash
                ):
                    raise MemoryMutationError(MemoryMutationErrorCode.CONFIRMATION_STALE)
                if rows:
                    count = db.execute(
                        delete(MemoryRecordRow).where(
                            MemoryRecordRow.owner_user_id == owner_id,
                            MemoryRecordRow.id.in_([item.id for item in rows]),
                        )
                    ).rowcount
                else:
                    count = 0
                if count != challenge.expected_count:
                    raise MemoryMutationError(MemoryMutationErrorCode.CONFIRMATION_STALE)
                if challenge.action == "delete_all" and challenge.revoke_consent_after_delete:
                    control = db.scalar(
                        select(MemoryControlRow).where(MemoryControlRow.user_id == owner_id)
                    )
                    if control is None:
                        db.add(
                            MemoryControlRow(
                                id=uuid4(),
                                user_id=owner_id,
                                consent_enabled=False,
                                paused=True,
                            )
                        )
                    else:
                        control.consent_enabled = False
                        control.paused = True
                challenge.consumed_at = now
                row = MemoryMutationRow(
                    id=uuid4(),
                    owner_user_id=owner_id,
                    operation_key=operation_key,
                    request_fingerprint=fingerprint,
                    action=challenge.action,
                    status="deleted",
                    affected_count=count,
                    target_id=challenge.target_id,
                    person_id=challenge.person_id,
                    relationship_id=challenge.relationship_id,
                    confirmation_id=confirmation_id,
                    performed_at=now,
                )
                self._add_receipt(db, row)
                return self._receipt(row, replayed=False)
        except MemoryMutationError:
            raise
        except Exception:
            raise MemoryMutationError(MemoryMutationErrorCode.PERSISTENCE_FAILURE) from None

    def inspect_receipt(
        self, actor: AuthenticatedActor, mutation_id: UUID
    ) -> MemoryMutationReceipt:
        owner_id = self._actor_id(actor)
        try:
            with self._session_factory() as db:
                self._owner(db, owner_id, lock=False)
                row = db.scalar(
                    select(MemoryMutationRow).where(
                        MemoryMutationRow.owner_user_id == owner_id,
                        MemoryMutationRow.id == mutation_id,
                    )
                )
                if row is None:
                    raise MemoryMutationError(MemoryMutationErrorCode.MUTATION_NOT_FOUND)
                return self._receipt(row, replayed=False)
        except MemoryMutationError:
            raise
        except Exception:
            raise MemoryMutationError(MemoryMutationErrorCode.PERSISTENCE_FAILURE) from None
