"""Explicit scope and server challenge; no client confirmation boolean."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.agent_service import valid_operation_key


class ErasureTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    domain: Literal["dataset", "conversation"]
    target_id: UUID
    relationship_id: UUID | None = None


class ErasureExecute(ErasureTarget):
    confirmation_id: UUID
    operation_key: str = Field(min_length=1, max_length=128)

    @field_validator("operation_key")
    @classmethod
    def valid_key(cls, value):
        if not valid_operation_key(value):
            raise ValueError("Invalid operation key")
        return value


class ErasureChallenge(ErasureTarget):
    confirmation_id: UUID
    message_count: int
    run_count: int
    expires_at: datetime
    memory_affected: Literal[False] = False
    retained_metadata: str = "Target tombstone, original operation keys and metadata-only receipts"


class ErasureResult(ErasureTarget):
    receipt_id: UUID
    confirmation_id: UUID
    message_count: int
    run_count: int
    performed_at: datetime
    status: Literal["deleted"] = "deleted"
    memory_affected: Literal[False] = False
