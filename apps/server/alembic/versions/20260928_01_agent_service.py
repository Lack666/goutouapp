"""Minimal persistent AgentRun lifecycle fields for Phase 4A.

Revision ID: 20260928_01
Revises: 20260927_03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260928_01"
down_revision: str | None = "20260927_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("agent_runs", sa.Column("started_at", sa.DateTime(timezone=True)))
    op.add_column("agent_runs", sa.Column("completed_at", sa.DateTime(timezone=True)))
    op.add_column("agent_runs", sa.Column("failure_code", sa.String(40)))


def downgrade() -> None:
    op.drop_column("agent_runs", "failure_code")
    op.drop_column("agent_runs", "completed_at")
    op.drop_column("agent_runs", "started_at")
