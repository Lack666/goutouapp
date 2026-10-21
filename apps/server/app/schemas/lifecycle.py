"""Separate full-scope contract; existing exact Dataset/Conversation DTOs stay intact."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.agent_service import valid_operation_key


class LifecycleTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")
    domain: Literal["person", "relationship", "owner"]
    target_id: UUID


class MobileLifecycleTarget(LifecycleTarget):
    domain: Literal["person", "relationship"]


class LifecycleExecute(LifecycleTarget):
    confirmation_id: UUID
    operation_key: str = Field(min_length=1, max_length=128)

    @field_validator("operation_key")
    @classmethod
    def valid_key(cls, value):
        if not valid_operation_key(value):
            raise ValueError("Invalid operation key")
        return value


class MobileLifecycleExecute(LifecycleExecute):
    domain: Literal["person", "relationship"]


class LifecycleChallenge(LifecycleTarget):
    confirmation_id: UUID
    counts: dict[str, int]
    expires_at: datetime
    memory_policy: Literal["delete_exact_structured_scope"] = "delete_exact_structured_scope"
    scope_notice: str = (
        "Primary scoped data and raw artifacts; UUID/key/receipt fences retained. "
        "Backups and external copies are separate."
    )


class LifecycleResult(LifecycleTarget):
    receipt_id: UUID
    confirmation_id: UUID
    counts: dict[str, int]
    performed_at: datetime
    status: Literal["deleted"] = "deleted"
    primary_store_only: Literal[True] = True
