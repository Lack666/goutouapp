"""Scope-only preparation endpoints; there is deliberately no execute request."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CalendarSelection(Strict):
    days: Literal[3, 7] | None = None
    first: date | None = None
    last: date | None = None

    @model_validator(mode="after")
    def exclusive(self):
        if self.days is not None:
            if self.first is not None or self.last is not None:
                raise ValueError("select calendar preset or custom dates")
        elif self.first is None or self.last is None or self.first > self.last:
            raise ValueError("custom range required")
        return self


class AnalysisPrepare(Strict):
    dataset_id: UUID
    relationship_id: UUID
    person_id: UUID
    timezone: str = Field(min_length=1, max_length=100)
    windows: list[CalendarSelection] = Field(min_length=1, max_length=2)
    question: str = Field(min_length=1, max_length=2000)
    model: str = Field(min_length=1, max_length=100)
    max_tokens: int = Field(gt=0, le=100_000_000)
    max_requests: int = Field(gt=0, le=104)


class AnalysisConfirm(Strict):
    preparation_id: UUID
    challenge: str = Field(min_length=32, max_length=128)
    binding_hash: str = Field(min_length=64, max_length=64)
    operation_key: str = Field(pattern=r"^[A-Za-z0-9_.:-]{1,128}$")
    confirmed: Literal[True]

    @field_validator("confirmed", mode="before")
    @classmethod
    def explicit_boolean(cls, value):
        if value is not True:
            raise ValueError("explicit confirmation required")
        return value


class EvidenceRequest(Strict):
    start: int = Field(ge=0, strict=True)
    end: int = Field(gt=0, strict=True)
    quote: str = Field(min_length=1, max_length=20000)


class AnalysisPreparation(Strict):
    preparation_id: UUID
    challenge: str
    binding_hash: str
    expires_at: datetime
    preview: dict
    provider_calls: Literal[0] = 0


class AnalysisGrantView(Strict):
    grant_id: UUID
    status: str
    expires_at: datetime
    binding_hash: str
    preview: dict
    manifests: list[dict]
    evidence_aliases: dict
    provider_calls: Literal[0] = 0


class EvidenceView(Strict):
    alias: str
    message_id: UUID
    dataset_id: UUID
    source_index: int
    speaker: str
    timestamp: datetime
    content: str
    quote: str
    line_start: int
    line_end: int
    external_message_id: str | None
    external_reply_id: str | None
