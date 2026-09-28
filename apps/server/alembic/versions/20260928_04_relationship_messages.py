"""Separate relationship transcript occurrences and durable import receipt.

Revision ID: 20260928_04
Revises: 20260928_03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260928_04"
down_revision: str | None = "20260928_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_chat_import_jobs_status_valid", "chat_import_jobs", type_="check")
    op.create_check_constraint(
        "ck_chat_import_jobs_status_valid",
        "chat_import_jobs",
        "status IN ('awaiting_binding', 'ready', 'importing', 'imported', 'cancelled')",
    )
    for name in ("imported_message_count", "ignored_message_count", "system_message_count"):
        op.add_column("chat_import_jobs", sa.Column(name, sa.Integer(), nullable=True))
    op.add_column("chat_import_jobs", sa.Column("imported_at", sa.DateTime(timezone=True)))
    op.create_unique_constraint(
        "uq_import_job_owner_id_relationship",
        "chat_import_jobs",
        ["owner_user_id", "id", "bound_relationship_id"],
    )
    op.create_index(
        "uq_import_dataset_scope",
        "chat_import_jobs",
        ["owner_user_id", "bound_relationship_id", "transcript_fingerprint"],
        unique=True,
        postgresql_where=sa.text("status = 'imported'"),
    )
    op.create_table(
        "relationship_messages",
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
        sa.Column("owner_user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("relationship_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("import_job_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("source_index", sa.Integer(), nullable=False),
        sa.Column("message_fingerprint", sa.String(64), nullable=False),
        sa.Column("raw_speaker_label", sa.String(120), nullable=False),
        sa.Column("sender_kind", sa.String(16), nullable=False),
        sa.Column("person_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(16), nullable=False),
        sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("original_timestamp", sa.String(19), nullable=False),
        sa.Column("source_timezone", sa.String(100), nullable=False),
        sa.Column("source_line_start", sa.Integer(), nullable=False),
        sa.Column("source_line_end", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_user_id", "import_job_id", "relationship_id"],
            [
                "chat_import_jobs.owner_user_id",
                "chat_import_jobs.id",
                "chat_import_jobs.bound_relationship_id",
            ],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id", "relationship_id", "person_id"],
            ["relationships.user_id", "relationships.id", "relationships.person_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["import_job_id", "raw_speaker_label"],
            ["chat_import_speakers.job_id", "chat_import_speakers.raw_speaker_label"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("import_job_id", "source_index"),
        sa.CheckConstraint(
            "source_index > 0", name="ck_relationship_messages_positive_source_index"
        ),
        sa.CheckConstraint(
            "sender_kind IN ('self', 'person', 'system')",
            name="ck_relationship_messages_sender_kind_valid",
        ),
        sa.CheckConstraint(
            "(sender_kind = 'person' AND person_id IS NOT NULL) OR "
            "(sender_kind <> 'person' AND person_id IS NULL)",
            name="ck_relationship_messages_sender_person_valid",
        ),
    )
    for name in ("owner_user_id", "relationship_id", "import_job_id"):
        op.create_index(f"ix_relationship_messages_{name}", "relationship_messages", [name])


def downgrade() -> None:
    op.drop_table("relationship_messages")
    op.drop_index("uq_import_dataset_scope", table_name="chat_import_jobs")
    op.drop_constraint("uq_import_job_owner_id_relationship", "chat_import_jobs", type_="unique")
    op.drop_column("chat_import_jobs", "imported_at")
    for name in ("system_message_count", "ignored_message_count", "imported_message_count"):
        op.drop_column("chat_import_jobs", name)
    op.drop_constraint("ck_chat_import_jobs_status_valid", "chat_import_jobs", type_="check")
    op.create_check_constraint(
        "ck_chat_import_jobs_status_valid",
        "chat_import_jobs",
        "status IN ('awaiting_binding', 'ready', 'cancelled')",
    )
