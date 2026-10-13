"""Metadata-only owner challenges and immutable destructive-operation receipts."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, RecordMixin


class ErasureConfirmation(RecordMixin, Base):
    __tablename__ = "erasure_confirmations"
    __table_args__ = (
        CheckConstraint("domain IN ('dataset', 'conversation')", name="domain_valid"),
        CheckConstraint("message_count >= 0 AND run_count >= 0", name="counts_valid"),
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    domain: Mapped[str] = mapped_column(String(16))
    target_id: Mapped[UUID] = mapped_column()
    relationship_id: Mapped[UUID | None] = mapped_column(nullable=True)
    snapshot_hash: Mapped[str] = mapped_column(String(64))
    message_count: Mapped[int] = mapped_column()
    run_count: Mapped[int] = mapped_column()
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ErasureReceipt(RecordMixin, Base):
    __tablename__ = "erasure_receipts"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "operation_key"),
        CheckConstraint("domain IN ('dataset', 'conversation')", name="domain_valid"),
        CheckConstraint("message_count >= 0 AND run_count >= 0", name="counts_valid"),
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    operation_key: Mapped[str] = mapped_column(String(128))
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    confirmation_id: Mapped[UUID] = mapped_column()
    domain: Mapped[str] = mapped_column(String(16))
    target_id: Mapped[UUID] = mapped_column()
    relationship_id: Mapped[UUID | None] = mapped_column(nullable=True)
    message_count: Mapped[int] = mapped_column()
    run_count: Mapped[int] = mapped_column()
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
