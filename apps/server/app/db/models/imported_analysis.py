"""Independent, temporary ICA preparation authority; never Memory consent."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, RecordMixin


class ImportedAnalysisGrant(RecordMixin, Base):
    __tablename__ = "imported_analysis_grants"
    __table_args__ = (UniqueConstraint("owner_user_id", "operation_key"),)
    owner_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("chat_import_jobs.id"), index=True)
    relationship_id: Mapped[UUID] = mapped_column(ForeignKey("relationships.id"))
    person_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id"))
    status: Mapped[str] = mapped_column(String(24))
    token_hash: Mapped[str] = mapped_column(String(64))
    binding_hash: Mapped[str] = mapped_column(String(64))
    operation_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    confirmation_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB)


class ImportedAnalysisRun(RecordMixin, Base):
    """Independent execution confirmation and temporary report; no chat transcript copy."""

    __tablename__ = "imported_analysis_runs"
    __table_args__ = (UniqueConstraint("owner_user_id", "operation_key"),)
    owner_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    grant_id: Mapped[UUID] = mapped_column(ForeignKey("imported_analysis_grants.id"), index=True)
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("chat_import_jobs.id"), index=True)
    relationship_id: Mapped[UUID] = mapped_column(ForeignKey("relationships.id"))
    person_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id"))
    status: Mapped[str] = mapped_column(String(24))
    operation_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    confirmation_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    token_hash: Mapped[str] = mapped_column(String(64))
    binding_hash: Mapped[str] = mapped_column(String(64))
    challenge_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    execution_binding: Mapped[dict] = mapped_column(JSONB)
    report: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ledger: Mapped[list] = mapped_column(JSONB, default=list)
    receipts: Mapped[list] = mapped_column(JSONB, default=list)
    request_count: Mapped[int] = mapped_column(Integer, default=0)
    reserved_tokens: Mapped[int] = mapped_column(Integer, default=0)
    writer_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    writer_active: Mapped[bool] = mapped_column(Boolean, default=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
