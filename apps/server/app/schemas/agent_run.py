"""Public REST request and response for a completed Agent execution."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.agent.contracts import AgentRunStatus, MemoryWriteStatus
from app.services.agent_service import AgentServiceResult


class CreateAgentRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=20000)
    expected_relationship_id: UUID | None = None
    operation_key: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("message")
    @classmethod
    def nonblank_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be blank")
        if "\x00" in value:
            raise ValueError("message contains unsupported characters")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            raise ValueError("message is not valid Unicode") from None
        return value


class AssistantMessageResponse(BaseModel):
    id: UUID
    role: Literal["assistant"] = "assistant"
    content: str


class AgentRunResponse(BaseModel):
    run_id: UUID
    conversation_id: UUID
    status: AgentRunStatus
    assistant_message: AssistantMessageResponse
    memory_status: MemoryWriteStatus
    warnings: list[str]

    @classmethod
    def from_service(cls, result: AgentServiceResult) -> "AgentRunResponse":
        return cls(
            run_id=result.run_id,
            conversation_id=result.conversation_id,
            status=result.status,
            assistant_message=AssistantMessageResponse(
                id=result.assistant_message.id,
                content=result.assistant_message.content,
            ),
            memory_status=result.memory_status,
            warnings=list(result.warnings),
        )
