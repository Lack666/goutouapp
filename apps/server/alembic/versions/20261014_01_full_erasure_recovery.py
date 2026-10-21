"""Full-scope erasure barriers and exact writer-stopped recovery receipts."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261014_01"
down_revision = "20261013_02"
branch_labels = None
depends_on = None


def common():
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "owner_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    ]


def upgrade():
    for name in ("users", "persons", "relationships"):
        op.add_column(name, sa.Column("deleted_at", sa.DateTime(timezone=True)))
    for column in (
        sa.Column("writer_token", sa.Uuid()),
        sa.Column("writer_scope", sa.String(64)),
        sa.Column("writer_released", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("recovered_at", sa.DateTime(timezone=True)),
    ):
        op.add_column("agent_runs", column)
    for name in ("lifecycle_confirmations", "lifecycle_receipts"):
        columns = common() + [
            sa.Column("domain", sa.String(16), nullable=False),
            sa.Column("target_id", sa.Uuid(), nullable=False),
            sa.Column("counts", JSONB, nullable=False),
            sa.CheckConstraint(
                "domain IN ('person', 'relationship', 'owner')", name="domain_valid"
            ),
        ]
        if name == "lifecycle_confirmations":
            columns += [
                sa.Column("snapshot_hash", sa.String(64), nullable=False),
                sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
                sa.Column("consumed_at", sa.DateTime(timezone=True)),
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
    op.create_index(
        "ix_lifecycle_confirmations_expires_at", "lifecycle_confirmations", ["expires_at"]
    )
    op.create_table(
        "run_recovery_receipts",
        *common(),
        sa.Column("operation_key", sa.String(128), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("old_status", sa.String(20), nullable=False),
        sa.Column("assistant_preserved", sa.Boolean(), nullable=False),
        sa.Column("observed_memory_count", sa.Integer(), nullable=False),
        sa.Column("writer_scope", sa.String(64), nullable=False),
        sa.Column("writer_token", sa.Uuid(), nullable=False),
        sa.Column("performed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_user_id", "operation_key"),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index(
        "ix_run_recovery_receipts_owner_user_id", "run_recovery_receipts", ["owner_user_id"]
    )


def downgrade():
    for name in ("run_recovery_receipts", "lifecycle_receipts", "lifecycle_confirmations"):
        op.drop_table(name)
    for name in ("recovered_at", "writer_released", "writer_scope", "writer_token"):
        op.drop_column("agent_runs", name)
    for name in ("relationships", "persons", "users"):
        op.drop_column(name, "deleted_at")
