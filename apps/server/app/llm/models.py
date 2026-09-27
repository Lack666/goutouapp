"""Small typed values returned by every LLM provider."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LLMMessage(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    role: Literal["system", "developer", "user", "assistant", "tool"]
    content: str


class Usage(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class ChatResult(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    content: str
    model: str
    finish_reason: str | None = None
    usage: Usage | None = None


class StreamChunk(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    content: str
    model: str | None = None
    finish_reason: str | None = None
    usage: Usage | None = None
