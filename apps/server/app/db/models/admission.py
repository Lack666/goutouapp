"""Shared bounded admission metadata; no transcript, filename or credential."""

from uuid import UUID

from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AdmissionState(Base):
    __tablename__ = "resource_admission_states"
    scope_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    policy_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    counters: Mapped[dict] = mapped_column(JSONB, nullable=False)


class UploadReservation(Base):
    __tablename__ = "upload_reservations"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    scope_key: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    owner_user_id: Mapped[UUID] = mapped_column(nullable=False)
    lock_key: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    artifact_key: Mapped[str | None] = mapped_column(String(32), unique=True)
    reserved_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
