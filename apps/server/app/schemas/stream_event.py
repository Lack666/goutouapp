"""Versioned, deliberately narrow SSE protocol for persisted Agent runs."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from app.agent.contracts import MemoryWriteStatus
from app.agent.events import ProgressStatus
from app.services.agent_stream import (
    ServiceCompleted,
    ServiceFailed,
    ServiceFinalResponse,
    ServiceMemoryStatus,
    ServiceRunStarted,
    ServiceStatus,
    ServiceStreamEvent,
)


class StreamModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class EmptyData(StreamModel):
    pass


class StatusData(StreamModel):
    status: ProgressStatus


class FinalResponseData(StreamModel):
    assistant_message_id: UUID
    answer: str


class MemoryStatusData(StreamModel):
    status: MemoryWriteStatus


class PendingConfirmationData(StreamModel):
    status: Literal["pending_confirmation"] = "pending_confirmation"


class CompletedData(StreamModel):
    status: Literal["completed"] = "completed"
    assistant_message_id: UUID
    memory_status: MemoryWriteStatus


class FailedData(StreamModel):
    code: Literal["agent_failure", "persistence_failure"]
    recovery_status: Literal["failed", "running_unknown"]


class RunStartedEnvelope(StreamModel):
    schema_version: Literal["1"] = "1"
    event: Literal["run_started"] = "run_started"
    run_id: UUID
    data: EmptyData = Field(default_factory=EmptyData)


class StatusEnvelope(StreamModel):
    schema_version: Literal["1"] = "1"
    event: Literal["status"] = "status"
    run_id: UUID
    data: StatusData


class FinalResponseEnvelope(StreamModel):
    schema_version: Literal["1"] = "1"
    event: Literal["final_response"] = "final_response"
    run_id: UUID
    data: FinalResponseData


class MemoryStatusEnvelope(StreamModel):
    schema_version: Literal["1"] = "1"
    event: Literal["memory_status"] = "memory_status"
    run_id: UUID
    data: MemoryStatusData


class PendingConfirmationEnvelope(StreamModel):
    schema_version: Literal["1"] = "1"
    event: Literal["pending_confirmation"] = "pending_confirmation"
    run_id: UUID
    data: PendingConfirmationData = Field(default_factory=PendingConfirmationData)


class CompletedEnvelope(StreamModel):
    schema_version: Literal["1"] = "1"
    event: Literal["completed"] = "completed"
    run_id: UUID
    data: CompletedData


class FailedEnvelope(StreamModel):
    schema_version: Literal["1"] = "1"
    event: Literal["failed"] = "failed"
    run_id: UUID
    data: FailedData


type NetworkStreamEvent = Annotated[
    RunStartedEnvelope
    | StatusEnvelope
    | FinalResponseEnvelope
    | MemoryStatusEnvelope
    | PendingConfirmationEnvelope
    | CompletedEnvelope
    | FailedEnvelope,
    Field(discriminator="event"),
]
NETWORK_EVENT_ADAPTER = TypeAdapter(NetworkStreamEvent)


def to_network_event(event: ServiceStreamEvent) -> NetworkStreamEvent:
    if isinstance(event, ServiceRunStarted):
        return RunStartedEnvelope(run_id=event.run_id)
    if isinstance(event, ServiceStatus):
        return StatusEnvelope(run_id=event.run_id, data=StatusData(status=event.status))
    if isinstance(event, ServiceFinalResponse):
        return FinalResponseEnvelope(
            run_id=event.run_id,
            data=FinalResponseData(
                assistant_message_id=event.assistant_message_id, answer=event.answer
            ),
        )
    if isinstance(event, ServiceMemoryStatus):
        if event.status == MemoryWriteStatus.PENDING_CONFIRMATION:
            return PendingConfirmationEnvelope(run_id=event.run_id)
        return MemoryStatusEnvelope(run_id=event.run_id, data=MemoryStatusData(status=event.status))
    if isinstance(event, ServiceCompleted):
        return CompletedEnvelope(
            run_id=event.run_id,
            data=CompletedData(
                assistant_message_id=event.assistant_message_id,
                memory_status=event.memory_status,
            ),
        )
    if isinstance(event, ServiceFailed):
        return FailedEnvelope(
            run_id=event.run_id,
            data=FailedData(code=event.code, recovery_status=event.recovery_status),
        )
    raise TypeError("Unsupported service stream event")


def encode_sse(event: NetworkStreamEvent) -> bytes:
    validated = NETWORK_EVENT_ADAPTER.validate_python(event)
    # Pydantic escapes data newlines inside JSON. One event maps to one frame.
    lines = (f"event: {validated.event}", f"data: {validated.model_dump_json()}", "", "")
    return "\n".join(lines).encode("utf-8")
