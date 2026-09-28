"""Transport-independent, owner-scoped Agent execution orchestration."""

from collections.abc import AsyncIterator, Callable
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
from app.agent.events import (
    CompletedEvent,
    FailedEvent,
    FinalResponseEvent,
    MemoryStatusEvent,
    RunStartedEvent,
    StatusEvent,
)
from app.db.repositories import records
from app.services.agent_stream import (
    AgentServiceStream,
    ServiceCompleted,
    ServiceFailed,
    ServiceFinalResponse,
    ServiceMemoryStatus,
    ServiceRunStarted,
    ServiceStatus,
    ServiceStreamEvent,
)

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
    CONVERSATION_BUSY = "conversation_busy"
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

    def stream(self, request: AgentInput) -> AsyncIterator: ...


class AgentService:
    def __init__(self, session_factory: Callable[[], Session], runtime: AgentRunner) -> None:
        self._session_factory = session_factory
        self._runtime = runtime

    def _prepare(
        self,
        *,
        actor: AuthenticatedActor,
        conversation_id: UUID,
        message: str,
        relationship_id: UUID | None,
        person_id: UUID | None,
        operation_key: str | None,
    ) -> AgentInput:
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
            # Transaction A is shared by synchronous and streaming execution.
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
                if not records.claim_conversation_run_slot(db, conversation_id):
                    raise AgentServiceError(AgentServiceErrorCode.CONVERSATION_BUSY)
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

        return AgentInput(
            run_id=run_id,
            user_id=actor.user_id,
            conversation_id=conversation_id,
            relationship_id=bound_relationship,
            message=message,
            recent_messages=history,
            memory_enabled=True,
        )

    def _mark_failed(self, request: AgentInput, failure_code: str) -> str:
        try:
            with self._session_factory() as db, db.begin():
                if not records.finish_agent_run(
                    db,
                    request.user_id,
                    request.conversation_id,
                    request.run_id,
                    AgentRunStatus.FAILED,
                    failure_code,
                ):
                    raise RuntimeError("run missing")
            return "failed"
        except Exception:
            return "running_unknown"

    def _commit_answer(self, request: AgentInput, answer: str) -> UUID:
        try:
            # Transaction B commits the assistant and terminal run atomically.
            with self._session_factory() as db, db.begin():
                assistant = records.create_message(
                    db, request.user_id, request.conversation_id, "assistant", answer
                )
                if assistant is None or not records.finish_agent_run(
                    db,
                    request.user_id,
                    request.conversation_id,
                    request.run_id,
                    AgentRunStatus.COMPLETED,
                ):
                    raise RuntimeError("run or conversation missing")
                return assistant.id
        except Exception:
            recovery = self._mark_failed(request, "persistence_failure")
            raise AgentServiceError(
                AgentServiceErrorCode.PERSISTENCE_FAILURE,
                run_id=request.run_id,
                recovery_status=recovery,
            ) from None

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
        request = self._prepare(
            actor=actor,
            conversation_id=conversation_id,
            message=message,
            relationship_id=relationship_id,
            person_id=person_id,
            operation_key=operation_key,
        )
        try:
            result = await self._runtime.run(request)
        except Exception:
            result = None
        if (
            result is None
            or not isinstance(result, (AgentResult, AgentFailure))
            or result.run_id != request.run_id
        ):
            failure_code = "runtime_failure"
        elif isinstance(result, AgentFailure):
            failure_code = result.code.value
        else:
            failure_code = None

        if failure_code is not None:
            recovery = self._mark_failed(request, failure_code)
            code = (
                AgentServiceErrorCode.RUNTIME_FAILURE
                if recovery == "failed"
                else AgentServiceErrorCode.PERSISTENCE_FAILURE
            )
            raise AgentServiceError(code, run_id=request.run_id, recovery_status=recovery)

        assistant_id = self._commit_answer(request, result.final_answer)
        return AgentServiceResult(
            run_id=request.run_id,
            conversation_id=conversation_id,
            assistant_message=AssistantMessageResult(
                assistant_id, "assistant", result.final_answer
            ),
            status=AgentRunStatus.COMPLETED,
            memory_status=result.memory_receipt.status,
            warnings=tuple(result.warnings),
        )

    async def stream(
        self,
        *,
        actor: AuthenticatedActor,
        conversation_id: UUID,
        message: str,
        relationship_id: UUID | None = None,
        person_id: UUID | None = None,
        operation_key: str | None = None,
    ) -> AgentServiceStream:
        # This await returns only after authz and Transaction A have completed.
        # The HTTP adapter can still return a normal 4xx before streaming starts.
        request = self._prepare(
            actor=actor,
            conversation_id=conversation_id,
            message=message,
            relationship_id=relationship_id,
            person_id=person_id,
            operation_key=operation_key,
        )
        return AgentServiceStream(
            run_id=request.run_id,
            events=self._stream_events(request),
            cancel_if_running=lambda: self._mark_failed(request, "client_disconnected"),
        )

    async def _stream_events(self, request: AgentInput) -> AsyncIterator[ServiceStreamEvent]:
        run_id = request.run_id
        runtime_events = None
        assistant_id: UUID | None = None
        final_answer: str | None = None
        memory_status = MemoryWriteStatus.NONE
        memory_sent = False
        terminal = False
        yield ServiceRunStarted(run_id)
        try:
            runtime_events = self._runtime.stream(request)
            async for event in runtime_events:
                if event.run_id != run_id:
                    raise RuntimeError("runtime event run ID mismatch")
                if isinstance(event, RunStartedEvent):
                    continue
                if isinstance(event, StatusEvent):
                    yield ServiceStatus(run_id, event.status)
                elif isinstance(event, FinalResponseEvent):
                    if assistant_id is not None:
                        raise RuntimeError("duplicate final response")
                    assistant_id = self._commit_answer(request, event.answer)
                    final_answer = event.answer
                    yield ServiceFinalResponse(run_id, assistant_id, event.answer)
                elif isinstance(event, MemoryStatusEvent):
                    if assistant_id is None:
                        raise RuntimeError("memory status before final response")
                    memory_status = event.receipt.status
                    memory_sent = True
                    yield ServiceMemoryStatus(run_id, memory_status)
                elif isinstance(event, CompletedEvent):
                    if assistant_id is None or event.result.final_answer != final_answer:
                        raise RuntimeError("completed event without matching final response")
                    memory_status = event.result.memory_receipt.status
                    if memory_status != MemoryWriteStatus.NONE and not memory_sent:
                        yield ServiceMemoryStatus(run_id, memory_status)
                    terminal = True
                    yield ServiceCompleted(run_id, assistant_id, memory_status)
                    return
                elif isinstance(event, FailedEvent):
                    if assistant_id is not None:
                        if not memory_sent:
                            yield ServiceMemoryStatus(run_id, MemoryWriteStatus.FAILED)
                        terminal = True
                        yield ServiceCompleted(
                            run_id,
                            assistant_id,
                            memory_status if memory_sent else MemoryWriteStatus.FAILED,
                        )
                    else:
                        recovery = self._mark_failed(request, event.failure.code.value)
                        terminal = True
                        code = "agent_failure" if recovery == "failed" else "persistence_failure"
                        yield ServiceFailed(run_id, code, recovery)
                    return
                else:
                    raise RuntimeError("unexpected runtime event")
            raise RuntimeError("runtime stream ended without a terminal event")
        except AgentServiceError as exc:
            terminal = True
            yield ServiceFailed(
                run_id,
                "persistence_failure",
                exc.recovery_status or "running_unknown",
            )
        except Exception:
            if assistant_id is not None:
                if not memory_sent:
                    yield ServiceMemoryStatus(run_id, MemoryWriteStatus.FAILED)
                terminal = True
                yield ServiceCompleted(
                    run_id,
                    assistant_id,
                    memory_status if memory_sent else MemoryWriteStatus.FAILED,
                )
            else:
                recovery = self._mark_failed(request, "runtime_failure")
                terminal = True
                code = "agent_failure" if recovery == "failed" else "persistence_failure"
                yield ServiceFailed(run_id, code, recovery)
        finally:
            try:
                if runtime_events is not None:
                    await runtime_events.aclose()
            finally:
                if not terminal and assistant_id is None:
                    self._mark_failed(request, "client_disconnected")
