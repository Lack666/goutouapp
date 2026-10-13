"""One-upload import orchestration; no FastAPI request or filesystem paths escape here."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from hashlib import sha256
from typing import BinaryIO
from uuid import UUID

from sqlalchemy import select
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
        """Explicit maintenance operation; no background scheduler is implied."""
        now = now or datetime.now(UTC)
        with self._sessions() as db, db.begin():
            artifacts = tuple(
                db.scalars(select(ChatImportArtifact).where(ChatImportArtifact.state == "active"))
            )
            cleanup: list[str] = []
            for artifact in artifacts:
                job = db.scalar(
                    select(ChatImportJob).where(ChatImportJob.artifact_id == artifact.id)
                )
                expired = artifact.expires_at <= now
                terminal = job is not None and job.status in {"imported", "cancelled"}
                if expired or terminal:
                    if expired and job is not None and job.status in {"ready", "awaiting_binding"}:
                        job.status = "cancelled"
                        job.updated_at = now
                    artifact.state = "expired" if expired else "deleted"
                    artifact.updated_at = now
                    cleanup.append(artifact.storage_key)
            live_keys = {row.storage_key for row in artifacts if row.state == "active"}
            # A pre-registration upload has no Artifact row yet. Its admission
            # fence protects .part/.bin even if a maintenance grace elapses.
            live_keys.update(
                db.scalars(
                    select(UploadReservation.artifact_key).where(
                        UploadReservation.active.is_(True),
                        UploadReservation.artifact_key.is_not(None),
                    )
                )
            )
        removed = 0
        for key in cleanup:
            try:
                self._store.delete(key)
                removed += 1
            except (OSError, ArtifactStoreError):
                _cleanup_warning()
        try:
            orphans = self._store.cleanup_expired(live_keys, now - timedelta(hours=1))
        except (OSError, ArtifactStoreError):
            _cleanup_warning()
            orphans = 0
        return removed, orphans
