"""Privileged, deterministic one-shot maintenance; never exposed through HTTP."""

from collections.abc import Callable
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.db.models import (
    MemoryConfirmationRow,
    MemoryMutationRow,
    MemoryOperationRow,
    MemoryRecordRow,
    User,
)
from app.retention import RetentionPolicy, as_utc, utc_now


class CleanupCounts(BaseModel):
    memory_records: int = 0
    undo_operations: int = 0
    confirmation_challenges: int = 0
    mutation_receipts_removed: int = 0
    mutation_receipts_retained: int = 0


class CleanupResult(BaseModel):
    dry_run: bool
    status: str = "ok"
    batches_committed: int = 0
    counts: CleanupCounts = Field(default_factory=CleanupCounts)
    error: str | None = None


class CleanupLimits(BaseModel):
    model_config = ConfigDict(extra="forbid")
    batch_size: int = Field(ge=1, le=1000, strict=True)
    max_batches: int = Field(ge=1, le=10000, strict=True)


class MemoryRetentionService:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        *,
        policy: RetentionPolicy | None = None,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._session_factory = session_factory
        self.policy = policy or RetentionPolicy()
        self._clock = clock

    def _counts(self, db: Session, now: datetime) -> CleanupCounts:
        expired = select(MemoryRecordRow.id).where(MemoryRecordRow.expires_at <= now)
        return CleanupCounts(
            memory_records=db.scalar(select(func.count()).select_from(expired.subquery())),
            undo_operations=db.scalar(
                select(func.count())
                .select_from(MemoryOperationRow)
                .where(MemoryOperationRow.record_id.in_(expired))
            ),
            confirmation_challenges=db.scalar(
                select(func.count())
                .select_from(MemoryConfirmationRow)
                .where(MemoryConfirmationRow.expires_at <= self.policy.challenge_cutoff(now))
            ),
            mutation_receipts_retained=db.scalar(
                select(func.count()).select_from(MemoryMutationRow)
            ),
        )

    def _delete_batch(self, db: Session, now: datetime, size: int) -> CleanupCounts:
        db.execute(text("SET LOCAL lock_timeout = '1000ms'"))
        db.execute(text("SET LOCAL statement_timeout = '5000ms'"))
        cutoff = self.policy.challenge_cutoff(now)
        # Discovery does not lock child rows: all writers take the owner lock first.
        memories = db.execute(
            select(MemoryRecordRow.id, MemoryRecordRow.owner_user_id)
            .where(MemoryRecordRow.expires_at <= now)
            .order_by(MemoryRecordRow.expires_at, MemoryRecordRow.id)
            .limit(size)
        ).all()
        challenges = db.execute(
            select(MemoryConfirmationRow.id, MemoryConfirmationRow.owner_user_id)
            .where(MemoryConfirmationRow.expires_at <= cutoff)
            .order_by(MemoryConfirmationRow.expires_at, MemoryConfirmationRow.id)
            .limit(size)
        ).all()
        owners = sorted({row.owner_user_id for row in [*memories, *challenges]})
        # Sorted acquisition prevents multi-owner maintenance deadlocks.
        for owner in owners:
            db.scalar(select(User.id).where(User.id == owner).with_for_update())
        ids = list(
            db.scalars(
                select(MemoryRecordRow.id).where(
                    MemoryRecordRow.id.in_([row.id for row in memories]),
                    MemoryRecordRow.expires_at <= now,
                )
            )
        )
        operations = db.scalar(
            select(func.count())
            .select_from(MemoryOperationRow)
            .where(MemoryOperationRow.record_id.in_(ids))
        )
        removed = db.execute(delete(MemoryRecordRow).where(MemoryRecordRow.id.in_(ids))).rowcount
        removed_challenges = db.execute(
            delete(MemoryConfirmationRow).where(
                MemoryConfirmationRow.id.in_([row.id for row in challenges]),
                MemoryConfirmationRow.expires_at <= cutoff,
            )
        ).rowcount
        return CleanupCounts(
            memory_records=removed,
            undo_operations=operations,
            confirmation_challenges=removed_challenges,
        )

    def run(
        self, *, dry_run: bool = True, batch_size: int | None = None, max_batches: int = 1
    ) -> CleanupResult:
        limits = CleanupLimits(
            batch_size=self.policy.batch_size if batch_size is None else batch_size,
            max_batches=max_batches,
        )
        result = CleanupResult(dry_run=dry_run)
        try:
            now = as_utc(self._clock())
            if dry_run:
                with self._session_factory() as db:
                    result.counts = self._counts(db, now)
                return result
            for _ in range(limits.max_batches):
                with self._session_factory() as db, db.begin():
                    counts = self._delete_batch(db, now, limits.batch_size)
                # Publish counts only after commit. Prior batches survive a later error.
                result.batches_committed += 1
                for category in ("memory_records", "undo_operations", "confirmation_challenges"):
                    setattr(
                        result.counts,
                        category,
                        getattr(result.counts, category) + getattr(counts, category),
                    )
                if counts.memory_records == counts.confirmation_challenges == 0:
                    break
            with self._session_factory() as db:
                result.counts.mutation_receipts_retained = db.scalar(
                    select(func.count()).select_from(MemoryMutationRow)
                )
        except Exception:
            result.status = "failed"
            result.error = "retention_cleanup_failed"
        return result
