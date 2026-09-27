"""Versioned service status."""

from fastapi import APIRouter, Request

from app.schemas.status import StatusResponse

router = APIRouter()


@router.get("/status", response_model=StatusResponse, tags=["status"])
def status(request: Request) -> StatusResponse:
    settings = request.app.state.settings
    return StatusResponse(environment=settings.app_env)
