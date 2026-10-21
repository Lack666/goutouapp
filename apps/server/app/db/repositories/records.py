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
    # Shared owner barrier precedes every domain lock. Full-scope erasure takes
    # NO KEY UPDATE on this row and rechecks the snapshot after prior writes commit.
    return db.scalar(
        select(User).where(User.id == user_id, User.deleted_at.is_(None)).with_for_update(read=True)
    )


def create_person(
    db: Session, user_id: UUID, display_name: str, *, resource_id: UUID | None = None
) -> Person:
    record = Person(user_id=user_id, display_name=display_name)
    if resource_id is not None:
        record.id = resource_id
    db.add(record)
    db.flush()
    return record


def get_person(db: Session, user_id: UUID, person_id: UUID) -> Person | None:
    return db.scalar(
        select(Person).where(
            Person.user_id == user_id, Person.id == person_id, Person.deleted_at.is_(None)
        )
    )


def create_relationship(
    db: Session,
    user_id: UUID,
    person_id: UUID,
    relationship_type: str,
    status: str,
    *,
    resource_id: UUID | None = None,
) -> Relationship:
    record = Relationship(
        user_id=user_id, person_id=person_id, relationship_type=relationship_type, status=status
    )
    if resource_id is not None:
        record.id = resource_id
    db.add(record)
    db.flush()
    return record


def get_relationship(db: Session, user_id: UUID, relationship_id: UUID) -> Relationship | None:
    return db.scalar(
        select(Relationship).where(
            Relationship.user_id == user_id,
            Relationship.id == relationship_id,
            Relationship.deleted_at.is_(None),
        )
    )


def create_conversation(
    db: Session,
    user_id: UUID,
    relationship_id: UUID | None = None,
    *,
    resource_id: UUID | None = None,
) -> Conversation:
    record = Conversation(user_id=user_id, relationship_id=relationship_id)
    if resource_id is not None:
        record.id = resource_id
    db.add(record)
    db.flush()
    return record


def get_conversation(db: Session, user_id: UUID, conversation_id: UUID) -> Conversation | None:
    return db.scalar(
        select(Conversation).where(
            Conversation.user_id == user_id,
            Conversation.id == conversation_id,
            Conversation.deleted_at.is_(None),
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
            .where(Conversation.deleted_at.is_(None))
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


def start_agent_run(
    db: Session,
    user_id: UUID,
    conversation_id: UUID,
    run_id: UUID,
    *,
    operation_key: str | None = None,
    request_fingerprint: str | None = None,
    user_message_id: UUID | None = None,
) -> AgentRun:
    record = AgentRun(
        id=run_id,
        user_id=user_id,
        conversation_id=conversation_id,
        status=AgentRunStatus.PENDING,
        operation_key=operation_key,
        request_fingerprint=request_fingerprint,
        user_message_id=user_message_id,
    )
    db.add(record)
    db.flush()
    record.status = AgentRunStatus.RUNNING
    record.started_at = datetime.now(UTC)
    db.flush()
    return record


def lock_conversation_run_slot(db: Session, conversation_id: UUID) -> None:
    """Serialize operation lookup and run starts across server processes."""
    first = int.from_bytes(conversation_id.bytes[:4], "big", signed=True)
    second = int.from_bytes(conversation_id.bytes[4:8], "big", signed=True)
    db.execute(select(func.pg_advisory_xact_lock(first, second)))


def get_agent_operation(
    db: Session, user_id: UUID, conversation_id: UUID, operation_key: str
) -> AgentRun | None:
    return db.scalar(
        select(AgentRun).where(
            AgentRun.user_id == user_id,
            AgentRun.conversation_id == conversation_id,
            AgentRun.operation_key == operation_key,
        )
    )


def claim_conversation_run_slot(db: Session, conversation_id: UUID) -> bool:
    """Call after lock_conversation_run_slot within the same transaction."""
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
    *,
    assistant_message_id: UUID | None = None,
    memory_status: str | None = None,
    result_warnings: list[str] | None = None,
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
    record.assistant_message_id = assistant_message_id
    record.memory_status = memory_status
    record.result_warnings = result_warnings
    db.flush()
    return True


def finalize_agent_run_result(
    db: Session,
    user_id: UUID,
    conversation_id: UUID,
    run_id: UUID,
    memory_status: str,
    warnings: list[str],
) -> bool:
    record = db.scalar(
        select(AgentRun).where(
            AgentRun.id == run_id,
            AgentRun.user_id == user_id,
            AgentRun.conversation_id == conversation_id,
        )
    )
    if record is None or record.status != AgentRunStatus.COMPLETED:
        return False
    if record.memory_status is None:
        record.memory_status = memory_status
        record.result_warnings = warnings
        db.flush()
    return True
