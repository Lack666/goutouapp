"""Durable import workflow metadata, separate from product conversations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, RecordMixin


class ChatImportJob(RecordMixin, Base):
    __tablename__ = "chat_import_jobs"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "id"),
        ForeignKeyConstraint(
            ["owner_user_id", "bound_relationship_id"],
            ["relationships.user_id", "relationships.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('awaiting_binding', 'ready', 'cancelled')", name="status_valid"
        ),
        CheckConstraint("message_count > 0 AND speaker_count > 0", name="positive_counts"),
        CheckConstraint(
            "warning_count >= 0 AND error_count >= 0 AND issues_truncated >= 0",
            name="issue_counts_valid",
        ),
    )

    owner_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    source_format: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(20), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(20), nullable=False)
    source_timezone: Mapped[str] = mapped_column(String(100), nullable=False)
    source_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    transcript_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    message_count: Mapped[int] = mapped_column(nullable=False)
    speaker_count: Mapped[int] = mapped_column(nullable=False)
    first_timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    warning_count: Mapped[int] = mapped_column(nullable=False)
    error_count: Mapped[int] = mapped_column(nullable=False)
    issues_truncated: Mapped[int] = mapped_column(nullable=False)
    issue_code_samples: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    bound_relationship_id: Mapped[UUID | None] = mapped_column(nullable=True)
    binding_revision: Mapped[int] = mapped_column(nullable=False, default=0)


class ChatImportSpeaker(RecordMixin, Base):
    __tablename__ = "chat_import_speakers"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_user_id", "job_id"],
            ["chat_import_jobs.owner_user_id", "chat_import_jobs.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["owner_user_id", "person_id"],
            ["persons.user_id", "persons.id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("job_id", "raw_speaker_label"),
        CheckConstraint("message_count > 0", name="positive_count"),
        CheckConstraint(
            "binding_kind IN ('unbound', 'self', 'person', 'system', 'ignore')",
            name="binding_kind_valid",
        ),
        CheckConstraint(
            "(binding_kind = 'person' AND person_id IS NOT NULL) OR "
            "(binding_kind <> 'person' AND person_id IS NULL)",
            name="person_binding_valid",
        ),
    )

    owner_user_id: Mapped[UUID] = mapped_column(index=True)
    job_id: Mapped[UUID] = mapped_column(index=True)
    raw_speaker_label: Mapped[str] = mapped_column(String(120), nullable=False)
    source_order: Mapped[int] = mapped_column(nullable=False)
    message_count: Mapped[int] = mapped_column(nullable=False)
    binding_kind: Mapped[str] = mapped_column(String(16), nullable=False, default="unbound")
    person_id: Mapped[UUID | None] = mapped_column(nullable=True)
