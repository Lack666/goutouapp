"""Narrow public contracts over the existing resource and Agent message records."""

import unicodedata
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import UUID4, BaseModel, ConfigDict, Field, field_validator

Name = Annotated[str, Field(strict=True, min_length=1, max_length=120)]
Label = Annotated[str, Field(strict=True, min_length=1, max_length=40)]


class PublicResourceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class ResourceCreateRequest(PublicResourceModel):
    id: UUID4 = Field(description="Fresh UUID v4 for one creation; retain on every retry.")

    @field_validator("display_name", "relationship_type", "status", check_fields=False)
    @classmethod
    def normalize_label(cls, value: str) -> str:
        value = unicodedata.normalize("NFC", value.strip())
        if not value or any(unicodedata.category(char) == "Cc" for char in value):
            raise ValueError("Invalid resource label")
        value.encode("utf-8")
        return value


class PersonCreateRequest(ResourceCreateRequest):
    display_name: Name


class RelationshipCreateRequest(ResourceCreateRequest):
    person_id: UUID
    relationship_type: Label = Field(description="Explicit caller label; unknown is allowed.")
    status: Label = Field(description="Explicit caller label; no inferred relationship state.")


class ConversationCreateRequest(ResourceCreateRequest):
    relationship_id: UUID | None = None


class ResourceResponse(PublicResourceModel):
    id: UUID
    created_at: datetime
    updated_at: datetime


class PersonResponse(ResourceResponse):
    display_name: str


class RelationshipResponse(ResourceResponse):
    person_id: UUID
    relationship_type: str
    status: str


class ConversationResponse(ResourceResponse):
    relationship_id: UUID | None


class AgentMessagePublicResponse(PublicResourceModel):
    id: UUID
    conversation_id: UUID
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class PageRequest(PublicResourceModel):
    limit: int = Field(default=30, ge=1, le=100)
    cursor: str | None = Field(default=None, min_length=1, max_length=512)


class PersonPage(PublicResourceModel):
    items: list[PersonResponse] = Field(max_length=100)
    next_cursor: str | None


class RelationshipPage(PublicResourceModel):
    items: list[RelationshipResponse] = Field(max_length=100)
    next_cursor: str | None


class ConversationPage(PublicResourceModel):
    items: list[ConversationResponse] = Field(max_length=100)
    next_cursor: str | None


class AgentMessagePage(PublicResourceModel):
    items: list[AgentMessagePublicResponse] = Field(max_length=100)
    next_cursor: str | None


class DatasetSummary(PublicResourceModel):
    dataset_job_id: UUID
    relationship_id: UUID
    source_format: str
    parser_version: str
    source_timezone: str
    first_timestamp_utc: datetime
    last_timestamp_utc: datetime
    imported_message_count: int
    current_message_count: int
    ignored_message_count: int
    system_message_count: int
    imported_at: datetime
    deleted_at: datetime | None
    deletable: bool


class DatasetPage(PublicResourceModel):
    items: list[DatasetSummary] = Field(max_length=100)
    next_cursor: str | None
