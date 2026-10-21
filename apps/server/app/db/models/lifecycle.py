"""Content-free full-scope confirmations, immutable receipts and Run recovery proof."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, RecordMixin


class LifecycleConfirmation(RecordMixin, Base):
    __tablename__ = "lifecycle_confirmations"
    __table_args__ = (
        CheckConstraint("domain IN ('person', 'relationship', 'owner')", name="domain_valid"),
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    domain: Mapped[str] = mapped_column(String(16))
    target_id: Mapped[UUID] = mapped_column()
    snapshot_hash: Mapped[str] = mapped_column(String(64))
    counts: Mapped[dict] = mapped_column(JSONB)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LifecycleReceipt(RecordMixin, Base):
    __tablename__ = "lifecycle_receipts"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "operation_key"),
        CheckConstraint("domain IN ('person', 'relationship', 'owner')", name="domain_valid"),
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    domain: Mapped[str] = mapped_column(String(16))
    target_id: Mapped[UUID] = mapped_column()
    operation_key: Mapped[str] = mapped_column(String(128))
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    confirmation_id: Mapped[UUID] = mapped_column()
    counts: Mapped[dict] = mapped_column(JSONB)
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RunRecoveryReceipt(RecordMixin, Base):
    __tablename__ = "run_recovery_receipts"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "operation_key"),
        UniqueConstraint("run_id"),
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    operation_key: Mapped[str] = mapped_column(String(128))
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    run_id: Mapped[UUID] = mapped_column()
    conversation_id: Mapped[UUID] = mapped_column()
    old_status: Mapped[str] = mapped_column(String(20))
    assistant_preserved: Mapped[bool] = mapped_column()
    observed_memory_count: Mapped[int] = mapped_column()
    writer_scope: Mapped[str] = mapped_column(String(64))
    writer_token: Mapped[UUID] = mapped_column()
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
