"""Durable import workflow metadata, separate from product conversations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, RecordMixin


class ChatImportJob(RecordMixin, Base):
    __tablename__ = "chat_import_jobs"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "id"),
        UniqueConstraint("artifact_id"),
        ForeignKeyConstraint(
            ["owner_user_id", "artifact_id"],
            ["chat_import_artifacts.owner_user_id", "chat_import_artifacts.id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "owner_user_id",
            "id",
            "bound_relationship_id",
            name="uq_import_job_owner_id_relationship",
        ),
        Index(
            "uq_import_dataset_scope",
            "owner_user_id",
            "bound_relationship_id",
            "transcript_fingerprint",
            unique=True,
            postgresql_where=text("status = 'imported'"),
        ),
        ForeignKeyConstraint(
            ["owner_user_id", "bound_relationship_id"],
            ["relationships.user_id", "relationships.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('awaiting_binding', 'ready', 'importing', 'imported', 'cancelled')",
            name="status_valid",
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
    artifact_id: Mapped[UUID | None] = mapped_column(nullable=True)
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
    imported_message_count: Mapped[int | None] = mapped_column(nullable=True)
    ignored_message_count: Mapped[int | None] = mapped_column(nullable=True)
    system_message_count: Mapped[int | None] = mapped_column(nullable=True)
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ChatImportArtifact(RecordMixin, Base):
    __tablename__ = "chat_import_artifacts"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "id"),
        UniqueConstraint("storage_key"),
        CheckConstraint("size_bytes > 0", name="positive_size"),
        CheckConstraint("state IN ('active', 'deleted', 'expired')", name="state_valid"),
    )

    owner_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    storage_key: Mapped[str] = mapped_column(String(32), nullable=False)
    source_format: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)


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


class RelationshipMessage(RecordMixin, Base):
    """External transcript occurrence; never an Agent Conversation Message."""

    __tablename__ = "relationship_messages"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_user_id", "import_job_id", "relationship_id"],
            [
                "chat_import_jobs.owner_user_id",
                "chat_import_jobs.id",
                "chat_import_jobs.bound_relationship_id",
            ],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["owner_user_id", "relationship_id", "person_id"],
            ["relationships.user_id", "relationships.id", "relationships.person_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["import_job_id", "raw_speaker_label"],
            ["chat_import_speakers.job_id", "chat_import_speakers.raw_speaker_label"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("import_job_id", "source_index"),
        CheckConstraint("source_index > 0", name="positive_source_index"),
        CheckConstraint("sender_kind IN ('self', 'person', 'system')", name="sender_kind_valid"),
        CheckConstraint(
            "(sender_kind = 'person' AND person_id IS NOT NULL) OR "
            "(sender_kind <> 'person' AND person_id IS NULL)",
            name="sender_person_valid",
        ),
    )

    owner_user_id: Mapped[UUID] = mapped_column(index=True)
    relationship_id: Mapped[UUID] = mapped_column(index=True)
    import_job_id: Mapped[UUID] = mapped_column(index=True)
    source_index: Mapped[int] = mapped_column(nullable=False)
    message_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_speaker_label: Mapped[str] = mapped_column(String(120), nullable=False)
    sender_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    person_id: Mapped[UUID | None] = mapped_column(nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(16), nullable=False)
    timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    original_timestamp: Mapped[str] = mapped_column(String(19), nullable=False)
    source_timezone: Mapped[str] = mapped_column(String(100), nullable=False)
    source_line_start: Mapped[int] = mapped_column(nullable=False)
    source_line_end: Mapped[int] = mapped_column(nullable=False)
