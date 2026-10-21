"""Owner-serialized complete structured-scope erasure, independent of transport."""

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from sqlalchemy import delete, or_, select, update
from sqlalchemy.exc import SQLAlchemyError

from app.chat_import.artifacts import ArtifactStoreError
from app.db.models import (
    AgentRun,
    ChatImportArtifact,
    ChatImportJob,
    ChatImportSpeaker,
    Conversation,
    ErasureConfirmation,
    LifecycleConfirmation,
    LifecycleReceipt,
    MemoryConfirmationRow,
    MemoryControlRow,
    MemoryRecordRow,
    Message,
    Person,
    Relationship,
    RelationshipMessage,
    UploadReservation,
    User,
)
from app.db.repositories import records
from app.schemas.lifecycle import (
    LifecycleChallenge,
    LifecycleExecute,
    LifecycleResult,
    LifecycleTarget,
)
from app.services.agent_service import AuthenticatedActor
from app.services.agent_writer import WriterProofUnavailable
from app.services.erasure import ErasureError, _canonical, _fingerprint


class LifecycleErasure:
    def __init__(self, sessions, artifacts, writers, *, clock=lambda: datetime.now(UTC)):
        self.sessions, self.artifacts, self.writers = sessions, artifacts, writers
        self.clock = clock

    @contextmanager
    def transaction(self, actor, *, allow_erased=False):
        if not isinstance(actor, AuthenticatedActor):
            raise ErasureError("invalid_credential")
        try:
            with self.sessions() as db, db.begin():
                owner = db.scalar(
                    select(User).where(User.id == actor.user_id).with_for_update(key_share=True)
                )
                if owner is None or (owner.deleted_at and not allow_erased):
                    raise ErasureError("invalid_credential")
                yield db, owner
        except (SQLAlchemyError, OSError, ArtifactStoreError):
            raise ErasureError("persistence_failure") from None
        except WriterProofUnavailable:
            raise ErasureError("writer_proof_unavailable") from None

    def scope(self, db, actor, body):
        owner = actor.user_id
        if body.domain == "owner":
            if body.target_id != owner:
                raise ErasureError("not_found")
            target = db.get(User, owner)
        else:
            model = Person if body.domain == "person" else Relationship
            target = db.scalar(
                select(model).where(model.id == body.target_id, model.user_id == owner)
            )
        if target is None:
            raise ErasureError("not_found")
        if target.deleted_at:
            raise ErasureError("target_deleted")
        persons = select(Person.id).where(Person.user_id == owner)
        relationships = select(Relationship.id).where(Relationship.user_id == owner)
        if body.domain == "person":
            persons = persons.where(Person.id == target.id)
            relationships = relationships.where(Relationship.person_id == target.id)
        elif body.domain == "relationship":
            persons = persons.where(Person.id == target.person_id)
            relationships = relationships.where(Relationship.id == target.id)
        conversations = select(Conversation.id).where(Conversation.user_id == owner)
        jobs = select(ChatImportJob.id).where(ChatImportJob.owner_user_id == owner)
        memories = select(MemoryRecordRow.id).where(MemoryRecordRow.owner_user_id == owner)
        if body.domain != "owner":
            conversations = conversations.where(Conversation.relationship_id.in_(relationships))
            jobs = jobs.where(ChatImportJob.bound_relationship_id.in_(relationships))
            memories = memories.where(
                or_(
                    MemoryRecordRow.person_id.in_(persons),
                    MemoryRecordRow.relationship_id.in_(relationships),
                )
                if body.domain == "person"
                else MemoryRecordRow.relationship_id.in_(relationships)
            )
        if body.domain == "person":
            # A Person binding in another/unbound import is an explicit shared-reference
            # rejection, never permission to erase that other relationship or job.
            if db.scalar(
                select(ChatImportSpeaker.id)
                .where(
                    ChatImportSpeaker.owner_user_id == owner,
                    ChatImportSpeaker.person_id == target.id,
                    ChatImportSpeaker.job_id.not_in(jobs),
                )
                .limit(1)
            ):
                raise ErasureError("shared_reference")
        # All write paths take owner SHARE before domain locks. Maintenance also
        # uses these job/artifact locks, so its physical cleanup cannot race here.
        for cid in db.scalars(conversations.order_by(Conversation.id)):
            records.lock_conversation_run_slot(db, cid)
        db.execute(
            select(ChatImportJob.id)
            .where(ChatImportJob.id.in_(jobs))
            .order_by(ChatImportJob.id)
            .with_for_update()
        ).all()
        artifacts = select(ChatImportArtifact.id).where(ChatImportArtifact.owner_user_id == owner)
        if body.domain != "owner":
            artifacts = artifacts.where(
                ChatImportArtifact.id.in_(
                    select(ChatImportJob.artifact_id).where(ChatImportJob.id.in_(jobs))
                )
            )
        db.execute(
            select(ChatImportArtifact.id)
            .where(ChatImportArtifact.id.in_(artifacts))
            .order_by(ChatImportArtifact.id)
            .with_for_update()
        ).all()
        if db.scalar(
            select(UploadReservation.id)
            .where(UploadReservation.owner_user_id == owner, UploadReservation.active.is_(True))
            .limit(1)
        ):
            raise ErasureError("target_busy")
        if body.domain == "owner":
            # Unknown files have no trustworthy owner attribution. Never delete
            # another owner's files or certify their contents as already erased.
            keys = set(db.scalars(select(ChatImportArtifact.storage_key)))
            keys.update(
                db.scalars(
                    select(UploadReservation.artifact_key).where(
                        UploadReservation.artifact_key.is_not(None)
                    )
                )
            )
            known = {key + suffix for key in keys for suffix in (".bin", ".part")}
            if any(
                path.is_symlink() or not path.is_file() or path.name not in known
                for path in self.artifacts._root.iterdir()
            ):
                raise ErasureError("shared_reference")
        scope = {
            Person: Person.id.in_(persons) if body.domain != "relationship" else Person.id.in_([]),
            Relationship: Relationship.id.in_(relationships),
            Conversation: Conversation.id.in_(conversations),
            AgentRun: AgentRun.conversation_id.in_(conversations),
            Message: Message.conversation_id.in_(conversations),
            ChatImportJob: ChatImportJob.id.in_(jobs),
            RelationshipMessage: RelationshipMessage.import_job_id.in_(jobs),
            ChatImportSpeaker: ChatImportSpeaker.job_id.in_(jobs),
            ChatImportArtifact: ChatImportArtifact.id.in_(artifacts),
            MemoryRecordRow: MemoryRecordRow.id.in_(memories),
        }
        if body.domain == "owner":
            scope[MemoryControlRow] = MemoryControlRow.user_id == owner
            scope[UploadReservation] = UploadReservation.owner_user_id == owner
        for run in db.scalars(select(AgentRun).where(scope[AgentRun])):
            if run.status in {"pending", "running"} or (
                run.status == "completed" and run.memory_status is None
            ):
                raise ErasureError("target_busy")
            self.writers.require_settled(db, run)
        return target, scope

    def snapshot(self, db, body, target, scope):
        digest = sha256(_canonical((body.domain, target.id, target.updated_at)))
        counts = {}
        for model, predicate in scope.items():
            digest.update(model.__tablename__.encode())
            count = 0
            # Streaming hashes contain no second persisted copy of private content.
            for row in db.execute(
                select(model.__table__)
                .where(predicate)
                .order_by(model.id)
                .execution_options(yield_per=500)
            ):
                digest.update(_canonical(tuple(row)))
                count += 1
            counts[model.__tablename__] = count
        return digest.hexdigest(), counts

    def prepare(self, actor, body: LifecycleTarget):
        with self.transaction(actor) as (db, _):
            target, scope = self.scope(db, actor, body)
            snapshot, counts = self.snapshot(db, body, target, scope)
            row = LifecycleConfirmation(
                owner_user_id=actor.user_id,
                **body.model_dump(),
                snapshot_hash=snapshot,
                counts=counts,
                expires_at=self.clock() + timedelta(minutes=5),
            )
            db.add(row)
            db.flush()
            return LifecycleChallenge(
                **body.model_dump(),
                confirmation_id=row.id,
                counts=counts,
                expires_at=row.expires_at,
            )

    @staticmethod
    def result(row):
        return LifecycleResult(
            domain=row.domain,
            target_id=row.target_id,
            receipt_id=row.id,
            confirmation_id=row.confirmation_id,
            counts=row.counts,
            performed_at=row.performed_at,
        )

    def execute(self, actor, body: LifecycleExecute):
        with self.transaction(actor, allow_erased=True) as (db, owner):
            fingerprint = _fingerprint(body)
            prior = db.scalar(
                select(LifecycleReceipt).where(
                    LifecycleReceipt.owner_user_id == actor.user_id,
                    LifecycleReceipt.operation_key == body.operation_key,
                )
            )
            if prior:
                if prior.request_fingerprint != fingerprint:
                    raise ErasureError("idempotency_conflict")
                return self.result(prior)
            if owner.deleted_at:
                raise ErasureError("invalid_credential")
            challenge = db.scalar(
                select(LifecycleConfirmation).where(
                    LifecycleConfirmation.id == body.confirmation_id,
                    LifecycleConfirmation.owner_user_id == actor.user_id,
                )
            )
            if challenge is None:
                raise ErasureError("confirmation_not_found")
            if challenge.domain != body.domain or challenge.target_id != body.target_id:
                raise ErasureError("confirmation_mismatch")
            if challenge.consumed_at:
                raise ErasureError("confirmation_consumed")
            if challenge.expires_at <= self.clock():
                raise ErasureError("confirmation_expired")
            target, scope = self.scope(db, actor, body)
            snapshot, counts = self.snapshot(db, body, target, scope)
            if snapshot != challenge.snapshot_hash:
                raise ErasureError("target_changed")
            now = self.clock()
            # Physical unlink is retryable and monotonic. A failed SQL commit may
            # have already removed raw files; never report a successful receipt.
            for row in db.scalars(select(ChatImportArtifact).where(scope[ChatImportArtifact])):
                self.artifacts.delete(row.storage_key)
                row.state, row.updated_at = "deleted", now
            if body.domain == "owner":
                for row in db.scalars(select(UploadReservation).where(scope[UploadReservation])):
                    if row.artifact_key:
                        self.artifacts.delete(row.artifact_key)
                        partial = self.artifacts._path(row.artifact_key, partial=True)
                        if partial.is_symlink():
                            raise ArtifactStoreError()
                        partial.unlink(missing_ok=True)
                db.execute(delete(UploadReservation).where(scope[UploadReservation]))
            for model in (Message, RelationshipMessage, ChatImportSpeaker, MemoryRecordRow):
                db.execute(delete(model).where(scope[model]))
            db.execute(
                update(AgentRun)
                .where(scope[AgentRun])
                .values(memory_status=None, result_warnings=None)
            )
            db.execute(
                update(Conversation)
                .where(scope[Conversation])
                .values(deleted_at=now, updated_at=now)
            )
            db.execute(
                update(ChatImportJob)
                .where(scope[ChatImportJob])
                .values(deleted_at=now, updated_at=now)
            )
            # Cancel only unfinished imports; canonical imported dedup fences survive.
            db.execute(
                update(ChatImportJob)
                .where(scope[ChatImportJob], ChatImportJob.status != "imported")
                .values(status="cancelled")
            )
            db.execute(
                update(Relationship)
                .where(scope[Relationship])
                .values(deleted_at=now, relationship_type="erased", status="erased", updated_at=now)
            )
            db.execute(
                update(Person)
                .where(scope[Person])
                .values(deleted_at=now, display_name="", updated_at=now)
            )
            # Scope challenges are disposable derived data; receipts/key fences remain.
            affected_relationships = select(Relationship.id).where(scope[Relationship])
            affected_persons = select(Person.id).where(scope[Person])
            condition = MemoryConfirmationRow.owner_user_id == actor.user_id
            if body.domain != "owner":
                condition = condition & or_(
                    MemoryConfirmationRow.person_id.in_(affected_persons),
                    MemoryConfirmationRow.relationship_id.in_(affected_relationships),
                )
            db.execute(delete(MemoryConfirmationRow).where(condition))
            condition = ErasureConfirmation.owner_user_id == actor.user_id
            if body.domain != "owner":
                condition = condition & ErasureConfirmation.relationship_id.in_(
                    affected_relationships
                )
            db.execute(delete(ErasureConfirmation).where(condition))
            challenge.consumed_at = now
            if body.domain == "owner":
                db.execute(delete(MemoryControlRow).where(scope[MemoryControlRow]))
                # Keep only the consumed owner challenge until normal expiry cleanup.
                db.execute(
                    delete(LifecycleConfirmation).where(
                        LifecycleConfirmation.owner_user_id == actor.user_id,
                        LifecycleConfirmation.id != challenge.id,
                    )
                )
                owner.deleted_at, owner.updated_at = now, now
            row = LifecycleReceipt(
                owner_user_id=actor.user_id,
                **body.model_dump(),
                request_fingerprint=fingerprint,
                counts=counts,
                performed_at=now,
            )
            db.add(row)
            db.flush()
            return self.result(row)

    def receipt(self, actor, receipt_id):
        with self.transaction(actor, allow_erased=True) as (db, _):
            row = db.scalar(
                select(LifecycleReceipt).where(
                    LifecycleReceipt.id == receipt_id,
                    LifecycleReceipt.owner_user_id == actor.user_id,
                )
            )
            if row is None:
                raise ErasureError("not_found")
            return self.result(row)
