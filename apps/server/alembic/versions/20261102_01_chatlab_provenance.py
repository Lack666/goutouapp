"""Optional exchange format provenance; canonical identity remains unchanged."""

import sqlalchemy as sa
from alembic import op

revision = "20261102_01"
down_revision = "20261014_01"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("relationship_messages", sa.Column("external_message_id", sa.String(1024)))
    op.add_column("relationship_messages", sa.Column("external_reply_id", sa.String(1024)))
    op.add_column("relationship_messages", sa.Column("external_message_type", sa.Integer()))
    op.create_index(
        "ix_ica_dataset_keyset",
        "relationship_messages",
        ["owner_user_id", "import_job_id", "timestamp_utc", "id"],
    )


def downgrade():
    op.drop_index("ix_ica_dataset_keyset", table_name="relationship_messages")
    for name in ("external_message_type", "external_reply_id", "external_message_id"):
        op.drop_column("relationship_messages", name)
