"""Authenticated, transport-independent memory control and inspection."""

import base64
import binascii
import json
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import SQLAlchemyError

from app.agent.contracts import MemoryRecord
from app.db.repositories.memory import SQLAlchemyMemoryStore
from app.services.agent_service import AuthenticatedActor


class MemoryControlErrorCode(StrEnum):
    UNAUTHORIZED = "unauthorized"
    INVALID_SCOPE = "invalid_scope"
    PERSON_NOT_FOUND = "person_not_found"
    RELATIONSHIP_NOT_FOUND = "relationship_not_found"
    MEMORY_NOT_FOUND = "memory_not_found"
    PERSISTENCE_FAILURE = "persistence_failure"


class MemoryControlError(Exception):
    def __init__(self, code: MemoryControlErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


class PublicModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class MemoryControlView(PublicModel):
    consent_enabled: bool
    paused: bool
    effective_read_enabled: bool
    effective_write_enabled: bool
    updated_at: datetime | None


class MemoryRecordView(PublicModel):
    id: UUID
    type: str
    content: str
    subject_id: UUID
    person_id: UUID | None
    relationship_id: UUID | None
    source: str
    provenance_summary: str
    created_at: datetime
    updated_at: datetime
    historical_notice: str = (
        "Saved memories describe past information and may no longer be accurate."
    )


class MemoryListResult(PublicModel):
    items: list[MemoryRecordView]
    next_cursor: str | None
    historical_notice: str = (
        "Saved memories describe past information and may no longer be accurate."
    )


def _encode_cursor(created_at: datetime, record_id: UUID) -> str:
    raw = json.dumps([created_at.isoformat(), str(record_id)], separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _decode_cursor(value: str | None) -> tuple[datetime, UUID] | None:
    if value is None:
        return None
    if not value or len(value) > 256:
        raise MemoryControlError(MemoryControlErrorCode.INVALID_SCOPE)
    try:
        raw = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
        pair = json.loads(raw)
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError
        timestamp, record_id = datetime.fromisoformat(pair[0]), UUID(pair[1])
        if timestamp.tzinfo is None:
            raise ValueError
        return timestamp, record_id
    except (ValueError, TypeError, UnicodeError, binascii.Error) as exc:
        raise MemoryControlError(MemoryControlErrorCode.INVALID_SCOPE) from exc


class MemoryControlService:
    def __init__(self, store: SQLAlchemyMemoryStore) -> None:
        self._store = store

    def _owner(self, actor: AuthenticatedActor) -> UUID:
        if not isinstance(actor, AuthenticatedActor):
            raise MemoryControlError(MemoryControlErrorCode.UNAUTHORIZED)
        try:
            if not self._store.owner_exists(actor.user_id):
                raise MemoryControlError(MemoryControlErrorCode.UNAUTHORIZED)
        except SQLAlchemyError as exc:
            raise MemoryControlError(MemoryControlErrorCode.PERSISTENCE_FAILURE) from exc
        return actor.user_id

    def inspect_control(self, actor: AuthenticatedActor) -> MemoryControlView:
        owner_id = self._owner(actor)
        try:
            control, updated_at = self._store.control_state(owner_id)
        except SQLAlchemyError as exc:
            raise MemoryControlError(MemoryControlErrorCode.PERSISTENCE_FAILURE) from exc
        effective = control.consent_enabled and not control.paused
        return MemoryControlView(
            consent_enabled=control.consent_enabled,
            paused=control.paused,
            effective_read_enabled=effective,
            effective_write_enabled=effective,
            updated_at=updated_at,
        )

    def _change(self, actor: AuthenticatedActor, operation: str) -> MemoryControlView:
        owner_id = self._owner(actor)
        try:
            self._store.change_control(owner_id, operation)
        except LookupError as exc:
            raise MemoryControlError(MemoryControlErrorCode.UNAUTHORIZED) from exc
        except SQLAlchemyError as exc:
            raise MemoryControlError(MemoryControlErrorCode.PERSISTENCE_FAILURE) from exc
        return self.inspect_control(actor)

    def grant_consent(self, actor: AuthenticatedActor) -> MemoryControlView:
        return self._change(actor, "grant")

    def revoke_consent(self, actor: AuthenticatedActor) -> MemoryControlView:
        return self._change(actor, "revoke")

    def pause(self, actor: AuthenticatedActor) -> MemoryControlView:
        return self._change(actor, "pause")

    def resume(self, actor: AuthenticatedActor) -> MemoryControlView:
        return self._change(actor, "resume")

    @staticmethod
    def _record_view(item: MemoryRecord) -> MemoryRecordView:
        return MemoryRecordView(
            id=item.id,
            type=item.type,
            content=item.content,
            subject_id=item.subject_id,
            person_id=item.person_id,
            relationship_id=item.relationship_id,
            source=item.source,
            provenance_summary=(
                "Saved from an explicit user statement"
                if item.source == "user_explicit"
                else "Saved from a user report"
                if item.source == "user_report"
                else "Saved historical information"
            ),
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    def inspect_memory(self, actor: AuthenticatedActor, memory_id: UUID) -> MemoryRecordView:
        owner_id = self._owner(actor)
        try:
            record = self._store.get_record(owner_id, memory_id)
        except SQLAlchemyError as exc:
            raise MemoryControlError(MemoryControlErrorCode.PERSISTENCE_FAILURE) from exc
        if record is None:
            raise MemoryControlError(MemoryControlErrorCode.MEMORY_NOT_FOUND)
        return self._record_view(record)

    def inspect_memories(
        self,
        actor: AuthenticatedActor,
        *,
        person_id: UUID | None = None,
        relationship_id: UUID | None = None,
        limit: int = 20,
        cursor: str | None = None,
    ) -> MemoryListResult:
        owner_id = self._owner(actor)
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 50:
            raise MemoryControlError(MemoryControlErrorCode.INVALID_SCOPE)
        after = _decode_cursor(cursor)
        try:
            if person_id is not None and not self._store.person_exists(owner_id, person_id):
                raise MemoryControlError(MemoryControlErrorCode.PERSON_NOT_FOUND)
            if relationship_id is not None:
                related_person = self._store.relationship_person(owner_id, relationship_id)
                if related_person is None:
                    raise MemoryControlError(MemoryControlErrorCode.RELATIONSHIP_NOT_FOUND)
                if person_id is not None and person_id != related_person:
                    raise MemoryControlError(MemoryControlErrorCode.INVALID_SCOPE)
            records = self._store.page_records(
                owner_id,
                person_id=person_id,
                relationship_id=relationship_id,
                after=after,
                limit=limit + 1,
            )
        except SQLAlchemyError as exc:
            raise MemoryControlError(MemoryControlErrorCode.PERSISTENCE_FAILURE) from exc
        page = records[:limit]
        next_cursor = (
            _encode_cursor(page[-1].created_at, page[-1].id) if len(records) > limit else None
        )
        return MemoryListResult(
            items=[self._record_view(item) for item in page],
            next_cursor=next_cursor,
        )
