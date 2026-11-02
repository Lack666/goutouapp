"""Signed preparation/confirmation/evidence only. No Agent or execute endpoint."""

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
from app.services.agent_service import AuthenticatedActor
from app.services.imported_analysis import ImportedAnalysisService

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
