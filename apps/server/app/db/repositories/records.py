"""Persistence operations used by services; callers own the transaction."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent.contracts import AgentRunStatus
from app.db.models import AgentRun, Conversation, Message, Person, Relationship, User


def create_user(db: Session) -> User:
    record = User()
    db.add(record)
    db.flush()
    return record


def get_user(db: Session, user_id: UUID) -> User | None:
    return db.get(User, user_id)


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


def get_conversation_by_id(db: Session, conversation_id: UUID) -> Conversation | None:
    """Only for distinguishing missing from forbidden; never return its content to callers."""
    return db.get(Conversation, conversation_id)


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
    record = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        speaker=speaker,
        created_at=datetime.now(UTC),
    )
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


def recent_messages(db: Session, user_id: UUID, conversation_id: UUID, limit: int) -> list[Message]:
    if get_conversation(db, user_id, conversation_id) is None:
        return []
    rows = list(
        db.scalars(
            select(Message)
            .where(
                Message.conversation_id == conversation_id, Message.role.in_(("user", "assistant"))
            )
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
        )
    )
    return list(reversed(rows))


def create_agent_run(db: Session, user_id: UUID, conversation_id: UUID) -> AgentRun:
    record = AgentRun(user_id=user_id, conversation_id=conversation_id, status="pending")
    db.add(record)
    db.flush()
    return record


def start_agent_run(db: Session, user_id: UUID, conversation_id: UUID, run_id: UUID) -> AgentRun:
    record = AgentRun(
        id=run_id,
        user_id=user_id,
        conversation_id=conversation_id,
        status=AgentRunStatus.PENDING,
    )
    db.add(record)
    db.flush()
    record.status = AgentRunStatus.RUNNING
    record.started_at = datetime.now(UTC)
    db.flush()
    return record


def claim_conversation_run_slot(db: Session, conversation_id: UUID) -> bool:
    """Serialize run starts across workers, then inspect committed active runs."""
    first = int.from_bytes(conversation_id.bytes[:4], "big", signed=True)
    second = int.from_bytes(conversation_id.bytes[4:8], "big", signed=True)
    db.execute(select(func.pg_advisory_xact_lock(first, second)))
    active = db.scalar(
        select(AgentRun.id)
        .where(
            AgentRun.conversation_id == conversation_id,
            AgentRun.status == AgentRunStatus.RUNNING,
        )
        .limit(1)
    )
    return active is None


def finish_agent_run(
    db: Session,
    user_id: UUID,
    conversation_id: UUID,
    run_id: UUID,
    status: AgentRunStatus,
    failure_code: str | None = None,
) -> bool:
    record = db.scalar(
        select(AgentRun).where(
            AgentRun.id == run_id,
            AgentRun.user_id == user_id,
            AgentRun.conversation_id == conversation_id,
        )
    )
    if record is None or record.status != AgentRunStatus.RUNNING:
        return False
    record.status = status
    record.completed_at = datetime.now(UTC)
    record.failure_code = failure_code
    db.flush()
    return True
