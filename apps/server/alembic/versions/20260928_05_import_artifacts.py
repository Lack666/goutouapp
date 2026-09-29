"""Bind immutable temporary upload metadata to owner-scoped import jobs.

Revision ID: 20260928_05
Revises: 20260928_04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260928_05"
down_revision: str | None = "20260928_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_import_artifacts",
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
        sa.Column(
            "owner_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("storage_key", sa.String(32), nullable=False),
        sa.Column("source_format", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.UniqueConstraint("owner_user_id", "id"),
        sa.UniqueConstraint("storage_key"),
        sa.CheckConstraint("size_bytes > 0", name="ck_chat_import_artifacts_positive_size"),
        sa.CheckConstraint(
            "state IN ('active', 'deleted', 'expired')", name="ck_chat_import_artifacts_state_valid"
        ),
    )
    op.create_index(
        "ix_chat_import_artifacts_owner_user_id", "chat_import_artifacts", ["owner_user_id"]
    )
    op.add_column(
        "chat_import_jobs", sa.Column("artifact_id", sa.Uuid(as_uuid=True), nullable=True)
    )
    op.create_unique_constraint(
        "uq_chat_import_jobs_artifact_id", "chat_import_jobs", ["artifact_id"]
    )
    op.create_foreign_key(
        "fk_chat_import_jobs_owner_artifact",
        "chat_import_jobs",
        "chat_import_artifacts",
        ["owner_user_id", "artifact_id"],
        ["owner_user_id", "id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_chat_import_jobs_owner_artifact", "chat_import_jobs", type_="foreignkey")
    op.drop_constraint("uq_chat_import_jobs_artifact_id", "chat_import_jobs", type_="unique")
    op.drop_column("chat_import_jobs", "artifact_id")
    op.drop_table("chat_import_artifacts")
