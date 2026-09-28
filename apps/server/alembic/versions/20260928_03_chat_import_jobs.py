"""Persist owner-scoped import jobs and explicit speaker bindings.

Revision ID: 20260928_03
Revises: 20260928_02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260928_03"
down_revision: str | None = "20260928_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _common() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "chat_import_jobs",
        *_common(),
        sa.Column(
            "owner_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("source_format", sa.String(64), nullable=False),
        sa.Column("parser_version", sa.String(20), nullable=False),
        sa.Column("schema_version", sa.String(20), nullable=False),
        sa.Column("source_timezone", sa.String(100), nullable=False),
        sa.Column("source_fingerprint", sa.String(64), nullable=False),
        sa.Column("transcript_fingerprint", sa.String(64), nullable=False),
        sa.Column("message_count", sa.Integer(), nullable=False),
        sa.Column("speaker_count", sa.Integer(), nullable=False),
        sa.Column("first_timestamp_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_timestamp_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("warning_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("issues_truncated", sa.Integer(), nullable=False),
        sa.Column("issue_code_samples", JSONB(), nullable=False),
        sa.Column("bound_relationship_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("binding_revision", sa.Integer(), nullable=False),
        sa.UniqueConstraint("owner_user_id", "id"),
        sa.ForeignKeyConstraint(
            ["owner_user_id", "bound_relationship_id"],
            ["relationships.user_id", "relationships.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "status IN ('awaiting_binding', 'ready', 'cancelled')",
            name="ck_chat_import_jobs_status_valid",
        ),
        sa.CheckConstraint(
            "message_count > 0 AND speaker_count > 0", name="ck_chat_import_jobs_positive_counts"
        ),
        sa.CheckConstraint(
            "warning_count >= 0 AND error_count >= 0 AND issues_truncated >= 0",
            name="ck_chat_import_jobs_issue_counts_valid",
        ),
    )
    op.create_index("ix_chat_import_jobs_owner_user_id", "chat_import_jobs", ["owner_user_id"])
    op.create_table(
        "chat_import_speakers",
        *_common(),
        sa.Column("owner_user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("job_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("raw_speaker_label", sa.String(120), nullable=False),
        sa.Column("source_order", sa.Integer(), nullable=False),
        sa.Column("message_count", sa.Integer(), nullable=False),
        sa.Column("binding_kind", sa.String(16), nullable=False),
        sa.Column("person_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["owner_user_id", "job_id"],
            ["chat_import_jobs.owner_user_id", "chat_import_jobs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id", "person_id"],
            ["persons.user_id", "persons.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("job_id", "raw_speaker_label"),
        sa.CheckConstraint("message_count > 0", name="ck_chat_import_speakers_positive_count"),
        sa.CheckConstraint(
            "binding_kind IN ('unbound', 'self', 'person', 'system', 'ignore')",
            name="ck_chat_import_speakers_binding_kind_valid",
        ),
        sa.CheckConstraint(
            "(binding_kind = 'person' AND person_id IS NOT NULL) OR "
            "(binding_kind <> 'person' AND person_id IS NULL)",
            name="ck_chat_import_speakers_person_binding_valid",
        ),
    )
    op.create_index(
        "ix_chat_import_speakers_owner_user_id", "chat_import_speakers", ["owner_user_id"]
    )
    op.create_index("ix_chat_import_speakers_job_id", "chat_import_speakers", ["job_id"])


def downgrade() -> None:
    op.drop_table("chat_import_speakers")
    op.drop_table("chat_import_jobs")
