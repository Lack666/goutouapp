"""Thin signed-JWT transport for memory controls and owner-scoped inspection."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict

from app.api.dependencies import get_authenticated_actor
from app.db.repositories.memory import SQLAlchemyMemoryStore
from app.services.agent_service import AuthenticatedActor
from app.services.memory_control import (
    MemoryControlService,
    MemoryControlView,
    MemoryListResult,
    MemoryRecordView,
)

router = APIRouter(tags=["memory"])


class ConsentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


def _service(request: Request) -> MemoryControlService:
    return MemoryControlService(SQLAlchemyMemoryStore(request.app.state.database.session))


@router.get("/memory/control", response_model=MemoryControlView)
def inspect_control(
    actor: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],
    service: Annotated[MemoryControlService, Depends(_service)],
) -> MemoryControlView:
    return service.inspect_control(actor)


@router.post("/memory/consent", response_model=MemoryControlView)
def change_consent(
    body: ConsentRequest,
    actor: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],
    service: Annotated[MemoryControlService, Depends(_service)],
) -> MemoryControlView:
    return service.grant_consent(actor) if body.enabled else service.revoke_consent(actor)


@router.post("/memory/pause", response_model=MemoryControlView)
def pause(
    actor: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],
    service: Annotated[MemoryControlService, Depends(_service)],
) -> MemoryControlView:
    return service.pause(actor)


@router.post("/memory/resume", response_model=MemoryControlView)
def resume(
    actor: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],
    service: Annotated[MemoryControlService, Depends(_service)],
) -> MemoryControlView:
    return service.resume(actor)


@router.get("/memories", response_model=MemoryListResult)
def inspect_memories(
    actor: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],
    service: Annotated[MemoryControlService, Depends(_service)],
    person_id: UUID | None = None,
    relationship_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    cursor: str | None = None,
) -> MemoryListResult:
    return service.inspect_memories(
        actor, person_id=person_id, relationship_id=relationship_id, limit=limit, cursor=cursor
    )


@router.get("/memories/{memory_id}", response_model=MemoryRecordView)
def inspect_memory(
    memory_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],
    service: Annotated[MemoryControlService, Depends(_service)],
) -> MemoryRecordView:
    return service.inspect_memory(actor, memory_id)
