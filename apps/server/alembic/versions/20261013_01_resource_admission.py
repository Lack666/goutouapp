"""Shared upload admission, rate windows and crash attribution."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261013_01"
down_revision = "20261008_01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "resource_admission_states",
        sa.Column("scope_key", sa.String(64), primary_key=True),
        sa.Column("policy_hash", sa.String(64), nullable=False),
        sa.Column("counters", JSONB, nullable=False),
    )
    op.create_table(
        "upload_reservations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("scope_key", sa.String(64), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("lock_key", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("artifact_key", sa.String(32), unique=True),
        sa.Column("reserved_bytes", sa.BigInteger(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_upload_reservations_scope_key", "upload_reservations", ["scope_key"])


def downgrade():
    op.drop_table("upload_reservations")
    op.drop_table("resource_admission_states")
