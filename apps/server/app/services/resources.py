"""Authenticated resource acquisition and Agent history, independent of transport/LLM."""

import base64
import binascii
import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from uuid import UUID

from sqlalchemy import func, select, tuple_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import ChatImportJob, Conversation, Person, Relationship, RelationshipMessage
from app.db.repositories import records, resources
from app.schemas.resources import (
    AgentMessagePage,
    AgentMessagePublicResponse,
    ConversationCreateRequest,
    ConversationPage,
    ConversationResponse,
    DatasetPage,
    DatasetSummary,
    PageRequest,
    PersonCreateRequest,
    PersonPage,
    PersonResponse,
    RelationshipCreateRequest,
    RelationshipPage,
    RelationshipResponse,
)
from app.services.agent_service import AuthenticatedActor


class ResourceErrorCode(StrEnum):
    UNAUTHORIZED = "unauthorized"
    NOT_FOUND = "not_found"
    CREATION_CONFLICT = "resource_creation_conflict"
    INVALID_CURSOR = "invalid_cursor"
    PERSISTENCE_FAILURE = "persistence_failure"


class ResourceError(Exception):
    def __init__(self, code: ResourceErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


def _context(owner: UUID, domain: str, parent: UUID | None = None) -> str:
    return sha256(f"resource-page-v1:{owner}:{domain}:{parent}".encode()).hexdigest()


def _decode_cursor(value: str | None, context: str) -> resources.Position | None:
    if value is None:
        return None
    try:
        if not 1 <= len(value) <= 512:
            raise ValueError
        raw = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
        parts = json.loads(raw)
        if (
            not isinstance(parts, list)
            or len(parts) != 4
            or type(parts[0]) is not int
            or parts[0] != 1
            or parts[1] != context
            or not isinstance(parts[2], str)
            or not isinstance(parts[3], str)
        ):
            raise ValueError
        timestamp, record_id = datetime.fromisoformat(parts[2]), UUID(parts[3])
        if timestamp.tzinfo is None:
            raise ValueError
        return timestamp, record_id
    except (ValueError, TypeError, UnicodeError, binascii.Error) as exc:
        raise ResourceError(ResourceErrorCode.INVALID_CURSOR) from exc


def _next_cursor(rows: list, limit: int, context: str) -> str | None:
    if len(rows) <= limit:
        return None
    last = rows[limit - 1]
    raw = json.dumps([1, context, last.created_at.isoformat(), str(last.id)], separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


BaseResourceRequest = PersonCreateRequest | RelationshipCreateRequest | ConversationCreateRequest


class ResourceService:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    @contextmanager
    def _transaction(self, actor: AuthenticatedActor) -> Iterator[Session]:
        if not isinstance(actor, AuthenticatedActor):
            raise ResourceError(ResourceErrorCode.UNAUTHORIZED)
        try:
            with self._session_factory() as db, db.begin():
                if records.get_user(db, actor.user_id) is None:
                    raise ResourceError(ResourceErrorCode.UNAUTHORIZED)
                yield db
        except SQLAlchemyError as exc:
            raise ResourceError(ResourceErrorCode.PERSISTENCE_FAILURE) from exc

    def _existing(self, db: Session, model: type, owner: UUID, body: BaseResourceRequest):
        resources.lock_creation(db, model.__tablename__, body.id)
        record = db.get(model, body.id)
        if record is not None:
            if record.user_id != owner:
                raise ResourceError(ResourceErrorCode.NOT_FOUND)
            if record.deleted_at is not None:
                raise ResourceError(ResourceErrorCode.CREATION_CONFLICT)
            for field, value in body.model_dump().items():
                if getattr(record, field) != value:
                    raise ResourceError(ResourceErrorCode.CREATION_CONFLICT)
        return record

    def create_person(self, actor: AuthenticatedActor, body: PersonCreateRequest) -> PersonResponse:
        with self._transaction(actor) as db:
            record = self._existing(db, Person, actor.user_id, body)
            if record is None:
                record = records.create_person(
                    db, actor.user_id, body.display_name, resource_id=body.id
                )
            return PersonResponse.model_validate(record)

    def create_relationship(
        self, actor: AuthenticatedActor, body: RelationshipCreateRequest
    ) -> RelationshipResponse:
        with self._transaction(actor) as db:
            if records.get_person(db, actor.user_id, body.person_id) is None:
                raise ResourceError(ResourceErrorCode.NOT_FOUND)
            record = self._existing(db, Relationship, actor.user_id, body)
            if record is None:
                record = records.create_relationship(
                    db,
                    actor.user_id,
                    body.person_id,
                    body.relationship_type,
                    body.status,
                    resource_id=body.id,
                )
            return RelationshipResponse.model_validate(record)

    def create_conversation(
        self, actor: AuthenticatedActor, body: ConversationCreateRequest
    ) -> ConversationResponse:
        with self._transaction(actor) as db:
            if body.relationship_id is not None:
                if records.get_relationship(db, actor.user_id, body.relationship_id) is None:
                    raise ResourceError(ResourceErrorCode.NOT_FOUND)
            record = self._existing(db, Conversation, actor.user_id, body)
            if record is None:
                record = records.create_conversation(
                    db, actor.user_id, body.relationship_id, resource_id=body.id
                )
            return ConversationResponse.model_validate(record)

    def get_person(self, actor: AuthenticatedActor, resource_id: UUID) -> PersonResponse:
        with self._transaction(actor) as db:
            record = records.get_person(db, actor.user_id, resource_id)
            if record is None:
                raise ResourceError(ResourceErrorCode.NOT_FOUND)
            return PersonResponse.model_validate(record)

    def get_relationship(
        self, actor: AuthenticatedActor, resource_id: UUID
    ) -> RelationshipResponse:
        with self._transaction(actor) as db:
            record = records.get_relationship(db, actor.user_id, resource_id)
            if record is None:
                raise ResourceError(ResourceErrorCode.NOT_FOUND)
            return RelationshipResponse.model_validate(record)

    def get_conversation(
        self, actor: AuthenticatedActor, resource_id: UUID
    ) -> ConversationResponse:
        with self._transaction(actor) as db:
            record = records.get_conversation(db, actor.user_id, resource_id)
            if record is None:
                raise ResourceError(ResourceErrorCode.NOT_FOUND)
            return ConversationResponse.model_validate(record)

    def list_persons(self, actor: AuthenticatedActor, page: PageRequest) -> PersonPage:
        with self._transaction(actor) as db:
            context = _context(actor.user_id, "persons")
            rows = resources.resource_page(
                db, Person, actor.user_id, _decode_cursor(page.cursor, context), page.limit
            )
            return PersonPage(
                items=[PersonResponse.model_validate(row) for row in rows[: page.limit]],
                next_cursor=_next_cursor(rows, page.limit, context),
            )

    def list_relationships(self, actor: AuthenticatedActor, page: PageRequest) -> RelationshipPage:
        with self._transaction(actor) as db:
            context = _context(actor.user_id, "relationships")
            rows = resources.resource_page(
                db, Relationship, actor.user_id, _decode_cursor(page.cursor, context), page.limit
            )
            return RelationshipPage(
                items=[RelationshipResponse.model_validate(row) for row in rows[: page.limit]],
                next_cursor=_next_cursor(rows, page.limit, context),
            )

    def list_conversations(self, actor: AuthenticatedActor, page: PageRequest) -> ConversationPage:
        with self._transaction(actor) as db:
            context = _context(actor.user_id, "conversations")
            rows = resources.resource_page(
                db, Conversation, actor.user_id, _decode_cursor(page.cursor, context), page.limit
            )
            return ConversationPage(
                items=[ConversationResponse.model_validate(row) for row in rows[: page.limit]],
                next_cursor=_next_cursor(rows, page.limit, context),
            )

    def list_datasets(
        self, actor: AuthenticatedActor, relationship_id: UUID, page: PageRequest
    ) -> DatasetPage:
        """Canonical imported Jobs only; ready duplicates are never deletion IDs."""
        with self._transaction(actor) as db:
            if records.get_relationship(db, actor.user_id, relationship_id) is None:
                raise ResourceError(ResourceErrorCode.NOT_FOUND)
            context = _context(actor.user_id, "datasets", relationship_id)
            position = _decode_cursor(page.cursor, context)
            job = ChatImportJob
            query = select(job).where(
                job.owner_user_id == actor.user_id,
                job.bound_relationship_id == relationship_id,
                job.status == "imported",
            )
            if position is not None:
                query = query.where(tuple_(job.created_at, job.id) > position)
            rows = list(db.scalars(query.order_by(job.created_at, job.id).limit(page.limit + 1)))
            counts = dict(
                db.execute(
                    select(RelationshipMessage.import_job_id, func.count())
                    .where(
                        RelationshipMessage.owner_user_id == actor.user_id,
                        RelationshipMessage.relationship_id == relationship_id,
                        RelationshipMessage.import_job_id.in_(
                            [row.id for row in rows[: page.limit]]
                        ),
                    )
                    .group_by(RelationshipMessage.import_job_id)
                ).all()
            )
            return DatasetPage(
                items=[
                    DatasetSummary(
                        dataset_job_id=row.id,
                        relationship_id=relationship_id,
                        source_format=row.source_format,
                        parser_version=row.parser_version,
                        source_timezone=row.source_timezone,
                        first_timestamp_utc=row.first_timestamp_utc,
                        last_timestamp_utc=row.last_timestamp_utc,
                        imported_message_count=row.imported_message_count,
                        current_message_count=counts.get(row.id, 0),
                        ignored_message_count=row.ignored_message_count,
                        system_message_count=row.system_message_count,
                        imported_at=row.imported_at,
                        deleted_at=row.deleted_at,
                        deletable=row.deleted_at is None,
                    )
                    for row in rows[: page.limit]
                ],
                next_cursor=_next_cursor(rows, page.limit, context),
            )

    def list_agent_messages(
        self, actor: AuthenticatedActor, conversation_id: UUID, page: PageRequest
    ) -> AgentMessagePage:
        with self._transaction(actor) as db:
            context = _context(actor.user_id, "agent_messages", conversation_id)
            if records.get_conversation(db, actor.user_id, conversation_id) is None:
                raise ResourceError(ResourceErrorCode.NOT_FOUND)
            rows = resources.message_page(
                db, actor.user_id, conversation_id, _decode_cursor(page.cursor, context), page.limit
            )
            return AgentMessagePage(
                items=[
                    AgentMessagePublicResponse.model_validate(row) for row in rows[: page.limit]
                ],
                next_cursor=_next_cursor(rows, page.limit, context),
            )
