"""Signed source authority and separately confirmed opt-in Mock execution."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_authenticated_actor
from app.schemas.imported_analysis import (
    AnalysisConfirm,
    AnalysisGrantView,
    AnalysisPreparation,
    AnalysisPrepare,
    EvidenceRequest,
    EvidenceView,
)
from app.schemas.imported_execution import (
    ExecutionConfirm,
    ExecutionPreparation,
    ExecutionPrepare,
    ExecutionView,
)
from app.services.agent_service import AuthenticatedActor
from app.services.imported_analysis import ImportedAnalysisService
from app.services.imported_execution import ImportedExecutionService

router = APIRouter(prefix="/imported-analysis", tags=["imported-analysis"])
Actor = Annotated[AuthenticatedActor, Depends(get_authenticated_actor)]


def service(request: Request):
    return ImportedAnalysisService(request.app.state.database.session)


Service = Annotated[ImportedAnalysisService, Depends(service)]


@router.post("/prepare", response_model=AnalysisPreparation)
def prepare(body: AnalysisPrepare, actor: Actor, service: Service):
    return service.prepare(actor, body)


@router.post("/confirm", response_model=AnalysisGrantView)
def confirm(body: AnalysisConfirm, actor: Actor, service: Service):
    return service.confirm(actor, body)


@router.get("/grants/{grant_id}", response_model=AnalysisGrantView)
def inspect(grant_id: UUID, actor: Actor, service: Service):
    return service.inspect(actor, grant_id)


@router.post("/grants/{grant_id}/revoke", response_model=AnalysisGrantView)
def revoke(grant_id: UUID, actor: Actor, service: Service):
    return service.revoke(actor, grant_id)


@router.post("/grants/{grant_id}/evidence/{alias}", response_model=EvidenceView)
def evidence(
    grant_id: UUID,
    alias: str,
    actor: Actor,
    service: Service,
    body: EvidenceRequest,
):
    return service.evidence(actor, grant_id, alias, body.start, body.end, body.quote)


def execution_service(request: Request):
    return ImportedExecutionService(
        request.app.state.database.session,
        enabled=request.app.state.settings.ica_mock_execution_enabled,
        provider_factory=getattr(request.app.state, "ica_mock_provider_factory", None),
    )


ExecutionService = Annotated[ImportedExecutionService, Depends(execution_service)]


@router.post("/execution-prepare", response_model=ExecutionPreparation)
def prepare_execution(body: ExecutionPrepare, actor: Actor, service: ExecutionService):
    return service.prepare_execution(actor, body)


@router.post("/execution-confirm", response_model=ExecutionView)
def confirm_execution(body: ExecutionConfirm, actor: Actor, service: ExecutionService):
    return service.confirm_execution(actor, body)


@router.post("/runs/{run_id}/execute", response_model=ExecutionView)
async def execute(run_id: UUID, actor: Actor, service: ExecutionService):
    return await service.execute(actor, run_id)


@router.get("/runs/{run_id}", response_model=ExecutionView)
def inspect_execution(run_id: UUID, actor: Actor, service: ExecutionService):
    return service.inspect_execution(actor, run_id)
