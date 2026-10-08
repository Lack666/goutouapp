"""Transport-free retention contract; server settings are injected at composition."""

from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_MEMORY_DAYS = 180


def utc_now() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("retention requires an aware datetime")
    return value.astimezone(UTC)


class RetentionPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    active_days: int = Field(default=DEFAULT_MEMORY_DAYS, ge=1, le=3650, strict=True)
    challenge_grace_hours: int = Field(default=24, ge=1, le=8760, strict=True)
    batch_size: int = Field(default=100, ge=1, le=1000, strict=True)
    receipt_retention: Literal["durable_owner_lifetime"] = "durable_owner_lifetime"

    def expires_at(self, created_at: datetime) -> datetime:
        return as_utc(created_at) + timedelta(days=self.active_days)

    def challenge_cutoff(self, now: datetime) -> datetime:
        return as_utc(now) - timedelta(hours=self.challenge_grace_hours)

    @property
    def summary(self) -> str:
        return (
            f"New memories expire {self.active_days} days after creation; recall does not renew "
            "them. Stored expiration dates remain fixed. Legacy memories receive 180 days "
            "from migration. You can delete primary-store memory at any time."
        )

    @classmethod
    def from_settings(cls, settings) -> "RetentionPolicy":
        return cls(
            active_days=settings.memory_retention_days,
            challenge_grace_hours=settings.memory_challenge_cleanup_grace_hours,
            batch_size=settings.memory_cleanup_batch_size,
        )
