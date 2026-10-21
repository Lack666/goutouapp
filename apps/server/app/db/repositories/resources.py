"""Bounded owner queries and cross-worker creation locks; never commit here."""

from datetime import datetime
from hashlib import sha256
from uuid import UUID

from sqlalchemy import func, select, tuple_
from sqlalchemy.orm import Session

from app.db.models import Conversation, Message, Person, Relationship

Position = tuple[datetime, UUID]


def lock_creation(db: Session, domain: str, resource_id: UUID) -> None:
    # Single-bigint advisory keys are separate from Agent's two-int run locks.
    raw = sha256(f"resource-create-v1:{domain}:{resource_id}".encode()).digest()[:8]
    db.execute(select(func.pg_advisory_xact_lock(int.from_bytes(raw, "big", signed=True))))


def resource_page[Resource: (Person, Relationship, Conversation)](
    db: Session, model: type[Resource], owner: UUID, position: Position | None, limit: int
) -> list[Resource]:
    query = select(model).where(model.user_id == owner)
    query = query.where(model.deleted_at.is_(None))
    if position is not None:
        query = query.where(tuple_(model.created_at, model.id) > position)
    return list(db.scalars(query.order_by(model.created_at, model.id).limit(limit + 1)))


def message_page(
    db: Session, owner: UUID, conversation_id: UUID, position: Position | None, limit: int
) -> list[Message]:
    query = (
        select(Message)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(
            Conversation.user_id == owner,
            Conversation.id == conversation_id,
            Conversation.deleted_at.is_(None),
            Message.role.in_(("user", "assistant")),
        )
    )
    if position is not None:
        query = query.where(tuple_(Message.created_at, Message.id) > position)
    return list(db.scalars(query.order_by(Message.created_at, Message.id).limit(limit + 1)))
