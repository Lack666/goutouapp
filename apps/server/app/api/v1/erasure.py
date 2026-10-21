"""Backend-only guarded erasure; no client-side bypass or owner override."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_authenticated_actor
from app.schemas.erasure import ErasureChallenge, ErasureExecute, ErasureResult, ErasureTarget
from app.services.agent_service import AuthenticatedActor
from app.services.agent_writer import AgentWriterRegistry
from app.services.erasure import ErasureService

router = APIRouter(prefix="/erasures", tags=["erasures"])
Actor = Annotated[AuthenticatedActor, Depends(get_authenticated_actor)]


def _service(request: Request):
    return ErasureService(
        request.app.state.database.session,
        writers=AgentWriterRegistry(request.app.state.settings.chat_import_artifact_root),
    )


Service = Annotated[ErasureService, Depends(_service)]


@router.post("/prepare", response_model=ErasureChallenge)
def prepare_erasure(body: ErasureTarget, actor: Actor, service: Service):
    return service.prepare(actor, body)


@router.post("/execute", response_model=ErasureResult)
def execute_erasure(body: ErasureExecute, actor: Actor, service: Service):
    return service.execute(actor, body)


@router.get("/receipts/{receipt_id}", response_model=ErasureResult)
def get_erasure_receipt(receipt_id: UUID, actor: Actor, service: Service):
    return service.receipt(actor, receipt_id)
