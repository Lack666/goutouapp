"""Independent, temporary ICA preparation authority; never Memory consent."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
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
