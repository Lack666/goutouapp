"""Signed resource transport; ownership, retries and persistence live in the service."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies import get_authenticated_actor
from app.schemas.resources import (
    AgentMessagePage,
    ConversationCreateRequest,
    ConversationPage,
    ConversationResponse,
    PageRequest,
    PersonCreateRequest,
    PersonPage,
    PersonResponse,
    RelationshipCreateRequest,
    RelationshipPage,
    RelationshipResponse,
)
from app.services.agent_service import AuthenticatedActor
from app.services.resources import ResourceService

router = APIRouter(tags=["resources"])


def _service(request: Request) -> ResourceService:
    return ResourceService(request.app.state.database.session)


Actor = Annotated[AuthenticatedActor, Depends(get_authenticated_actor)]
Service = Annotated[ResourceService, Depends(_service)]
Page = Annotated[PageRequest, Query()]


@router.post("/persons", status_code=201, response_model=PersonResponse)
def create_person(body: PersonCreateRequest, actor: Actor, service: Service) -> PersonResponse:
    return service.create_person(actor, body)


@router.get("/persons", response_model=PersonPage)
def list_persons(actor: Actor, service: Service, page: Page) -> PersonPage:
    return service.list_persons(actor, page)


@router.get("/persons/{person_id}", response_model=PersonResponse)
def get_person(person_id: UUID, actor: Actor, service: Service) -> PersonResponse:
    return service.get_person(actor, person_id)


@router.post("/relationships", status_code=201, response_model=RelationshipResponse)
def create_relationship(
    body: RelationshipCreateRequest, actor: Actor, service: Service
) -> RelationshipResponse:
    return service.create_relationship(actor, body)


@router.get("/relationships", response_model=RelationshipPage)
def list_relationships(actor: Actor, service: Service, page: Page) -> RelationshipPage:
    return service.list_relationships(actor, page)


@router.get("/relationships/{relationship_id}", response_model=RelationshipResponse)
def get_relationship(relationship_id: UUID, actor: Actor, service: Service) -> RelationshipResponse:
    return service.get_relationship(actor, relationship_id)


@router.post("/conversations", status_code=201, response_model=ConversationResponse)
def create_conversation(
    body: ConversationCreateRequest, actor: Actor, service: Service
) -> ConversationResponse:
    return service.create_conversation(actor, body)


@router.get("/conversations", response_model=ConversationPage)
def list_conversations(actor: Actor, service: Service, page: Page) -> ConversationPage:
    return service.list_conversations(actor, page)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation(conversation_id: UUID, actor: Actor, service: Service) -> ConversationResponse:
    return service.get_conversation(actor, conversation_id)


@router.get("/conversations/{conversation_id}/messages", response_model=AgentMessagePage)
def list_agent_messages(
    conversation_id: UUID, actor: Actor, service: Service, page: Page
) -> AgentMessagePage:
    return service.list_agent_messages(actor, conversation_id, page)
