"""Fixed UTC memory expiry, with a safe migration-time legacy grace period."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261008_01"
down_revision: str | None = "20260929_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "memory_records",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Deliberately independent of deployment config and old creation dates.
    op.execute("UPDATE memory_records SET expires_at = now() + interval '180 days'")
    op.alter_column("memory_records", "expires_at", nullable=False)
    op.create_index("ix_memory_records_expires_at", "memory_records", ["expires_at"])
    op.create_index("ix_memory_confirmations_expires_at", "memory_confirmations", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_memory_confirmations_expires_at", "memory_confirmations")
    op.drop_index("ix_memory_records_expires_at", "memory_records")
    op.drop_column("memory_records", "expires_at")
