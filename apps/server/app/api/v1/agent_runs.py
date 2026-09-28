"""Thin REST transport for the owner-scoped AgentService."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import get_agent_service, get_authenticated_actor
from app.schemas.agent_run import AgentRunResponse, CreateAgentRunRequest
from app.services.agent_service import AgentService, AuthenticatedActor

router = APIRouter()


@router.post(
    "/conversations/{conversation_id}/agent-runs",
    response_model=AgentRunResponse,
    tags=["agent"],
)
async def create_agent_run(
    conversation_id: UUID,
    body: CreateAgentRunRequest,
    actor: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],
    service: Annotated[AgentService, Depends(get_agent_service)],
) -> AgentRunResponse:
    result = await service.execute(
        actor=actor,
        conversation_id=conversation_id,
        message=body.message,
        relationship_id=body.expected_relationship_id,
        operation_key=body.operation_key,
    )
    return AgentRunResponse.from_service(result)
