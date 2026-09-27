"""Stable, transport-independent public events for one Agent run."""

from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, TypeAdapter, model_validator

from app.agent.contracts import AgentResult, ContractModel, MemoryDecision, MemoryReceipt
from app.agent.errors import AgentFailure


class ProgressStatus(StrEnum):
    PREPARING = "preparing"
    CHECKING_SAFETY = "checking_safety"
    UNDERSTANDING_REQUEST = "understanding_request"
    LOADING_CONTEXT = "loading_context"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    COMPOSING = "composing"
    PREPARING_SAFETY_RESPONSE = "preparing_safety_response"
    UPDATING_MEMORY = "updating_memory"


class RunStartedEvent(ContractModel):
    type: Literal["run_started"] = "run_started"
    run_id: UUID


class StatusEvent(ContractModel):
    type: Literal["status"] = "status"
    run_id: UUID
    status: ProgressStatus


class FinalResponseEvent(ContractModel):
    type: Literal["final_response"] = "final_response"
    run_id: UUID
    answer: str = Field(min_length=1)


class MemoryStatusEvent(ContractModel):
    type: Literal["memory_status"] = "memory_status"
    run_id: UUID
    decision: MemoryDecision
    receipt: MemoryReceipt


class CompletedEvent(ContractModel):
    type: Literal["completed"] = "completed"
    run_id: UUID
    result: AgentResult

    @model_validator(mode="after")
    def correlated_result(self) -> "CompletedEvent":
        if self.result.run_id != self.run_id:
            raise ValueError("completed result must match event run")
        return self


class FailedEvent(ContractModel):
    type: Literal["failed"] = "failed"
    run_id: UUID
    failure: AgentFailure

    @model_validator(mode="after")
    def correlated_failure(self) -> "FailedEvent":
        if self.failure.run_id != self.run_id:
            raise ValueError("failure must match event run")
        return self


type AgentEvent = Annotated[
    RunStartedEvent
    | StatusEvent
    | FinalResponseEvent
    | MemoryStatusEvent
    | CompletedEvent
    | FailedEvent,
    Field(discriminator="type"),
]
AGENT_EVENT_ADAPTER = TypeAdapter(AgentEvent)
