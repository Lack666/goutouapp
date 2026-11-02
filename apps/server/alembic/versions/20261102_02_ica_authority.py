"""Temporary analysis authority and pending coverage ledger."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261102_02"
down_revision = "20261102_01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "imported_analysis_grants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("owner_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), sa.ForeignKey("chat_import_jobs.id"), nullable=False),
        sa.Column("relationship_id", sa.Uuid(), sa.ForeignKey("relationships.id"), nullable=False),
        sa.Column("person_id", sa.Uuid(), sa.ForeignKey("persons.id"), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("binding_hash", sa.String(64), nullable=False),
        sa.Column("operation_key", sa.String(128)),
        sa.Column("confirmation_hash", sa.String(64)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("payload", JSONB, nullable=False),
        sa.UniqueConstraint("owner_user_id", "operation_key"),
    )
    for name in ("owner_user_id", "dataset_id", "expires_at"):
        op.create_index(f"ix_imported_analysis_grants_{name}", "imported_analysis_grants", [name])


def downgrade():
    op.drop_table("imported_analysis_grants")
