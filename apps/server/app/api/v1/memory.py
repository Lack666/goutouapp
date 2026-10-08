"""Thin signed-JWT transport for memory controls and owner-scoped inspection."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict

from app.api.dependencies import get_authenticated_actor
from app.db.repositories.memory import SQLAlchemyMemoryStore
from app.retention import RetentionPolicy
from app.services.agent_service import AuthenticatedActor
from app.services.memory_control import (
    MemoryControlService,
    MemoryControlView,
    MemoryListResult,
    MemoryRecordView,
)
from app.services.memory_mutation import (
    MemoryConfirmationChallenge,
    MemoryMutationReceipt,
    MemoryMutationService,
    UndoPreview,
)

router = APIRouter(tags=["memory"])


class ConsentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


class UndoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_operation_id: UUID
    operation_key: str


class DeleteOnePreparation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    memory_id: UUID
    person_id: UUID | None = None
    relationship_id: UUID | None = None


class DeletePersonPreparation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    person_id: UUID


class DeleteAllPreparation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revoke_consent_after_delete: bool


class ExecuteDeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_key: str


def _service(request: Request) -> MemoryControlService:
    return MemoryControlService(
        SQLAlchemyMemoryStore(
            request.app.state.database.session,
            policy=RetentionPolicy.from_settings(request.app.state.settings),
        )
    )


def _mutation_service(request: Request) -> MemoryMutationService:
    return MemoryMutationService(request.app.state.database.session)


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


@router.get("/memory/undo/preview", response_model=UndoPreview)
def preview_undo(
    actor: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],
    service: Annotated[MemoryMutationService, Depends(_mutation_service)],
) -> UndoPreview:
    return service.preview_undo(actor)


@router.post("/memory/undo", response_model=MemoryMutationReceipt)
def undo_memory(
    body: UndoRequest,
    actor: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],
    service: Annotated[MemoryMutationService, Depends(_mutation_service)],
) -> MemoryMutationReceipt:
    return service.undo(
        actor,
        expected_operation_id=body.expected_operation_id,
        operation_key=body.operation_key,
    )


@router.post("/memory/deletions/one/prepare", response_model=MemoryConfirmationChallenge)
def prepare_delete_one(
    body: DeleteOnePreparation,
    actor: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],
    service: Annotated[MemoryMutationService, Depends(_mutation_service)],
) -> MemoryConfirmationChallenge:
    return service.prepare_delete_one(
        actor,
        memory_id=body.memory_id,
        person_id=body.person_id,
        relationship_id=body.relationship_id,
    )


@router.post("/memory/deletions/person/prepare", response_model=MemoryConfirmationChallenge)
def prepare_delete_person(
    body: DeletePersonPreparation,
    actor: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],
    service: Annotated[MemoryMutationService, Depends(_mutation_service)],
) -> MemoryConfirmationChallenge:
    return service.prepare_delete_person(actor, person_id=body.person_id)


@router.post("/memory/deletions/all/prepare", response_model=MemoryConfirmationChallenge)
def prepare_delete_all(
    body: DeleteAllPreparation,
    actor: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],
    service: Annotated[MemoryMutationService, Depends(_mutation_service)],
) -> MemoryConfirmationChallenge:
    return service.prepare_delete_all(
        actor, revoke_consent_after_delete=body.revoke_consent_after_delete
    )


@router.post("/memory/deletions/{confirmation_id}/execute", response_model=MemoryMutationReceipt)
def execute_delete(
    confirmation_id: UUID,
    body: ExecuteDeleteRequest,
    actor: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],
    service: Annotated[MemoryMutationService, Depends(_mutation_service)],
) -> MemoryMutationReceipt:
    return service.execute_delete(
        actor, confirmation_id=confirmation_id, operation_key=body.operation_key
    )


@router.get("/memory/mutations/{mutation_id}", response_model=MemoryMutationReceipt)
def inspect_mutation(
    mutation_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],
    service: Annotated[MemoryMutationService, Depends(_mutation_service)],
) -> MemoryMutationReceipt:
    return service.inspect_receipt(actor, mutation_id)
