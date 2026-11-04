"""Exact owner-scoped erasure; independent of HTTP, Agent runtime and LLMs."""

import json
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.db.models import (
    AgentRun,
    ChatImportJob,
    ChatImportSpeaker,
    Conversation,
    ErasureConfirmation,
    ErasureReceipt,
    ImportedAnalysisRun,
    Message,
    RelationshipMessage,
    User,
)
from app.db.repositories import records
from app.schemas.erasure import ErasureChallenge, ErasureExecute, ErasureResult, ErasureTarget
from app.services.agent_service import AuthenticatedActor
from app.services.agent_writer import AgentWriterRegistry, WriterProofUnavailable
from app.services.imported_analysis import invalidate_datasets


class ErasureError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _fingerprint(body):
    return sha256(json.dumps(body.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()


def _canonical(values):
    # Connection timezones differ between HTTP and standalone callers. Bind
    # identical instants rather than Python's driver-specific tuple repr.
    return json.dumps(
        [
            value.astimezone(UTC).isoformat()
            if isinstance(value, datetime)
            else str(value)
            if isinstance(value, UUID)
            else value
            for value in values
        ],
        separators=(",", ":"),
    ).encode()


class ErasureService:
    def __init__(self, sessions, *, clock=lambda: datetime.now(UTC), writers=None):
        self._sessions = sessions
        self._clock = clock
        self._writers = writers or AgentWriterRegistry(get_settings().chat_import_artifact_root)

    @contextmanager
    def _transaction(self, actor):
        if not isinstance(actor, AuthenticatedActor):
            raise ErasureError("invalid_credential")
        try:
            with self._sessions() as db, db.begin():
                # Same owner serialization as guarded Memory: receipt lookup first,
                # then target lock, challenge and all destructive effects in one commit.
                # FOR NO KEY UPDATE permits child FK KEY SHARE checks while
                # serializing owner mutations. FOR UPDATE would deadlock an
                # Agent holding the Conversation advisory slot.
                if (
                    db.scalar(
                        select(User)
                        .where(User.id == actor.user_id, User.deleted_at.is_(None))
                        .with_for_update(key_share=True)
                    )
                    is None
                ):
                    raise ErasureError("invalid_credential")
                yield db
        except SQLAlchemyError:
            raise ErasureError("persistence_failure") from None
        except WriterProofUnavailable:
            raise ErasureError("writer_proof_unavailable") from None

    def _target(self, db, actor, body):
        if body.domain == "conversation":
            records.lock_conversation_run_slot(db, body.target_id)
            row = db.scalar(
                select(Conversation)
                .where(Conversation.id == body.target_id, Conversation.user_id == actor.user_id)
                .with_for_update()
            )
            relationship = row.relationship_id if row else None
        else:
            row = db.scalar(
                select(ChatImportJob)
                .where(
                    ChatImportJob.id == body.target_id,
                    ChatImportJob.owner_user_id == actor.user_id,
                    ChatImportJob.status == "imported",
                )
                .with_for_update()
            )
            relationship = row.bound_relationship_id if row else None
            if row is not None:
                # Exactly the same scope lock as ImportMergeService; never broaden
                # to another Job, duplicate transcript or Relationship.
                key = f"{actor.user_id}:{relationship}:{row.transcript_fingerprint}"
                value = int.from_bytes(sha256(key.encode()).digest()[:8], signed=True)
                db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": value})
        if row is None or relationship != body.relationship_id:
            raise ErasureError("not_found")
        if (
            relationship is not None
            and records.get_relationship(db, actor.user_id, relationship) is None
        ):
            raise ErasureError("not_found")
        if row.deleted_at is not None:
            raise ErasureError("target_deleted")
        return row

    def _snapshot(self, db, body, row):
        digest = sha256()
        digest.update(_canonical((row.id, row.updated_at, body.domain, body.relationship_id)))
        if body.domain == "conversation":
            query = (
                select(Message.id, Message.updated_at, func.md5(Message.content))
                .where(Message.conversation_id == row.id)
                .order_by(Message.id)
            )
            runs = db.execute(
                select(
                    AgentRun.id,
                    AgentRun.status,
                    AgentRun.updated_at,
                    AgentRun.memory_status,
                    AgentRun.operation_key,
                    AgentRun.request_fingerprint,
                )
                .where(AgentRun.conversation_id == row.id)
                .order_by(AgentRun.id)
                .execution_options(yield_per=500)
            )
            run_count = 0
            for run in runs:
                durable = db.get(AgentRun, run.id)
                if run.status in {"running", "pending"} or (
                    run.status == "completed" and run.memory_status is None
                ):
                    raise ErasureError("target_busy")
                self._writers.require_settled(db, durable)
                digest.update(_canonical(tuple(run)))
                run_count += 1
        else:
            if db.scalar(
                select(ImportedAnalysisRun.id)
                .where(
                    ImportedAnalysisRun.dataset_id == row.id,
                    ImportedAnalysisRun.owner_user_id == row.owner_user_id,
                    ImportedAnalysisRun.writer_active.is_(True),
                )
                .limit(1)
            ):
                raise ErasureError("target_busy")
            query = (
                select(
                    RelationshipMessage.id,
                    RelationshipMessage.updated_at,
                    func.md5(RelationshipMessage.content),
                )
                .where(
                    RelationshipMessage.import_job_id == row.id,
                    RelationshipMessage.owner_user_id == row.owner_user_id,
                    RelationshipMessage.relationship_id == body.relationship_id,
                )
                .order_by(RelationshipMessage.id)
            )
            run_count = 0
            for run in db.execute(
                select(ImportedAnalysisRun.__table__)
                .where(
                    ImportedAnalysisRun.dataset_id == row.id,
                    ImportedAnalysisRun.owner_user_id == row.owner_user_id,
                )
                .order_by(ImportedAnalysisRun.id)
                .execution_options(yield_per=500)
            ):
                digest.update(_canonical(tuple(run)))
                run_count += 1
        count = 0
        for message in db.execute(query.execution_options(yield_per=500)):
            digest.update(_canonical(tuple(message)))
            count += 1
        return digest.hexdigest(), count, run_count

    def prepare(self, actor, body: ErasureTarget) -> ErasureChallenge:
        with self._transaction(actor) as db:
            target = self._target(db, actor, body)
            snapshot, messages, runs = self._snapshot(db, body, target)
            challenge = ErasureConfirmation(
                owner_user_id=actor.user_id,
                **body.model_dump(),
                snapshot_hash=snapshot,
                message_count=messages,
                run_count=runs,
                expires_at=self._clock() + timedelta(minutes=5),
            )
            db.add(challenge)
            db.flush()
            return ErasureChallenge(
                **body.model_dump(),
                confirmation_id=challenge.id,
                message_count=messages,
                run_count=runs,
                expires_at=challenge.expires_at,
            )

    @staticmethod
    def _result(row):
        return ErasureResult(
            domain=row.domain,
            target_id=row.target_id,
            relationship_id=row.relationship_id,
            receipt_id=row.id,
            confirmation_id=row.confirmation_id,
            message_count=row.message_count,
            run_count=row.run_count,
            performed_at=row.performed_at,
        )

    def execute(self, actor, body: ErasureExecute) -> ErasureResult:
        with self._transaction(actor) as db:
            fingerprint = _fingerprint(body)
            previous = db.scalar(
                select(ErasureReceipt).where(
                    ErasureReceipt.owner_user_id == actor.user_id,
                    ErasureReceipt.operation_key == body.operation_key,
                )
            )
            if previous is not None:
                if previous.request_fingerprint != fingerprint:
                    raise ErasureError("idempotency_conflict")
                return self._result(previous)
            challenge = db.scalar(
                select(ErasureConfirmation).where(
                    ErasureConfirmation.id == body.confirmation_id,
                    ErasureConfirmation.owner_user_id == actor.user_id,
                )
            )
            if challenge is None:
                raise ErasureError("confirmation_not_found")
            if any(
                getattr(challenge, k) != getattr(body, k)
                for k in ("domain", "target_id", "relationship_id")
            ):
                raise ErasureError("confirmation_mismatch")
            if challenge.consumed_at is not None:
                raise ErasureError("confirmation_consumed")
            if challenge.expires_at <= self._clock():
                raise ErasureError("confirmation_expired")
            target = self._target(db, actor, body)
            snapshot, messages, runs = self._snapshot(db, body, target)
            if snapshot != challenge.snapshot_hash:
                raise ErasureError("target_changed")
            now = self._clock()
            if body.domain == "conversation":
                db.execute(delete(Message).where(Message.conversation_id == target.id))
                # Preserve run IDs/key/fingerprint/status, erase answer-linked metadata.
                db.execute(
                    update(AgentRun)
                    .where(AgentRun.conversation_id == target.id)
                    .values(result_warnings=None, memory_status=None)
                )
            else:
                db.execute(
                    delete(RelationshipMessage).where(
                        RelationshipMessage.import_job_id == target.id,
                        RelationshipMessage.owner_user_id == actor.user_id,
                        RelationshipMessage.relationship_id == body.relationship_id,
                    )
                )
                db.execute(
                    delete(ChatImportSpeaker).where(
                        ChatImportSpeaker.job_id == target.id,
                        ChatImportSpeaker.owner_user_id == actor.user_id,
                    )
                )
            if body.domain == "dataset":
                invalidate_datasets(db, [target.id])
            target.deleted_at = now
            target.updated_at = now
            challenge.consumed_at = now
            receipt = ErasureReceipt(
                owner_user_id=actor.user_id,
                **body.model_dump(),
                request_fingerprint=fingerprint,
                message_count=messages,
                run_count=runs,
                performed_at=now,
            )
            db.add(receipt)
            db.flush()
            return self._result(receipt)

    def receipt(self, actor, receipt_id: UUID) -> ErasureResult:
        with self._transaction(actor) as db:
            row = db.scalar(
                select(ErasureReceipt).where(
                    ErasureReceipt.id == receipt_id,
                    ErasureReceipt.owner_user_id == actor.user_id,
                )
            )
            if row is None:
                raise ErasureError("not_found")
            return self._result(row)
