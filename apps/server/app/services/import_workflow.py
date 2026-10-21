"""One-upload import orchestration; no FastAPI request or filesystem paths escape here."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from hashlib import sha256
from typing import BinaryIO
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.chat_import import ChatImportSource, ImportOptions, WeChatMarkdownParser
from app.chat_import.artifacts import (
    CHUNK_BYTES,
    ArtifactStat,
    ArtifactStoreError,
    ImportArtifactStore,
)
from app.core.logging import LOGGER_NAME
from app.db.models import ChatImportArtifact, ChatImportJob, UploadReservation
from app.db.repositories import records
from app.retention import as_utc
from app.services.agent_service import AuthenticatedActor
from app.services.import_jobs import (
    ImportJobError,
    ImportJobErrorCode,
    ImportJobService,
    ImportJobView,
)
from app.services.import_merge import (
    ImportMergeError,
    ImportMergeErrorCode,
    ImportMergeResult,
    ImportMergeService,
    ImportMergeStatus,
)


@dataclass
class ArtifactCleanupResult:
    removed: int = 0
    orphans: int = 0
    failures: int = 0
    scanned: int = 0
    next_cursor: UUID | None = None


def _cleanup_warning() -> None:
    logging.getLogger(LOGGER_NAME).warning(
        "Import artifact cleanup deferred; maintenance retry required"
    )


class ImportWorkflowErrorCode(StrEnum):
    INVALID_UPLOAD = "invalid_upload"
    UNSUPPORTED_FORMAT = "unsupported_format"
    PARSE_FAILED = "parse_failed"
    ARTIFACT_UNAVAILABLE = "artifact_unavailable"
    TRANSCRIPT_MISMATCH = "transcript_mismatch"


class ImportWorkflowError(Exception):
    def __init__(self, code: ImportWorkflowErrorCode) -> None:
        super().__init__(code.value)
        self.code = code


def _chunks(stream: BinaryIO) -> Iterator[bytes]:
    while chunk := stream.read(CHUNK_BYTES):
        yield chunk


class ImportWorkflowService:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        store: ImportArtifactStore,
        retention_hours: int,
        max_speakers: int = 1024,
    ) -> None:
        self._sessions = session_factory
        self._store = store
        self._retention = timedelta(hours=retention_hours)
        self._max_speakers = max_speakers

    def register_uploaded(
        self,
        actor: AuthenticatedActor,
        artifact: ArtifactStat,
        *,
        source_timezone: str,
        source_format: str | None,
    ) -> ImportJobView:
        try:
            if artifact.size_bytes == 0:
                raise ImportWorkflowError(ImportWorkflowErrorCode.INVALID_UPLOAD)
            speakers = set()

            def bounded_speakers(message):
                speakers.add(message.raw_speaker_label)
                if len(speakers) > self._max_speakers:
                    raise ImportWorkflowError(ImportWorkflowErrorCode.PARSE_FAILED)

            with self._store.open(artifact.key) as stream:
                parsed = WeChatMarkdownParser().parse(
                    ChatImportSource(_chunks(stream)),
                    ImportOptions(
                        source_timezone=source_timezone,
                        source_format=source_format,
                        include_messages=False,
                    ),
                    on_message=bounded_speakers,
                )
            if parsed.fatal:
                codes = {issue.code.value for issue in parsed.issues}
                code = (
                    ImportWorkflowErrorCode.UNSUPPORTED_FORMAT
                    if "unsupported_format" in codes
                    else ImportWorkflowErrorCode.PARSE_FAILED
                )
                raise ImportWorkflowError(code)
            with self._sessions() as db, db.begin():
                row = ChatImportArtifact(
                    owner_user_id=actor.user_id,
                    storage_key=artifact.key,
                    source_format=parsed.source_format,
                    size_bytes=artifact.size_bytes,
                    content_hash=artifact.content_hash,
                    expires_at=datetime.now(UTC) + self._retention,
                    state="active",
                )
                db.add(row)
                db.flush()
                return ImportJobService(db).create(actor, parsed, artifact_id=row.id)
        except BaseException as exc:
            try:
                self._store.delete(artifact.key)
            except (OSError, ArtifactStoreError):
                _cleanup_warning()
            if isinstance(exc, SQLAlchemyError):
                raise ImportMergeError(ImportMergeErrorCode.PERSISTENCE_FAILED) from None
            raise

    def _owned_job(self, db: Session, actor: AuthenticatedActor, job_id: UUID) -> ChatImportJob:
        if records.get_user(db, actor.user_id) is None:
            raise ImportJobError(ImportJobErrorCode.JOB_NOT_FOUND)
        job = db.scalar(
            select(ChatImportJob).where(
                ChatImportJob.id == job_id, ChatImportJob.owner_user_id == actor.user_id
            )
        )
        if job is None:
            raise ImportJobError(ImportJobErrorCode.JOB_NOT_FOUND)
        return job

    def _artifact(
        self, db: Session, actor: AuthenticatedActor, job: ChatImportJob
    ) -> ChatImportArtifact:
        if job.artifact_id is None:
            raise ImportWorkflowError(ImportWorkflowErrorCode.ARTIFACT_UNAVAILABLE)
        row = db.scalar(
            select(ChatImportArtifact).where(
                ChatImportArtifact.id == job.artifact_id,
                ChatImportArtifact.owner_user_id == actor.user_id,
            )
        )
        if row is None:
            raise ImportWorkflowError(ImportWorkflowErrorCode.ARTIFACT_UNAVAILABLE)
        return row

    def inspect(self, actor: AuthenticatedActor, job_id: UUID) -> ImportJobView:
        with self._sessions() as db:
            return ImportJobService(db).inspect(actor, job_id)

    def finalize(
        self, actor: AuthenticatedActor, job_id: UUID, expected_revision: int
    ) -> ImportMergeResult:
        with self._sessions() as db:
            job = self._owned_job(db, actor, job_id)
            if job.deleted_at is not None:
                raise ImportMergeError(ImportMergeErrorCode.DATASET_DELETED)
            if job.binding_revision != expected_revision:
                raise ImportMergeError(ImportMergeErrorCode.REVISION_CONFLICT)
            if job.status == "imported":
                return ImportMergeService._receipt(job, job, ImportMergeStatus.ALREADY_IMPORTED, 0)
            if job.status != "ready":
                raise ImportMergeError(ImportMergeErrorCode.JOB_NOT_READY)
            artifact = self._artifact(db, actor, job)
            if artifact.state != "active" or artifact.expires_at <= datetime.now(UTC):
                raise ImportWorkflowError(ImportWorkflowErrorCode.ARTIFACT_UNAVAILABLE)
            key, expected_hash, expected_size = (
                artifact.storage_key,
                artifact.content_hash,
                artifact.size_bytes,
            )
        try:
            with self._store.open(key) as stream:
                digest = sha256()
                size = 0
                for chunk in _chunks(stream):
                    digest.update(chunk)
                    size += len(chunk)
                if size != expected_size or digest.hexdigest() != expected_hash:
                    raise ImportWorkflowError(ImportWorkflowErrorCode.TRANSCRIPT_MISMATCH)
                stream.seek(0)
                result = ImportMergeService(self._sessions).merge(
                    actor=actor,
                    job_id=job_id,
                    expected_revision=expected_revision,
                    source=ChatImportSource(_chunks(stream)),
                )
        except ArtifactStoreError:
            # A concurrent finalize may have imported and removed this same artifact.
            with self._sessions() as db:
                current = self._owned_job(db, actor, job_id)
                if current.deleted_at is not None:
                    raise ImportMergeError(ImportMergeErrorCode.DATASET_DELETED) from None
                if current.status == "imported" and current.binding_revision == expected_revision:
                    return ImportMergeService._receipt(
                        current, current, ImportMergeStatus.ALREADY_IMPORTED, 0
                    )
            raise ImportWorkflowError(ImportWorkflowErrorCode.ARTIFACT_UNAVAILABLE) from None
        if result.status == ImportMergeStatus.IMPORTED:
            self._delete_artifact(actor, job_id, key)
        return result

    def _delete_artifact(self, actor: AuthenticatedActor, job_id: UUID, key: str) -> None:
        try:
            self._store.delete(key)
            with self._sessions() as db, db.begin():
                job = self._owned_job(db, actor, job_id)
                artifact = self._artifact(db, actor, job)
                if artifact.storage_key == key:
                    artifact.state = "deleted"
                    artifact.updated_at = datetime.now(UTC)
        except (OSError, ArtifactStoreError, SQLAlchemyError):
            # Formal receipt is already durable. Maintenance can reconcile an
            # active metadata row or orphaned file without reimporting data.
            _cleanup_warning()
            return

    def cancel(self, actor: AuthenticatedActor, job_id: UUID) -> ImportJobView:
        with self._sessions() as db, db.begin():
            service = ImportJobService(db)
            service.cancel(actor, job_id)
            job = self._owned_job(db, actor, job_id)
            key = self._artifact(db, actor, job).storage_key if job.artifact_id else None
        if key:
            self._delete_artifact(actor, job_id, key)
        return self.inspect(actor, job_id)

    def cleanup_expired(self, *, now: datetime | None = None) -> tuple[int, int]:
        """Compatibility one-shot; scheduled maintenance uses detailed cleanup_pass."""
        result = self.cleanup_pass(now=now)
        return result.removed, result.orphans

    def cleanup_pass(
        self,
        *,
        now: datetime | None = None,
        batch_size: int = 100,
        max_batches: int = 100,
        start_after: UUID | None = None,
    ) -> ArtifactCleanupResult:
        if not 1 <= batch_size <= 1000 or not 1 <= max_batches <= 10000:
            raise ValueError("Invalid artifact cleanup bounds")
        now = as_utc(now or datetime.now(UTC))
        result = ArtifactCleanupResult()
        cursor = start_after
        for _ in range(max_batches):
            with self._sessions() as db:
                query = (
                    select(ChatImportArtifact.id).order_by(ChatImportArtifact.id).limit(batch_size)
                )
                if cursor is not None:
                    query = query.where(ChatImportArtifact.id > cursor)
                ids = list(db.scalars(query))
            if not ids:
                cursor = None
                break
            for artifact_id in ids:
                # Merge/cancel lock Job first. Use that same order, then recheck
                # Artifact state under lock before any irreversible filesystem work.
                with self._sessions() as db, db.begin():
                    db.execute(text("SET LOCAL lock_timeout = '1000ms'"))
                    db.execute(text("SET LOCAL statement_timeout = '5000ms'"))
                    job = db.scalar(
                        select(ChatImportJob)
                        .where(ChatImportJob.artifact_id == artifact_id)
                        .with_for_update()
                    )
                    row = db.scalar(
                        select(ChatImportArtifact)
                        .where(ChatImportArtifact.id == artifact_id)
                        .with_for_update()
                    )
                    if row is None:
                        continue
                    expired = row.expires_at <= now
                    terminal = job is not None and job.status in {"imported", "cancelled"}
                    physical = self._store.exists(row.storage_key)
                    invalid = row.state != "active" or not physical
                    if expired or terminal or invalid:
                        if job is not None and job.status in {"ready", "awaiting_binding"}:
                            job.status = "cancelled"
                            job.updated_at = now
                        try:
                            self._store.delete(row.storage_key)
                        except (OSError, ArtifactStoreError):
                            result.failures += 1
                            _cleanup_warning()
                        else:
                            # State never releases quota: actual disk inventory does.
                            row.state = "expired" if expired else "deleted"
                            row.updated_at = now
                            result.removed += int(physical)
                result.scanned += 1
            cursor = ids[-1]
            if len(ids) < batch_size:
                cursor = None
                break
        result.next_cursor = cursor
        with self._sessions() as db:
            live_keys = set(
                db.scalars(
                    select(ChatImportArtifact.storage_key).where(
                        ChatImportArtifact.state == "active", ChatImportArtifact.expires_at > now
                    )
                )
            )
            live_keys.update(
                db.scalars(
                    select(UploadReservation.artifact_key).where(
                        UploadReservation.active.is_(True),
                        UploadReservation.artifact_key.is_not(None),
                    )
                )
            )
        try:
            result.orphans = self._store.cleanup_expired(live_keys, now - timedelta(hours=1))
        except (OSError, ArtifactStoreError):
            _cleanup_warning()
            result.failures += 1
        return result
