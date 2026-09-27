"""The only interface future application/Agent code should depend on."""

from collections.abc import AsyncIterator, Sequence
from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.llm.models import ChatResult, LLMMessage, StreamChunk

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class LLMProvider(Protocol):
    async def chat(
        self,
        messages: Sequence[LLMMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> ChatResult: ...

    def stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[StreamChunk]: ...

    async def structured_output(
        self,
        messages: Sequence[LLMMessage],
        schema: type[SchemaT],
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> SchemaT: ...
