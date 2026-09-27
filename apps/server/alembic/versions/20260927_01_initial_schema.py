"""Create the six Phase 2B owner-scoped tables.

Revision ID: 20260927_01
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260927_01"
down_revision: str | None = None
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
    op.create_table("users", *common_columns())
    op.create_table(
        "persons",
        *common_columns(),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("user_id", "id", name="uq_persons_user_id"),
    )
    op.create_index("ix_persons_user_id", "persons", ["user_id"])
    op.create_table(
        "relationships",
        *common_columns(),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("person_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("relationship_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["user_id", "person_id"], ["persons.user_id", "persons.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("user_id", "id", name="uq_relationships_user_id"),
    )
    op.create_index("ix_relationships_user_id", "relationships", ["user_id"])
    op.create_index("ix_relationships_person_id", "relationships", ["person_id"])
    op.create_table(
        "conversations",
        *common_columns(),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("relationship_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["user_id", "relationship_id"],
            ["relationships.user_id", "relationships.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("user_id", "id", name="uq_conversations_user_id"),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_table(
        "messages",
        *common_columns(),
        sa.Column("conversation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("speaker", sa.String(120), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.CheckConstraint("role IN ('user', 'assistant', 'tool')", name="ck_messages_role_valid"),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_table(
        "agent_runs",
        *common_columns(),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("conversation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["user_id", "conversation_id"],
            ["conversations.user_id", "conversations.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_agent_runs_status_valid",
        ),
    )
    op.create_index("ix_agent_runs_user_id", "agent_runs", ["user_id"])
    op.create_index("ix_agent_runs_conversation_id", "agent_runs", ["conversation_id"])


def downgrade() -> None:
    op.drop_table("agent_runs")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("relationships")
    op.drop_table("persons")
    op.drop_table("users")
