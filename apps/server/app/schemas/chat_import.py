"""Public import transport models; no raw source or storage key."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.services.import_jobs import SpeakerBinding
from app.services.import_merge import ImportMergeStatus


class SpeakerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    raw_speaker_label: str
    message_count: int
    binding_kind: SpeakerBinding
    person_id: UUID | None


class ImportJobReceiptSummary(BaseModel):
    dataset_job_id: UUID
    relationship_id: UUID
    imported_message_count: int
    ignored_message_count: int
    system_message_count: int
    imported_at: datetime
    transcript_fingerprint: str


class ImportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    artifact_id: UUID | None
    artifact_state: str | None
    status: str
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
    speakers: tuple[SpeakerResponse, ...]
    readiness_issues: tuple[str, ...]

    @computed_field
    @property
    def receipt(self) -> ImportJobReceiptSummary | None:
        if (
            self.status != "imported"
            or self.bound_relationship_id is None
            or self.imported_message_count is None
            or self.ignored_message_count is None
            or self.system_message_count is None
            or self.imported_at is None
        ):
            return None
        return ImportJobReceiptSummary(
            dataset_job_id=self.id,
            relationship_id=self.bound_relationship_id,
            imported_message_count=self.imported_message_count,
            ignored_message_count=self.ignored_message_count,
            system_message_count=self.system_message_count,
            imported_at=self.imported_at,
            transcript_fingerprint=self.transcript_fingerprint,
        )


class SpeakerBindingRequest(BaseModel):
    raw_speaker_label: str = Field(min_length=1, max_length=120)
    binding_kind: SpeakerBinding
    person_id: UUID | None = None
    expected_revision: int = Field(ge=0)


class RelationshipBindingRequest(BaseModel):
    relationship_id: UUID | None
    expected_revision: int = Field(ge=0)


class FinalizeRequest(BaseModel):
    expected_revision: int = Field(ge=0)


class ImportReceiptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
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


class RelationshipMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
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


class RelationshipMessagePageResponse(BaseModel):
    items: tuple[RelationshipMessageResponse, ...]
    next_cursor: str | None
