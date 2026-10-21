"""Operator-only exact-run recovery; no Provider call or synthetic answer."""

from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.db.models import AgentRun, MemoryRecordRow, Message, RunRecoveryReceipt, User
from app.db.repositories import records
from app.services.agent_service import AuthenticatedActor, valid_operation_key
from app.services.agent_writer import AgentWriterRegistry, WriterProofUnavailable
from app.services.erasure import ErasureError, _canonical


class AgentRunRecovery:
    def __init__(self, sessions, writer_registry: AgentWriterRegistry):
        self.sessions = sessions
        self.writers = writer_registry

    def recover(
        self, actor: AuthenticatedActor, conversation_id: UUID, run_id: UUID, operation_key: str
    ):
        if not isinstance(actor, AuthenticatedActor) or not valid_operation_key(operation_key):
            raise ErasureError("invalid_credential")
        fingerprint = sha256(_canonical((actor.user_id, conversation_id, run_id))).hexdigest()
        try:
            with self.sessions() as db, db.begin():
                owner = db.scalar(
                    select(User)
                    .where(User.id == actor.user_id, User.deleted_at.is_(None))
                    .with_for_update(key_share=True)
                )
                if owner is None:
                    raise ErasureError("invalid_credential")
                previous = db.scalar(
                    select(RunRecoveryReceipt).where(
                        RunRecoveryReceipt.owner_user_id == actor.user_id,
                        RunRecoveryReceipt.operation_key == operation_key,
                    )
                )
                if previous:
                    if previous.request_fingerprint != fingerprint:
                        raise ErasureError("idempotency_conflict")
                    return self.result(previous)
                records.lock_conversation_run_slot(db, conversation_id)
                run = db.scalar(
                    select(AgentRun)
                    .where(
                        AgentRun.id == run_id,
                        AgentRun.user_id == actor.user_id,
                        AgentRun.conversation_id == conversation_id,
                    )
                    .with_for_update()
                )
                if (
                    run is None
                    or records.get_conversation(db, actor.user_id, conversation_id) is None
                ):
                    raise ErasureError("not_found")
                if run.recovered_at is not None:
                    raise ErasureError("target_changed")
                if (
                    run.status not in {"pending", "running"}
                    and not (run.status == "completed" and run.memory_status is None)
                    and not (
                        run.status == "failed" and run.writer_token and not run.writer_released
                    )
                ):
                    raise ErasureError("target_changed")
                # Hold the actual OS lock throughout reconciliation and receipt commit.
                # DB disconnection/time/status never replaces this proof.
                with self.writers.stopped(run):
                    for pointer, role in (
                        (run.user_message_id, "user"),
                        (run.assistant_message_id, "assistant"),
                    ):
                        if pointer is not None:
                            message = db.get(Message, pointer)
                            if (
                                message is None
                                or message.conversation_id != conversation_id
                                or message.role != role
                            ):
                                raise ErasureError("effects_unresolved")
                    if run.status == "completed" and run.assistant_message_id is None:
                        raise ErasureError("effects_unresolved")
                    memories = db.scalar(
                        select(func.count())
                        .select_from(MemoryRecordRow)
                        .where(
                            MemoryRecordRow.owner_user_id == actor.user_id,
                            MemoryRecordRow.first_run_id == run_id,
                        )
                    )
                    now = datetime.now(UTC)
                    receipt = RunRecoveryReceipt(
                        owner_user_id=actor.user_id,
                        operation_key=operation_key,
                        request_fingerprint=fingerprint,
                        run_id=run_id,
                        conversation_id=conversation_id,
                        old_status=run.status,
                        assistant_preserved=run.assistant_message_id is not None,
                        observed_memory_count=memories,
                        writer_scope=run.writer_scope,
                        writer_token=run.writer_token,
                        performed_at=now,
                    )
                    # Failed means no successful overall result is asserted. Existing
                    # answer/Memory effects remain; their unknown outcome is explicit.
                    run.status = "failed"
                    run.failure_code = "writer_stopped"
                    run.recovered_at = now
                    run.completed_at = now
                    db.add(receipt)
                    db.flush()
                    result = self.result(receipt)
                    db.commit()
                    return result
        except WriterProofUnavailable:
            raise ErasureError("writer_proof_unavailable") from None
        except SQLAlchemyError:
            raise ErasureError("persistence_failure") from None

    @staticmethod
    def result(row):
        return {
            "receipt_id": str(row.id),
            "run_id": str(row.run_id),
            "conversation_id": str(row.conversation_id),
            "status": "failed",
            "assistant_preserved": row.assistant_preserved,
            "observed_memory_count": row.observed_memory_count,
            "memory_outcome": "unknown_preserved",
            "performed_at": row.performed_at.isoformat(),
        }
