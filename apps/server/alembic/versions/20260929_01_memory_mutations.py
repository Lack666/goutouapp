"""Persist owner-bound memory confirmations and idempotent mutation receipts.

Revision ID: 20260929_01
Revises: 20260928_05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260929_01"
down_revision: str | None = "20260928_05"
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
        sa.Column(
            "owner_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "memory_confirmations",
        *_common(),
        sa.Column("action", sa.String(24), nullable=False),
        sa.Column("target_id", sa.Uuid(as_uuid=True)),
        sa.Column("person_id", sa.Uuid(as_uuid=True)),
        sa.Column("relationship_id", sa.Uuid(as_uuid=True)),
        sa.Column("revoke_consent_after_delete", sa.Boolean(), nullable=False),
        sa.Column("expected_count", sa.Integer(), nullable=False),
        sa.Column("snapshot_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("expected_count >= 0", name="ck_memory_confirmations_nonnegative_count"),
        sa.CheckConstraint(
            "action IN ('delete_one', 'delete_person', 'delete_all')",
            name="ck_memory_confirmations_action_valid",
        ),
    )
    op.create_index(
        "ix_memory_confirmations_owner_user_id", "memory_confirmations", ["owner_user_id"]
    )
    op.create_table(
        "memory_mutations",
        *_common(),
        sa.Column("operation_key", sa.String(128), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("action", sa.String(24), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("affected_count", sa.Integer(), nullable=False),
        sa.Column("target_id", sa.Uuid(as_uuid=True)),
        sa.Column("person_id", sa.Uuid(as_uuid=True)),
        sa.Column("relationship_id", sa.Uuid(as_uuid=True)),
        sa.Column("undone_memory_id", sa.Uuid(as_uuid=True)),
        sa.Column("confirmation_id", sa.Uuid(as_uuid=True)),
        sa.Column("performed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "owner_user_id", "operation_key", name="uq_memory_mutations_owner_user_id"
        ),
        sa.CheckConstraint("affected_count >= 0", name="ck_memory_mutations_nonnegative_count"),
        sa.CheckConstraint(
            "action IN ('undo', 'delete_one', 'delete_person', 'delete_all')",
            name="ck_memory_mutations_action_valid",
        ),
        sa.CheckConstraint(
            "status IN ('undone', 'deleted')", name="ck_memory_mutations_status_valid"
        ),
    )
    op.create_index("ix_memory_mutations_owner_user_id", "memory_mutations", ["owner_user_id"])


def downgrade() -> None:
    op.drop_table("memory_mutations")
    op.drop_table("memory_confirmations")
