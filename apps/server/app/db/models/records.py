"""Owner-scoped persistence records; no authentication or Agent execution here."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, RecordMixin


class User(RecordMixin, Base):
    __tablename__ = "users"


class Person(RecordMixin, Base):
    __tablename__ = "persons"
    __table_args__ = (UniqueConstraint("user_id", "id"),)

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)


class Relationship(RecordMixin, Base):
    __tablename__ = "relationships"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "person_id"], ["persons.user_id", "persons.id"], ondelete="RESTRICT"
        ),
        UniqueConstraint("user_id", "id"),
        UniqueConstraint(
            "user_id", "id", "person_id", name="uq_relationships_user_id_id_person_id"
        ),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    person_id: Mapped[UUID] = mapped_column(index=True)
    relationship_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)


class Conversation(RecordMixin, Base):
    __tablename__ = "conversations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "relationship_id"],
            ["relationships.user_id", "relationships.id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("user_id", "id"),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    relationship_id: Mapped[UUID | None] = mapped_column(nullable=True)


class Message(RecordMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (CheckConstraint("role IN ('user', 'assistant', 'tool')", name="role_valid"),)

    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    speaker: Mapped[str | None] = mapped_column(String(120), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)


class AgentRun(RecordMixin, Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "conversation_id"],
            ["conversations.user_id", "conversations.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')", name="status_valid"
        ),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    conversation_id: Mapped[UUID] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(40), nullable=True)


class MemoryControlRow(RecordMixin, Base):
    __tablename__ = "memory_controls"
    __table_args__ = (UniqueConstraint("user_id"),)

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    consent_enabled: Mapped[bool] = mapped_column(nullable=False, default=False)
    paused: Mapped[bool] = mapped_column(nullable=False, default=False)


class MemoryRecordRow(RecordMixin, Base):
    __tablename__ = "memory_records"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_user_id", "person_id"], ["persons.user_id", "persons.id"], ondelete="RESTRICT"
        ),
        ForeignKeyConstraint(
            ["owner_user_id", "relationship_id", "person_id"],
            ["relationships.user_id", "relationships.id", "relationships.person_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("owner_user_id", "subject_id", "type", "content_hash"),
        UniqueConstraint("owner_user_id", "id", name="uq_memory_records_owner_id"),
        CheckConstraint("type IN ('user', 'object', 'relationship')", name="type_valid"),
        CheckConstraint(
            "(type = 'user' AND person_id IS NULL AND relationship_id IS NULL "
            "AND subject_id = owner_user_id) OR (type <> 'user' AND person_id IS NOT NULL "
            "AND relationship_id IS NOT NULL AND subject_id = person_id)",
            name="scope_valid",
        ),
    )

    owner_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    subject_id: Mapped[UUID] = mapped_column(index=True)
    person_id: Mapped[UUID | None] = mapped_column(nullable=True)
    relationship_id: Mapped[UUID | None] = mapped_column(nullable=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(String(200), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    evidence: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    first_run_id: Mapped[UUID] = mapped_column(nullable=False)


class MemoryOperationRow(RecordMixin, Base):
    """At most twenty owner-scoped, reversible memory insert operations."""

    __tablename__ = "memory_operations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_user_id", "record_id"],
            ["memory_records.owner_user_id", "memory_records.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("record_id"),
    )

    owner_user_id: Mapped[UUID] = mapped_column(index=True)
    record_id: Mapped[UUID] = mapped_column(nullable=False)
