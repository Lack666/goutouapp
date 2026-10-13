"""Guarded domain erasure and durable retry fences."""

import sqlalchemy as sa
from alembic import op

revision = "20261013_02"
down_revision = "20261013_01"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("conversations", "chat_import_jobs"):
        op.add_column(table, sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    for name in ("erasure_confirmations", "erasure_receipts"):
        columns = [
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "owner_user_id",
                sa.Uuid(),
                sa.ForeignKey("users.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("domain", sa.String(16), nullable=False),
            sa.Column("target_id", sa.Uuid(), nullable=False),
            sa.Column("relationship_id", sa.Uuid(), nullable=True),
            sa.Column("message_count", sa.Integer(), nullable=False),
            sa.Column("run_count", sa.Integer(), nullable=False),
            sa.CheckConstraint("domain IN ('dataset', 'conversation')", name="domain_valid"),
            sa.CheckConstraint("message_count >= 0 AND run_count >= 0", name="counts_valid"),
        ]
        if name == "erasure_confirmations":
            columns += [
                sa.Column("snapshot_hash", sa.String(64), nullable=False),
                sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
                sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
            ]
        else:
            columns += [
                sa.Column("operation_key", sa.String(128), nullable=False),
                sa.Column("request_fingerprint", sa.String(64), nullable=False),
                sa.Column("confirmation_id", sa.Uuid(), nullable=False),
                sa.Column("performed_at", sa.DateTime(timezone=True), nullable=False),
                sa.UniqueConstraint("owner_user_id", "operation_key"),
            ]
        op.create_table(name, *columns)
        op.create_index("ix_" + name + "_owner_user_id", name, ["owner_user_id"])
    op.create_index("ix_erasure_confirmations_expires_at", "erasure_confirmations", ["expires_at"])


def downgrade():
    op.drop_table("erasure_receipts")
    op.drop_table("erasure_confirmations")
    for table in ("chat_import_jobs", "conversations"):
        op.drop_column(table, "deleted_at")
