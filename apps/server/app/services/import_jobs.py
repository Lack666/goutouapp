"""Transport-independent, owner-scoped import job and binding workflow."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chat_import.contracts import ChatParseResult
from app.db.models import ChatImportArtifact, ChatImportJob, ChatImportSpeaker
from app.db.repositories import records
from app.services.agent_service import AuthenticatedActor


class ImportJobStatus(StrEnum):
    AWAITING_BINDING = "awaiting_binding"
    READY = "ready"
    IMPORTING = "importing"
    IMPORTED = "imported"
    CANCELLED = "cancelled"


class SpeakerBinding(StrEnum):
    UNBOUND = "unbound"
    SELF = "self"
    PERSON = "person"
    SYSTEM = "system"
    IGNORE = "ignore"


class ImportJobErrorCode(StrEnum):
    INVALID_ACTOR = "invalid_actor"
    INVALID_PARSE_RESULT = "invalid_parse_result"
    FATAL_PARSE_RESULT = "fatal_parse_result"
    JOB_NOT_FOUND = "job_not_found"
    JOB_CANCELLED = "job_cancelled"
    JOB_IMPORTED = "job_imported"
    SPEAKER_NOT_FOUND = "speaker_not_found"
    PERSON_NOT_FOUND = "person_not_found"
    RELATIONSHIP_NOT_FOUND = "relationship_not_found"
    INVALID_BINDING = "invalid_binding"
    REVISION_CONFLICT = "revision_conflict"
    NOT_READY = "not_ready"


class ImportJobError(Exception):
    def __init__(self, code: ImportJobErrorCode, issues: tuple[str, ...] = ()) -> None:
        super().__init__(code.value)
        self.code = code
        self.issues = issues


@dataclass(frozen=True)
class SpeakerView:
    raw_speaker_label: str
    message_count: int
    binding_kind: SpeakerBinding
    person_id: UUID | None


@dataclass(frozen=True)
class ImportJobView:
    id: UUID
    artifact_id: UUID | None
    artifact_state: str | None
    owner_user_id: UUID
    status: ImportJobStatus
    source_format: str
    parser_version: str
    schema_version: str
    source_timezone: str
    source_fingerprint: str
    transcript_fingerprint: str
    message_count: int
    speaker_count: int
    first_timestamp_utc: datetime
    last_timestamp_utc: datetime
    warning_count: int
    error_count: int
    issues_truncated: int
    issue_code_samples: tuple[str, ...]
    bound_relationship_id: UUID | None
    binding_revision: int
    imported_message_count: int | None
    ignored_message_count: int | None
    system_message_count: int | None
    imported_at: datetime | None
    possible_duplicate_job_id: UUID | None
    created_at: datetime
    updated_at: datetime
    speakers: tuple[SpeakerView, ...]
    readiness_issues: tuple[str, ...]


class ImportJobService:
    """Mutations flush in the caller's transaction; the caller commits."""

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _owner(actor: AuthenticatedActor) -> UUID:
        if not isinstance(actor, AuthenticatedActor):
            raise ImportJobError(ImportJobErrorCode.INVALID_ACTOR)
        return actor.user_id

    def _job(self, owner: UUID, job_id: UUID, *, lock: bool = False) -> ChatImportJob:
        if records.get_user(self.db, owner) is None:
            raise ImportJobError(ImportJobErrorCode.JOB_NOT_FOUND)
        query = select(ChatImportJob).where(
            ChatImportJob.id == job_id, ChatImportJob.owner_user_id == owner
        )
        job = self.db.scalar(query.with_for_update() if lock else query)
        if job is None:
            raise ImportJobError(ImportJobErrorCode.JOB_NOT_FOUND)
        if job.deleted_at is not None and job.status != "imported":
            raise ImportJobError(ImportJobErrorCode.JOB_NOT_FOUND)
        return job

    def _speakers(self, owner: UUID, job_id: UUID) -> tuple[ChatImportSpeaker, ...]:
        return tuple(
            self.db.scalars(
                select(ChatImportSpeaker)
                .where(ChatImportSpeaker.owner_user_id == owner, ChatImportSpeaker.job_id == job_id)
                .order_by(ChatImportSpeaker.source_order)
            )
        )

    @staticmethod
    def _validate_parse(result: ChatParseResult) -> None:
        if not isinstance(result, ChatParseResult):
            raise ImportJobError(ImportJobErrorCode.INVALID_PARSE_RESULT)
        if result.fatal:
            raise ImportJobError(ImportJobErrorCode.FATAL_PARSE_RESULT)
        if (
            not result.source_format
            or not result.source_timezone
            or not result.parser_version
            or not result.schema_version
            or not result.source_fingerprint
            or not result.transcript_fingerprint
            or not result.first_timestamp_utc
            or not result.last_timestamp_utc
            or result.message_count < 1
            or not result.speaker_counts
            or sum(s.message_count for s in result.speaker_counts) != result.message_count
            or len({s.raw_speaker_label for s in result.speaker_counts})
            != len(result.speaker_counts)
            or any(not s.raw_speaker_label or s.message_count < 1 for s in result.speaker_counts)
        ):
            raise ImportJobError(ImportJobErrorCode.INVALID_PARSE_RESULT)

    def create(
        self, actor: AuthenticatedActor, result: ChatParseResult, *, artifact_id: UUID | None = None
    ) -> ImportJobView:
        owner = self._owner(actor)
        self._validate_parse(result)
        if records.get_user(self.db, owner) is None:
            raise ImportJobError(ImportJobErrorCode.INVALID_ACTOR)
        if artifact_id is not None:
            artifact = self.db.get(ChatImportArtifact, artifact_id)
            if artifact is None or artifact.owner_user_id != owner or artifact.state != "active":
                raise ImportJobError(ImportJobErrorCode.INVALID_PARSE_RESULT)
        prior = self.db.scalar(
            select(ChatImportJob.id)
            .where(
                ChatImportJob.owner_user_id == owner,
                ChatImportJob.transcript_fingerprint == result.transcript_fingerprint,
            )
            .order_by(ChatImportJob.created_at, ChatImportJob.id)
            .limit(1)
        )
        codes = list(dict.fromkeys(issue.code.value for issue in result.issues))[:20]
        job = ChatImportJob(
            owner_user_id=owner,
            artifact_id=artifact_id,
            status=ImportJobStatus.AWAITING_BINDING.value,
            source_format=result.source_format,
            parser_version=result.parser_version,
            schema_version=result.schema_version,
            source_timezone=result.source_timezone,
            source_fingerprint=result.source_fingerprint,
            transcript_fingerprint=result.transcript_fingerprint,
            message_count=result.message_count,
            speaker_count=len(result.speaker_counts),
            first_timestamp_utc=result.first_timestamp_utc,
            last_timestamp_utc=result.last_timestamp_utc,
            warning_count=result.warning_count,
            error_count=result.error_count,
            issues_truncated=result.issues_truncated,
            issue_code_samples=codes,
            binding_revision=0,
        )
        self.db.add(job)
        self.db.flush()
        for source_order, speaker in enumerate(result.speaker_counts):
            self.db.add(
                ChatImportSpeaker(
                    owner_user_id=owner,
                    job_id=job.id,
                    raw_speaker_label=speaker.raw_speaker_label,
                    source_order=source_order,
                    message_count=speaker.message_count,
                    binding_kind=SpeakerBinding.UNBOUND.value,
                )
            )
        self.db.flush()
        return self._view(job, prior)

    def _readiness(
        self,
        job: ChatImportJob,
        speakers: tuple[ChatImportSpeaker, ...],
        *,
        include_status: bool = True,
    ) -> tuple[str, ...]:
        issues: list[str] = []
        if include_status and job.status == ImportJobStatus.CANCELLED:
            return ("job_cancelled",)
        if include_status and job.status in (ImportJobStatus.IMPORTING, ImportJobStatus.IMPORTED):
            return ("job_imported",)
        if not all(
            (
                job.source_format,
                job.parser_version,
                job.schema_version,
                job.source_timezone,
                job.source_fingerprint,
                job.transcript_fingerprint,
                job.first_timestamp_utc,
                job.last_timestamp_utc,
            )
        ):
            issues.append("transcript_metadata_incomplete")
        kinds = [speaker.binding_kind for speaker in speakers]
        if kinds.count(SpeakerBinding.SELF) != 1:
            issues.append("exactly_one_self_required")
        if kinds.count(SpeakerBinding.PERSON) == 0:
            issues.append("exactly_one_primary_person_required")
        elif kinds.count(SpeakerBinding.PERSON) > 1:
            issues.append("unsupported_group_binding")
        if SpeakerBinding.UNBOUND in kinds:
            issues.append("unbound_speakers")
        if job.bound_relationship_id is None:
            issues.append("relationship_required")
        else:
            relationship = records.get_relationship(
                self.db, job.owner_user_id, job.bound_relationship_id
            )
            if relationship is None:
                issues.append("relationship_scope_invalid")
            elif kinds.count(SpeakerBinding.PERSON) == 1:
                person_id = next(
                    s.person_id for s in speakers if s.binding_kind == SpeakerBinding.PERSON
                )
                if person_id != relationship.person_id:
                    issues.append("relationship_person_mismatch")
        return tuple(issues)

    def _view(self, job: ChatImportJob, prior: UUID | None = None) -> ImportJobView:
        speakers = self._speakers(job.owner_user_id, job.id)
        return ImportJobView(
            id=job.id,
            artifact_id=job.artifact_id,
            artifact_state=(
                self.db.get(ChatImportArtifact, job.artifact_id).state
                if job.artifact_id is not None
                else None
            ),
            owner_user_id=job.owner_user_id,
            status=ImportJobStatus(job.status),
            source_format=job.source_format,
            parser_version=job.parser_version,
            schema_version=job.schema_version,
            source_timezone=job.source_timezone,
            source_fingerprint=job.source_fingerprint,
            transcript_fingerprint=job.transcript_fingerprint,
            message_count=job.message_count,
            speaker_count=job.speaker_count,
            first_timestamp_utc=job.first_timestamp_utc,
            last_timestamp_utc=job.last_timestamp_utc,
            warning_count=job.warning_count,
            error_count=job.error_count,
            issues_truncated=job.issues_truncated,
            issue_code_samples=tuple(job.issue_code_samples),
            bound_relationship_id=job.bound_relationship_id,
            binding_revision=job.binding_revision,
            imported_message_count=job.imported_message_count,
            ignored_message_count=job.ignored_message_count,
            system_message_count=job.system_message_count,
            imported_at=job.imported_at,
            possible_duplicate_job_id=prior,
            created_at=job.created_at,
            updated_at=job.updated_at,
            speakers=tuple(
                SpeakerView(
                    s.raw_speaker_label,
                    s.message_count,
                    SpeakerBinding(s.binding_kind),
                    s.person_id,
                )
                for s in speakers
            ),
            readiness_issues=self._readiness(job, speakers),
        )

    def inspect(self, actor: AuthenticatedActor, job_id: UUID) -> ImportJobView:
        return self._view(self._job(self._owner(actor), job_id))

    def list_speakers(self, actor: AuthenticatedActor, job_id: UUID) -> tuple[SpeakerView, ...]:
        return self.inspect(actor, job_id).speakers

    def validate_readiness(self, actor: AuthenticatedActor, job_id: UUID) -> tuple[str, ...]:
        return self.inspect(actor, job_id).readiness_issues

    @staticmethod
    def _touch(job: ChatImportJob) -> None:
        job.binding_revision += 1
        job.updated_at = datetime.now(UTC)
        job.status = ImportJobStatus.AWAITING_BINDING.value

    @staticmethod
    def _editable(job: ChatImportJob, expected_revision: int | None) -> None:
        if job.status == ImportJobStatus.CANCELLED:
            raise ImportJobError(ImportJobErrorCode.JOB_CANCELLED)
        if job.status in (ImportJobStatus.IMPORTING, ImportJobStatus.IMPORTED):
            raise ImportJobError(ImportJobErrorCode.JOB_IMPORTED)
        if expected_revision is not None and job.binding_revision != expected_revision:
            raise ImportJobError(ImportJobErrorCode.REVISION_CONFLICT)

    def set_speaker_binding(
        self,
        actor: AuthenticatedActor,
        job_id: UUID,
        raw_speaker_label: str,
        binding: SpeakerBinding,
        person_id: UUID | None = None,
        *,
        expected_revision: int | None = None,
    ) -> ImportJobView:
        owner = self._owner(actor)
        job = self._job(owner, job_id, lock=True)
        self._editable(job, expected_revision)
        if not isinstance(binding, SpeakerBinding) or (
            (binding == SpeakerBinding.PERSON) != (person_id is not None)
        ):
            raise ImportJobError(ImportJobErrorCode.INVALID_BINDING)
        speaker = self.db.scalar(
            select(ChatImportSpeaker).where(
                ChatImportSpeaker.owner_user_id == owner,
                ChatImportSpeaker.job_id == job_id,
                ChatImportSpeaker.raw_speaker_label == raw_speaker_label,
            )
        )
        if speaker is None:
            raise ImportJobError(ImportJobErrorCode.SPEAKER_NOT_FOUND)
        if person_id is not None and records.get_person(self.db, owner, person_id) is None:
            raise ImportJobError(ImportJobErrorCode.PERSON_NOT_FOUND)
        speaker.binding_kind = binding.value
        speaker.person_id = person_id
        speaker.updated_at = datetime.now(UTC)
        self._touch(job)
        self.db.flush()
        return self._view(job)

    def set_relationship_binding(
        self,
        actor: AuthenticatedActor,
        job_id: UUID,
        relationship_id: UUID | None,
        *,
        expected_revision: int | None = None,
    ) -> ImportJobView:
        owner = self._owner(actor)
        job = self._job(owner, job_id, lock=True)
        self._editable(job, expected_revision)
        if (
            relationship_id is not None
            and records.get_relationship(self.db, owner, relationship_id) is None
        ):
            raise ImportJobError(ImportJobErrorCode.RELATIONSHIP_NOT_FOUND)
        job.bound_relationship_id = relationship_id
        self._touch(job)
        self.db.flush()
        return self._view(job)

    def mark_ready(self, actor: AuthenticatedActor, job_id: UUID) -> ImportJobView:
        owner = self._owner(actor)
        job = self._job(owner, job_id, lock=True)
        self._editable(job, None)
        issues = self._readiness(job, self._speakers(owner, job_id))
        if issues:
            raise ImportJobError(ImportJobErrorCode.NOT_READY, issues)
        job.status = ImportJobStatus.READY.value
        job.updated_at = datetime.now(UTC)
        self.db.flush()
        return self._view(job)

    def cancel(self, actor: AuthenticatedActor, job_id: UUID) -> ImportJobView:
        job = self._job(self._owner(actor), job_id, lock=True)
        self._editable(job, None)
        job.status = ImportJobStatus.CANCELLED.value
        job.updated_at = datetime.now(UTC)
        self.db.flush()
        return self._view(job)
