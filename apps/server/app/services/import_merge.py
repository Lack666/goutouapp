"""Atomic deterministic promotion of a verified transcript into relationship history."""

import json
from base64 import urlsafe_b64decode, urlsafe_b64encode
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import select, text, tuple_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.chat_import import ChatImportSource, ImportOptions
from app.chat_import.contracts import ChatParseResult, ImportedMessage
from app.chat_import.parsers import parser_for
from app.db.models import ChatImportJob, ChatImportSpeaker, RelationshipMessage
from app.db.repositories import records
from app.services.agent_service import AuthenticatedActor
from app.services.import_jobs import ImportJobService, ImportJobStatus, SpeakerBinding


class ImportMergeErrorCode(StrEnum):
    INVALID_ACTOR = "invalid_actor"
    JOB_NOT_FOUND = "job_not_found"
    JOB_NOT_READY = "job_not_ready"
    REVISION_CONFLICT = "revision_conflict"
    TRANSCRIPT_MISMATCH = "transcript_mismatch"
    BINDING_INVALID = "binding_invalid"
    PERSISTENCE_FAILED = "persistence_failed"
    DATASET_DELETED = "dataset_deleted"


class ImportMergeError(Exception):
    def __init__(self, code: ImportMergeErrorCode, issues: tuple[str, ...] = ()) -> None:
        super().__init__(code.value)
        self.code = code
        self.issues = issues


class ImportMergeStatus(StrEnum):
    IMPORTED = "imported"
    ALREADY_IMPORTED = "already_imported"


@dataclass(frozen=True)
class ImportMergeResult:
    import_job_id: UUID
    dataset_job_id: UUID
    relationship_id: UUID
    imported_message_count: int
    ignored_message_count: int
    system_message_count: int
    new_message_count: int
    first_timestamp_utc: datetime
    last_timestamp_utc: datetime
    transcript_fingerprint: str
    status: ImportMergeStatus
    imported_at: datetime


@dataclass(frozen=True)
class RelationshipMessageView:
    id: UUID
    relationship_id: UUID
    import_job_id: UUID
    source_index: int
    timestamp_utc: datetime
    original_timestamp: str
    source_timezone: str
    sender_kind: str
    person_id: UUID | None
    raw_speaker_label: str
    content: str
    content_type: str
    message_fingerprint: str


@dataclass(frozen=True)
class RelationshipMessagePage:
    items: tuple[RelationshipMessageView, ...]
    next_cursor: str | None


_STAGE_COLUMNS = (
    "source_index, message_fingerprint, raw_speaker_label, content, content_type, "
    "timestamp_utc, original_timestamp, source_timezone, source_line_start, source_line_end, "
    "external_message_id, external_reply_id, external_message_type"
)


