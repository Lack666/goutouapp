"""Stable Agent-facing error categories, without transport or vendor exceptions."""

from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.agent.contracts import AgentRunStatus


class AgentErrorCode(StrEnum):
    INVALID_INPUT = "invalid_input"
    DEPENDENCY_FAILURE = "dependency_failure"
    STRUCTURED_OUTPUT_FAILURE = "structured_output_failure"
    RUNTIME_FAILURE = "runtime_failure"


class AgentError(Exception):
    code: AgentErrorCode = AgentErrorCode.RUNTIME_FAILURE

    def __init__(self, message: str = "Agent run failed") -> None:
        super().__init__(message)


class AgentInputError(AgentError):
    code = AgentErrorCode.INVALID_INPUT


class AgentDependencyError(AgentError):
    code = AgentErrorCode.DEPENDENCY_FAILURE


class AgentStructuredOutputError(AgentError):
    code = AgentErrorCode.STRUCTURED_OUTPUT_FAILURE


class AgentFailure(BaseModel):
    """Safe public failure value; raw dependency exceptions remain internal."""

    model_config = ConfigDict(strict=True, extra="forbid")

    schema_version: Literal["1"] = "1"
    run_id: UUID
    status: Literal[AgentRunStatus.FAILED] = AgentRunStatus.FAILED
    code: AgentErrorCode
    message: str
