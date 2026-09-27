"""Add bounded owner-scoped memory insert undo history.

Revision ID: 20260927_03
Revises: 20260927_02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260927_03"
down_revision: str | None = "20260927_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_memory_records_owner_id", "memory_records", ["owner_user_id", "id"]
    )
    op.create_table(
        "memory_operations",
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
        sa.Column("record_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_user_id", "record_id"],
            ["memory_records.owner_user_id", "memory_records.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("record_id", name="uq_memory_operations_record_id"),
    )
    op.create_index("ix_memory_operations_owner_user_id", "memory_operations", ["owner_user_id"])


def downgrade() -> None:
    op.drop_table("memory_operations")
    op.drop_constraint("uq_memory_records_owner_id", "memory_records", type_="unique")
