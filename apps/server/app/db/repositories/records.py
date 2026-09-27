"""Persistence operations used by services; callers own the transaction."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AgentRun, Conversation, Message, Person, Relationship, User


def create_user(db: Session) -> User:
    record = User()
    db.add(record)
    db.flush()
    return record


def create_person(db: Session, user_id: UUID, display_name: str) -> Person:
    record = Person(user_id=user_id, display_name=display_name)
    db.add(record)
    db.flush()
    return record


def get_person(db: Session, user_id: UUID, person_id: UUID) -> Person | None:
    return db.scalar(select(Person).where(Person.user_id == user_id, Person.id == person_id))


def create_relationship(
    db: Session, user_id: UUID, person_id: UUID, relationship_type: str, status: str
) -> Relationship:
    record = Relationship(
        user_id=user_id, person_id=person_id, relationship_type=relationship_type, status=status
    )
    db.add(record)
    db.flush()
    return record


def get_relationship(db: Session, user_id: UUID, relationship_id: UUID) -> Relationship | None:
    return db.scalar(
        select(Relationship).where(
            Relationship.user_id == user_id, Relationship.id == relationship_id
        )
    )


def create_conversation(
    db: Session, user_id: UUID, relationship_id: UUID | None = None
) -> Conversation:
    record = Conversation(user_id=user_id, relationship_id=relationship_id)
    db.add(record)
    db.flush()
    return record


def get_conversation(db: Session, user_id: UUID, conversation_id: UUID) -> Conversation | None:
    return db.scalar(
        select(Conversation).where(
            Conversation.user_id == user_id, Conversation.id == conversation_id
        )
    )


def list_conversations(db: Session, user_id: UUID) -> list[Conversation]:
    return list(
        db.scalars(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.created_at, Conversation.id)
        )
    )


def delete_conversation(db: Session, user_id: UUID, conversation_id: UUID) -> bool:
    record = get_conversation(db, user_id, conversation_id)
    if record is None:
        return False
    db.delete(record)
    db.flush()
    return True


def create_message(
    db: Session,
    user_id: UUID,
    conversation_id: UUID,
    role: str,
    content: str,
    speaker: str | None = None,
) -> Message | None:
    if get_conversation(db, user_id, conversation_id) is None:
        return None
    record = Message(conversation_id=conversation_id, role=role, content=content, speaker=speaker)
    db.add(record)
    db.flush()
    return record


def list_messages(db: Session, user_id: UUID, conversation_id: UUID) -> list[Message]:
    if get_conversation(db, user_id, conversation_id) is None:
        return []
    return list(
        db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at, Message.id)
        )
    )


def create_agent_run(db: Session, user_id: UUID, conversation_id: UUID) -> AgentRun:
    record = AgentRun(user_id=user_id, conversation_id=conversation_id, status="pending")
    db.add(record)
    db.flush()
    return record
