"""Shared shape for basic HTTP errors."""

from uuid import UUID

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    run_id: UUID | None = None
    recovery_status: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
