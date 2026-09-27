"""Add owner and person scoped long-term memory.

Revision ID: 20260927_02
Revises: 20260927_01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260927_02"
down_revision: str | None = "20260927_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def common_columns() -> list[sa.Column]:
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
    op.create_unique_constraint(
        "uq_relationships_user_id_id_person_id", "relationships", ["user_id", "id", "person_id"]
    )
    op.create_table(
        "memory_controls",
        *common_columns(),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("consent_enabled", sa.Boolean(), nullable=False),
        sa.Column("paused", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_memory_controls_user_id"),
    )
    op.create_table(
        "memory_records",
        *common_columns(),
        sa.Column("owner_user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("subject_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("person_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("relationship_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("content", sa.String(200), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("evidence", sa.String(100), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("first_run_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["owner_user_id", "person_id"], ["persons.user_id", "persons.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id", "relationship_id", "person_id"],
            ["relationships.user_id", "relationships.id", "relationships.person_id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "owner_user_id",
            "subject_id",
            "type",
            "content_hash",
            name="uq_memory_records_owner_user_id",
        ),
        sa.CheckConstraint(
            "type IN ('user', 'object', 'relationship')", name="ck_memory_records_type_valid"
        ),
        sa.CheckConstraint(
            "(type = 'user' AND person_id IS NULL AND relationship_id IS NULL "
            "AND subject_id = owner_user_id) OR (type <> 'user' AND person_id IS NOT NULL "
            "AND relationship_id IS NOT NULL AND subject_id = person_id)",
            name="ck_memory_records_scope_valid",
        ),
    )
    op.create_index("ix_memory_records_owner_user_id", "memory_records", ["owner_user_id"])
    op.create_index("ix_memory_records_subject_id", "memory_records", ["subject_id"])


def downgrade() -> None:
    op.drop_table("memory_records")
    op.drop_table("memory_controls")
    op.drop_constraint("uq_relationships_user_id_id_person_id", "relationships", type_="unique")
