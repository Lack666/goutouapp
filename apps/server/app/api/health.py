"""Unversioned liveness endpoint."""

from fastapi import APIRouter

from app.schemas.status import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse()
