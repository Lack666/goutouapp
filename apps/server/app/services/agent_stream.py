"""Transport-neutral application events after persistence decisions."""

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from app.agent.contracts import MemoryWriteStatus
from app.agent.events import ProgressStatus


@dataclass(frozen=True)
class ServiceRunStarted:
    run_id: UUID


@dataclass(frozen=True)
class ServiceStatus:
    run_id: UUID
    status: ProgressStatus


@dataclass(frozen=True)
class ServiceFinalResponse:
    run_id: UUID
    assistant_message_id: UUID
    answer: str


@dataclass(frozen=True)
class ServiceMemoryStatus:
    run_id: UUID
    status: MemoryWriteStatus


@dataclass(frozen=True)
class ServiceCompleted:
    run_id: UUID
    assistant_message_id: UUID
    memory_status: MemoryWriteStatus


@dataclass(frozen=True)
class ServiceFailed:
    run_id: UUID
    code: Literal["agent_failure", "persistence_failure"]
    recovery_status: Literal["failed", "running_unknown"]


type ServiceStreamEvent = (
    ServiceRunStarted
    | ServiceStatus
    | ServiceFinalResponse
    | ServiceMemoryStatus
    | ServiceCompleted
    | ServiceFailed
)


@dataclass(frozen=True)
class AgentServiceStream:
    run_id: UUID
    events: AsyncIterator[ServiceStreamEvent]
    cancel_if_running: Callable[[], None]
