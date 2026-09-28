"""Persist scoped Agent operation keys and replayable result metadata.

Revision ID: 20260928_02
Revises: 20260928_01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260928_02"
down_revision: str | None = "20260928_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("agent_runs", sa.Column("operation_key", sa.String(128)))
    op.add_column("agent_runs", sa.Column("request_fingerprint", sa.String(64)))
    op.add_column("agent_runs", sa.Column("user_message_id", sa.Uuid(as_uuid=True)))
    op.add_column("agent_runs", sa.Column("assistant_message_id", sa.Uuid(as_uuid=True)))
    op.add_column("agent_runs", sa.Column("memory_status", sa.String(40)))
    op.add_column("agent_runs", sa.Column("result_warnings", JSONB()))
    op.create_foreign_key(
        "fk_agent_runs_user_message_id_messages",
        "agent_runs",
        "messages",
        ["user_message_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_agent_runs_assistant_message_id_messages",
        "agent_runs",
        "messages",
        ["assistant_message_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_agent_runs_operation_fingerprint_pair",
        "agent_runs",
        "(operation_key IS NULL AND request_fingerprint IS NULL) OR "
        "(operation_key IS NOT NULL AND request_fingerprint IS NOT NULL)",
    )
    op.create_unique_constraint(
        "uq_agent_runs_operation",
        "agent_runs",
        ["user_id", "conversation_id", "operation_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_agent_runs_operation", "agent_runs", type_="unique")
    op.drop_constraint("ck_agent_runs_operation_fingerprint_pair", "agent_runs", type_="check")
    op.drop_constraint(
        "fk_agent_runs_assistant_message_id_messages", "agent_runs", type_="foreignkey"
    )
    op.drop_constraint("fk_agent_runs_user_message_id_messages", "agent_runs", type_="foreignkey")
    op.drop_column("agent_runs", "result_warnings")
    op.drop_column("agent_runs", "memory_status")
    op.drop_column("agent_runs", "assistant_message_id")
    op.drop_column("agent_runs", "user_message_id")
    op.drop_column("agent_runs", "request_fingerprint")
    op.drop_column("agent_runs", "operation_key")
