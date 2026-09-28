"""HTTP-specific adapters for independent backend dependencies."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.agent.dependencies import RuntimeDependencies
from app.agent.memory import MemoryService
from app.agent.runtime import AgentRuntime
from app.auth.jwt_verifier import CredentialVerificationError, JWTBearerVerifier
from app.db.repositories.memory import SQLAlchemyMemoryStore
from app.llm.factory import create_llm_provider
from app.services.agent_service import (
    AgentService,
    AuthenticatedActor,
    actor_from_verified_identity,
)

bearer_scheme = HTTPBearer(auto_error=False, scheme_name="BearerCredential")


def get_authenticated_actor(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)],
) -> AuthenticatedActor:
    if len(request.headers.getlist("authorization")) != 1 or credentials is None:
        raise CredentialVerificationError
    identity = JWTBearerVerifier(request.app.state.settings).verify(credentials.credentials)
    return actor_from_verified_identity(identity.user_id)


def get_agent_service(request: Request) -> AgentService:
    """Compile once per app, lazily, without holding a database connection."""
    state = request.app.state
    with state.agent_service_lock:
        if state.agent_service is None:
            database = state.database
            provider = create_llm_provider(state.settings)
            runtime = AgentRuntime(
                dependencies=RuntimeDependencies(
                    llm_provider=provider,
                    memory_service=MemoryService(SQLAlchemyMemoryStore(database.session)),
                )
            )
            state.agent_service = AgentService(database.session, runtime)
        return state.agent_service


def get_db(request: Request) -> Iterator[Session]:
    """Commit successful request work; rollback on any exception; always close."""
    with request.app.state.database.session() as session:
        try:
            yield session
            session.commit()
        except BaseException:
            session.rollback()
            raise
