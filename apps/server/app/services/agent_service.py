"""Transport-independent, owner-scoped Agent execution orchestration."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.agent.contracts import (
    AgentInput,
    AgentResult,
    AgentRunStatus,
    ConversationMessage,
    MemoryWriteStatus,
)
from app.agent.errors import AgentFailure
from app.db.repositories import records

HISTORY_LIMIT = 20
_ACTOR_ISSUER = object()


@dataclass(frozen=True, init=False)
class AuthenticatedActor:
    """Identity asserted by a trusted authentication adapter, never a request body."""

    user_id: UUID

    def __init__(self, user_id: UUID, *, _issuer: object) -> None:
        if _issuer is not _ACTOR_ISSUER or not isinstance(user_id, UUID):
            raise TypeError("AuthenticatedActor requires a verified identity")
        object.__setattr__(self, "user_id", user_id)


def actor_from_verified_identity(user_id: UUID) -> AuthenticatedActor:
    """Only a trusted auth adapter may call this after verifying its credential."""
    return AuthenticatedActor(user_id, _issuer=_ACTOR_ISSUER)


class AgentServiceErrorCode(StrEnum):
    INVALID_ACTOR = "invalid_actor"
    USER_NOT_FOUND = "user_not_found"
    INVALID_INPUT = "invalid_input"
    CONVERSATION_NOT_FOUND = "conversation_not_found"
    CONVERSATION_FORBIDDEN = "conversation_forbidden"
    INVALID_RELATIONSHIP_SCOPE = "invalid_relationship_scope"
    RUNTIME_FAILURE = "runtime_failure"
    PERSISTENCE_FAILURE = "persistence_failure"


class AgentServiceError(Exception):
    def __init__(
        self,
        code: AgentServiceErrorCode,
        *,
        run_id: UUID | None = None,
        recovery_status: str | None = None,
    ) -> None:
        self.code = code
        self.run_id = run_id
        self.recovery_status = recovery_status
        super().__init__(code.value)


@dataclass(frozen=True)
class AssistantMessageResult:
    id: UUID
    role: str
    content: str


@dataclass(frozen=True)
class AgentServiceResult:
    run_id: UUID
    conversation_id: UUID
    assistant_message: AssistantMessageResult
    status: AgentRunStatus
    memory_status: MemoryWriteStatus
    warnings: tuple[str, ...]


class AgentRunner(Protocol):
    async def run(self, request: AgentInput) -> AgentResult | AgentFailure: ...


class AgentService:
    def __init__(self, session_factory: Callable[[], Session], runtime: AgentRunner) -> None:
        self._session_factory = session_factory
        self._runtime = runtime

    async def execute(
        self,
        *,
        actor: AuthenticatedActor,
        conversation_id: UUID,
        message: str,
        relationship_id: UUID | None = None,
        person_id: UUID | None = None,
        operation_key: str | None = None,
    ) -> AgentServiceResult:
        if not isinstance(actor, AuthenticatedActor):
            raise AgentServiceError(AgentServiceErrorCode.INVALID_ACTOR)
        if (
            not isinstance(conversation_id, UUID)
            or not isinstance(message, str)
            or not message.strip()
        ):
            raise AgentServiceError(AgentServiceErrorCode.INVALID_INPUT)
        if operation_key is not None and (
            not isinstance(operation_key, str) or not 1 <= len(operation_key) <= 128
        ):
            raise AgentServiceError(AgentServiceErrorCode.INVALID_INPUT)
        if relationship_id is not None and not isinstance(relationship_id, UUID):
            raise AgentServiceError(AgentServiceErrorCode.INVALID_INPUT)
        if person_id is not None and not isinstance(person_id, UUID):
            raise AgentServiceError(AgentServiceErrorCode.INVALID_INPUT)

        run_id = uuid4()
        try:
            # Transaction A: all reads and writes finish before the runtime starts.
            with self._session_factory() as db, db.begin():
                if records.get_user(db, actor.user_id) is None:
                    raise AgentServiceError(AgentServiceErrorCode.USER_NOT_FOUND)
                conversation = records.get_conversation(db, actor.user_id, conversation_id)
                if conversation is None:
                    code = (
                        AgentServiceErrorCode.CONVERSATION_FORBIDDEN
                        if records.get_conversation_by_id(db, conversation_id) is not None
                        else AgentServiceErrorCode.CONVERSATION_NOT_FOUND
                    )
                    raise AgentServiceError(code)
                bound_relationship = conversation.relationship_id
                if relationship_id is not None and relationship_id != bound_relationship:
                    raise AgentServiceError(AgentServiceErrorCode.INVALID_RELATIONSHIP_SCOPE)
                if person_id is not None:
                    relationship = (
                        records.get_relationship(db, actor.user_id, bound_relationship)
                        if bound_relationship is not None
                        else None
                    )
                    if relationship is None or relationship.person_id != person_id:
                        raise AgentServiceError(AgentServiceErrorCode.INVALID_RELATIONSHIP_SCOPE)
                history = [
                    ConversationMessage(role=row.role, content=row.content, speaker=row.speaker)
                    for row in records.recent_messages(
                        db, actor.user_id, conversation_id, HISTORY_LIMIT
                    )
                ]
                user_message = records.create_message(
                    db, actor.user_id, conversation_id, "user", message
                )
                if user_message is None:
                    raise AgentServiceError(AgentServiceErrorCode.CONVERSATION_NOT_FOUND)
                records.start_agent_run(db, actor.user_id, conversation_id, run_id)
        except AgentServiceError:
            raise
        except Exception:
            raise AgentServiceError(AgentServiceErrorCode.PERSISTENCE_FAILURE) from None

        request = AgentInput(
            run_id=run_id,
            user_id=actor.user_id,
            conversation_id=conversation_id,
            relationship_id=bound_relationship,
            message=message,
            recent_messages=history,
            memory_enabled=True,
        )
        try:
            result = await self._runtime.run(request)
        except Exception:
            result = None
        if (
            result is None
            or not isinstance(result, (AgentResult, AgentFailure))
            or result.run_id != run_id
        ):
            failure_code = "runtime_failure"
        elif isinstance(result, AgentFailure):
            failure_code = result.code.value
        else:
            failure_code = None

        if failure_code is not None:
            try:
                with self._session_factory() as db, db.begin():
                    if not records.finish_agent_run(
                        db,
                        actor.user_id,
                        conversation_id,
                        run_id,
                        AgentRunStatus.FAILED,
                        failure_code,
                    ):
                        raise RuntimeError("run missing")
            except Exception:
                raise AgentServiceError(
                    AgentServiceErrorCode.PERSISTENCE_FAILURE,
                    run_id=run_id,
                    recovery_status="running_unknown",
                ) from None
            raise AgentServiceError(
                AgentServiceErrorCode.RUNTIME_FAILURE,
                run_id=run_id,
                recovery_status="failed",
            )

        try:
            # Transaction B: assistant text and completion are atomic.
            with self._session_factory() as db, db.begin():
                assistant = records.create_message(
                    db, actor.user_id, conversation_id, "assistant", result.final_answer
                )
                if assistant is None or not records.finish_agent_run(
                    db, actor.user_id, conversation_id, run_id, AgentRunStatus.COMPLETED
                ):
                    raise RuntimeError("run or conversation missing")
                assistant_id = assistant.id
        except Exception:
            # B rolled back. A fresh short transaction makes the failed run visible.
            try:
                with self._session_factory() as db, db.begin():
                    if not records.finish_agent_run(
                        db,
                        actor.user_id,
                        conversation_id,
                        run_id,
                        AgentRunStatus.FAILED,
                        "persistence_failure",
                    ):
                        raise RuntimeError("run missing")
                recovery_status = "failed"
            except Exception:
                recovery_status = "running_unknown"
            raise AgentServiceError(
                AgentServiceErrorCode.PERSISTENCE_FAILURE,
                run_id=run_id,
                recovery_status=recovery_status,
            ) from None

        return AgentServiceResult(
            run_id=run_id,
            conversation_id=conversation_id,
            assistant_message=AssistantMessageResult(
                assistant_id, "assistant", result.final_answer
            ),
            status=AgentRunStatus.COMPLETED,
            memory_status=result.memory_receipt.status,
            warnings=tuple(result.warnings),
        )
