"""Owner-scoped persistence records; no authentication or Agent execution here."""

from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
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
