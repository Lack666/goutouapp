"""Signed self-service Person/Relationship erasure; Owner remains operator-only."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_authenticated_actor
from app.schemas.lifecycle import (
    LifecycleChallenge,
    LifecycleResult,
    MobileLifecycleExecute,
    MobileLifecycleTarget,
)
from app.services.agent_service import AuthenticatedActor
from app.services.agent_writer import AgentWriterRegistry
from app.services.lifecycle_erasure import LifecycleErasure

router = APIRouter(prefix="/lifecycle-erasures", tags=["lifecycle-erasures"])
Actor = Annotated[AuthenticatedActor, Depends(get_authenticated_actor)]


def service(request: Request):
    state = request.app.state
    return LifecycleErasure(
        state.database.session,
        state.import_artifact_store,
        AgentWriterRegistry(state.settings.chat_import_artifact_root),
    )


Service = Annotated[LifecycleErasure, Depends(service)]


@router.post("/prepare", response_model=LifecycleChallenge)
def prepare_lifecycle_erasure(body: MobileLifecycleTarget, actor: Actor, service: Service):
    return service.prepare(actor, body)


@router.post("/execute", response_model=LifecycleResult)
def execute_lifecycle_erasure(body: MobileLifecycleExecute, actor: Actor, service: Service):
    return service.execute(actor, body)


@router.get("/receipts/{receipt_id}", response_model=LifecycleResult)
def get_lifecycle_erasure_receipt(receipt_id: UUID, actor: Actor, service: Service):
    return service.receipt(actor, receipt_id)