class ImportMergeService:
    """Owns one DB transaction; a temp staging table bounds Python message memory."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _assert_integrity(
        job: ChatImportJob, speakers: tuple[ChatImportSpeaker, ...], result: ChatParseResult
    ) -> None:
        expected = (
            job.source_format,
            job.parser_version,
            job.schema_version,
            job.source_timezone,
            job.source_fingerprint,
            job.transcript_fingerprint,
            job.message_count,
            job.first_timestamp_utc,
            job.last_timestamp_utc,
            tuple((s.raw_speaker_label, s.message_count) for s in speakers),
        )
        actual = (
            result.source_format,
            result.parser_version,
            result.schema_version,
            result.source_timezone,
            result.source_fingerprint,
            result.transcript_fingerprint,
            result.message_count,
            result.first_timestamp_utc,
            result.last_timestamp_utc,
            tuple((s.raw_speaker_label, s.message_count) for s in result.speaker_counts),
        )
        if result.fatal or actual != expected:
            raise ImportMergeError(ImportMergeErrorCode.TRANSCRIPT_MISMATCH)

    @staticmethod
    def _receipt(
        requested: ChatImportJob,
        dataset: ChatImportJob,
        status: ImportMergeStatus,
        new_message_count: int,
    ) -> ImportMergeResult:
        assert dataset.bound_relationship_id is not None
        assert dataset.imported_at is not None
        assert dataset.imported_message_count is not None
        assert dataset.ignored_message_count is not None
        assert dataset.system_message_count is not None
        return ImportMergeResult(
            import_job_id=requested.id,
            dataset_job_id=dataset.id,
            relationship_id=dataset.bound_relationship_id,
            imported_message_count=dataset.imported_message_count,
            ignored_message_count=dataset.ignored_message_count,
            system_message_count=dataset.system_message_count,
            new_message_count=new_message_count,
            first_timestamp_utc=dataset.first_timestamp_utc,
            last_timestamp_utc=dataset.last_timestamp_utc,
            transcript_fingerprint=dataset.transcript_fingerprint,
            status=status,
            imported_at=dataset.imported_at,
        )

    def merge(
        self,
        *,
        actor: AuthenticatedActor,
        job_id: UUID,
        expected_revision: int,
        source: ChatImportSource,
    ) -> ImportMergeResult:
        if not isinstance(actor, AuthenticatedActor):
            raise ImportMergeError(ImportMergeErrorCode.INVALID_ACTOR)
        if (
            not isinstance(job_id, UUID)
            or type(expected_revision) is not int
            or expected_revision < 0
        ):
            raise ImportMergeError(ImportMergeErrorCode.JOB_NOT_FOUND)
        if not isinstance(source, ChatImportSource):
            raise ImportMergeError(ImportMergeErrorCode.TRANSCRIPT_MISMATCH)
        try:
            with self._session_factory() as db, db.begin():
                if records.get_user(db, actor.user_id) is None:
                    raise ImportMergeError(ImportMergeErrorCode.JOB_NOT_FOUND)
                job = db.scalar(
                    select(ChatImportJob)
                    .where(
                        ChatImportJob.id == job_id,
                        ChatImportJob.owner_user_id == actor.user_id,
                    )
                    .with_for_update()
                )
                if job is None:
                    raise ImportMergeError(ImportMergeErrorCode.JOB_NOT_FOUND)
                if job.deleted_at is not None:
                    raise ImportMergeError(ImportMergeErrorCode.DATASET_DELETED)
                if job.binding_revision != expected_revision:
                    raise ImportMergeError(ImportMergeErrorCode.REVISION_CONFLICT)
                if job.status not in (ImportJobStatus.READY, ImportJobStatus.IMPORTED):
                    raise ImportMergeError(ImportMergeErrorCode.JOB_NOT_READY)
                job_service = ImportJobService(db)
                speakers = job_service._speakers(actor.user_id, job.id)
                issues = job_service._readiness(job, speakers, include_status=False)
                if issues or len(speakers) != job.speaker_count:
                    raise ImportMergeError(ImportMergeErrorCode.BINDING_INVALID, issues)
                if (
                    job.bound_relationship_id is None
                    or records.get_relationship(db, actor.user_id, job.bound_relationship_id)
                    is None
                ):
                    raise ImportMergeError(ImportMergeErrorCode.BINDING_INVALID)

                stage = f"import_stage_{uuid4().hex}"
                db.execute(
                    text(
                        f"CREATE TEMP TABLE {stage} ("
                        "source_index integer PRIMARY KEY, "
                        "message_fingerprint varchar(64) NOT NULL, "
                        "raw_speaker_label varchar(120) NOT NULL, content text NOT NULL, "
                        "content_type varchar(16) NOT NULL, timestamp_utc timestamptz NOT NULL, "
                        "original_timestamp varchar(19) NOT NULL, "
                        "source_timezone varchar(100) NOT NULL, "
                        "source_line_start integer NOT NULL, "
                        "source_line_end integer NOT NULL, external_message_id varchar(1024), "
                        "external_reply_id varchar(1024), "
                        "external_message_type integer) ON COMMIT DROP"
                    )
                )
                batch: list[dict[str, object]] = []

                def flush_batch() -> None:
                    if batch:
                        db.execute(
                            text(
                                f"INSERT INTO {stage} ({_STAGE_COLUMNS}) VALUES ("
                                ":source_index, :message_fingerprint, :raw_speaker_label, "
                                ":content, :content_type, :timestamp_utc, "
                                ":original_timestamp, :source_timezone, "
                                ":source_line_start, :source_line_end, :external_message_id, "
                                ":external_reply_id, :external_message_type)"
                            ),
                            batch,
                        )
                        batch.clear()

                def stage_message(message: ImportedMessage) -> None:
                    batch.append(
                        {
                            "source_index": message.source_index,
                            "message_fingerprint": message.fingerprint,
                            "raw_speaker_label": message.raw_speaker_label,
                            "content": message.content,
                            "content_type": message.content_type.value,
                            "timestamp_utc": message.timestamp_utc,
                            "original_timestamp": message.original_timestamp,
                            "source_timezone": message.source_timezone,
                            "source_line_start": message.provenance.line_start,
                            "source_line_end": message.provenance.line_end,
                            "external_message_id": message.external_message_id,
                            "external_reply_id": message.external_reply_id,
                            "external_message_type": message.external_message_type,
                        }
                    )
                    if len(batch) >= 500:
                        flush_batch()

                result = parser_for(job.source_format).parse(
                    source,
                    ImportOptions(
                        source_timezone=job.source_timezone,
                        source_format=job.source_format,
                        include_messages=False,
                    ),
                    on_message=stage_message,
                )
                flush_batch()
                self._assert_integrity(job, speakers, result)
                assert job.bound_relationship_id is not None
                key = f"{actor.user_id}:{job.bound_relationship_id}:{job.transcript_fingerprint}"
                lock_key = int.from_bytes(sha256(key.encode()).digest()[:8], signed=True)
                db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})
                if job.status == ImportJobStatus.IMPORTED:
                    return self._receipt(job, job, ImportMergeStatus.ALREADY_IMPORTED, 0)
                prior = db.scalar(
                    select(ChatImportJob)
                    .where(
                        ChatImportJob.owner_user_id == actor.user_id,
                        ChatImportJob.bound_relationship_id == job.bound_relationship_id,
                        ChatImportJob.transcript_fingerprint == job.transcript_fingerprint,
                        ChatImportJob.status == ImportJobStatus.IMPORTED,
                    )
                    .limit(1)
                )
                if prior is not None:
                    if prior.deleted_at is not None:
                        raise ImportMergeError(ImportMergeErrorCode.DATASET_DELETED)
                    return self._receipt(job, prior, ImportMergeStatus.ALREADY_IMPORTED, 0)
                counts = {s.binding_kind: 0 for s in speakers}
                for speaker in speakers:
                    counts[speaker.binding_kind] = (
                        counts.get(speaker.binding_kind, 0) + speaker.message_count
                    )
                ignored = counts.get(SpeakerBinding.IGNORE, 0)
                system = counts.get(SpeakerBinding.SYSTEM, 0)
                expected_imported = job.message_count - ignored
                job.status = ImportJobStatus.IMPORTING.value
                db.flush()
                inserted = db.execute(
                    text(
                        "INSERT INTO relationship_messages ("
                        "id, created_at, updated_at, owner_user_id, relationship_id, "
                        "import_job_id, source_index, message_fingerprint, raw_speaker_label, "
                        "sender_kind, person_id, content, content_type, timestamp_utc, "
                        "original_timestamp, source_timezone, source_line_start, source_line_end, "
                        "external_message_id, external_reply_id, external_message_type) "
                        f"SELECT gen_random_uuid(), now(), now(), :owner, :relationship, :job, "
                        "st.source_index, st.message_fingerprint, st.raw_speaker_label, "
                        "sp.binding_kind, sp.person_id, st.content, st.content_type, "
                        "st.timestamp_utc, st.original_timestamp, st.source_timezone, "
                        "st.source_line_start, st.source_line_end, st.external_message_id, "
                        "st.external_reply_id, st.external_message_type "
                        f"FROM {stage} st JOIN chat_import_speakers sp "
                        "ON sp.job_id = :job AND sp.raw_speaker_label = st.raw_speaker_label "
                        "WHERE sp.binding_kind <> 'ignore' ORDER BY st.source_index"
                    ),
                    {
                        "owner": actor.user_id,
                        "relationship": job.bound_relationship_id,
                        "job": job.id,
                    },
                )
                if inserted.rowcount != expected_imported:
                    raise ImportMergeError(ImportMergeErrorCode.PERSISTENCE_FAILED)
                job.imported_message_count = expected_imported
                job.ignored_message_count = ignored
                job.system_message_count = system
                job.imported_at = datetime.now(UTC)
                job.status = ImportJobStatus.IMPORTED.value
                job.updated_at = job.imported_at
                db.flush()
                return self._receipt(job, job, ImportMergeStatus.IMPORTED, expected_imported)
        except ImportMergeError:
            raise
        except SQLAlchemyError:
            raise ImportMergeError(ImportMergeErrorCode.PERSISTENCE_FAILED) from None


def list_relationship_messages(
    db: Session,
    actor: AuthenticatedActor,
    relationship_id: UUID,
    *,
    limit: int = 100,
    offset: int = 0,
) -> tuple[RelationshipMessageView, ...]:
    if not isinstance(actor, AuthenticatedActor):
        raise ImportMergeError(ImportMergeErrorCode.INVALID_ACTOR)
    if not 1 <= limit <= 1000 or offset < 0:
        raise ValueError("invalid pagination")
    if records.get_relationship(db, actor.user_id, relationship_id) is None:
        raise ImportMergeError(ImportMergeErrorCode.JOB_NOT_FOUND)
    rows = db.scalars(
        select(RelationshipMessage)
        .where(
            RelationshipMessage.owner_user_id == actor.user_id,
            RelationshipMessage.relationship_id == relationship_id,
            RelationshipMessage.import_job_id.in_(
                select(ChatImportJob.id).where(ChatImportJob.deleted_at.is_(None))
            ),
        )
        .order_by(
            RelationshipMessage.timestamp_utc,
            RelationshipMessage.import_job_id,
            RelationshipMessage.source_index,
        )
        .offset(offset)
        .limit(limit)
    )
    return tuple(
        RelationshipMessageView(
            id=row.id,
            relationship_id=row.relationship_id,
            import_job_id=row.import_job_id,
            source_index=row.source_index,
            timestamp_utc=row.timestamp_utc,
            original_timestamp=row.original_timestamp,
            source_timezone=row.source_timezone,
            sender_kind=row.sender_kind,
            person_id=row.person_id,
            raw_speaker_label=row.raw_speaker_label,
            content=row.content,
            content_type=row.content_type,
            message_fingerprint=row.message_fingerprint,
        )
        for row in rows
    )


def page_relationship_messages(
    db: Session,
    actor: AuthenticatedActor,
    relationship_id: UUID,
    *,
    limit: int = 100,
    cursor: str | None = None,
) -> RelationshipMessagePage:
    if not isinstance(actor, AuthenticatedActor):
        raise ImportMergeError(ImportMergeErrorCode.INVALID_ACTOR)
    if not 1 <= limit <= 200:
        raise ValueError("invalid pagination")
    if records.get_relationship(db, actor.user_id, relationship_id) is None:
        raise ImportMergeError(ImportMergeErrorCode.JOB_NOT_FOUND)
    query = select(RelationshipMessage).where(
        RelationshipMessage.owner_user_id == actor.user_id,
        RelationshipMessage.relationship_id == relationship_id,
        RelationshipMessage.import_job_id.in_(
            select(ChatImportJob.id).where(ChatImportJob.deleted_at.is_(None))
        ),
    )
    scope = sha256(f"import-history-v2:{actor.user_id}:{relationship_id}".encode()).hexdigest()
    if cursor is not None:
        try:
            if not 1 <= len(cursor) <= 512:
                raise ValueError
            payload = json.loads(urlsafe_b64decode(cursor.encode("ascii") + b"=="))
            if (
                not isinstance(payload, list)
                or len(payload) != 6
                or payload[:2] != [2, scope]
                or not all(isinstance(payload[index], str) for index in (2, 3, 5))
                or type(payload[4]) is not int
            ):
                raise ValueError
            stamp = datetime.fromisoformat(payload[2])
            job_id = UUID(payload[3])
            source_index = payload[4]
            row_id = UUID(payload[5])
            if stamp.tzinfo is None or source_index < 1:
                raise ValueError
        except (ValueError, TypeError, UnicodeError, IndexError) as exc:
            raise ValueError("invalid cursor") from exc
        query = query.where(
            tuple_(
                RelationshipMessage.timestamp_utc,
                RelationshipMessage.import_job_id,
                RelationshipMessage.source_index,
                RelationshipMessage.id,
            )
            > (stamp, job_id, source_index, row_id)
        )
    rows = tuple(
        db.scalars(
            query.order_by(
                RelationshipMessage.timestamp_utc,
                RelationshipMessage.import_job_id,
                RelationshipMessage.source_index,
                RelationshipMessage.id,
            ).limit(limit + 1)
        )
    )
    has_more = len(rows) > limit
    selected = rows[:limit]
    # Existing mapper enforces owner scope; this fetch uses only selected source IDs.
    items = tuple(
        RelationshipMessageView(
            row.id,
            row.relationship_id,
            row.import_job_id,
            row.source_index,
            row.timestamp_utc,
            row.original_timestamp,
            row.source_timezone,
            row.sender_kind,
            row.person_id,
            row.raw_speaker_label,
            row.content,
            row.content_type,
            row.message_fingerprint,
        )
        for row in selected
    )
    next_cursor = None
    if has_more and selected:
        last = selected[-1]
        raw = json.dumps(
            [
                2,
                scope,
                last.timestamp_utc.isoformat(),
                str(last.import_job_id),
                last.source_index,
                str(last.id),
            ],
            separators=(",", ":"),
        ).encode("ascii")
        next_cursor = urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return RelationshipMessagePage(items, next_cursor)
