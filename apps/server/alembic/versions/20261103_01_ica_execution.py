"""Independent ICA Mock execution authority and expiring reports."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261103_01"
down_revision = "20261102_02"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "imported_analysis_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("owner_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "grant_id", sa.Uuid(), sa.ForeignKey("imported_analysis_grants.id"), nullable=False
        ),
        sa.Column("dataset_id", sa.Uuid(), sa.ForeignKey("chat_import_jobs.id"), nullable=False),
        sa.Column("relationship_id", sa.Uuid(), sa.ForeignKey("relationships.id"), nullable=False),
        sa.Column("person_id", sa.Uuid(), sa.ForeignKey("persons.id"), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("operation_key", sa.String(128)),
        sa.Column("confirmation_hash", sa.String(64)),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("binding_hash", sa.String(64), nullable=False),
        sa.Column("challenge_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("execution_binding", JSONB(), nullable=False),
        sa.Column("report", JSONB()),
        sa.Column("ledger", JSONB(), nullable=False),
        sa.Column("receipts", JSONB(), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False),
        sa.Column("reserved_tokens", sa.Integer(), nullable=False),
        sa.Column("writer_token", sa.String(64)),
        sa.Column("writer_active", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.String(64)),
        sa.UniqueConstraint("owner_user_id", "operation_key"),
    )
    for column in ("owner_user_id", "grant_id", "dataset_id", "expires_at"):
        op.create_index(f"ix_imported_analysis_runs_{column}", "imported_analysis_runs", [column])


def downgrade():
    op.drop_table("imported_analysis_runs")
