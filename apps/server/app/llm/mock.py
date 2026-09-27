"""Deterministic, keyless provider with per-operation response queues."""

import json
from collections import deque
from collections.abc import AsyncIterator, Mapping, Sequence
from typing import Literal

from app.llm.errors import LLMConfigurationError, LLMError, LLMStructuredOutputError
from app.llm.models import ChatResult, LLMMessage, StreamChunk, Usage
from app.llm.provider import SchemaT
from app.llm.validation import validate_structured_output

Operation = Literal["chat", "stream", "structured_output"]


class MockLLMProvider:
    def __init__(self, *, model: str = "mock") -> None:
        self.model = model
        self._chats: deque[ChatResult | LLMError] = deque()
        self._streams: deque[tuple[StreamChunk, ...] | LLMError] = deque()
        self._structured: deque[str | Mapping[str, object] | LLMError] = deque()

    def queue_chat(
        self,
        content: str,
        *,
        finish_reason: str | None = "stop",
        usage: Usage | None = None,
    ) -> None:
        self._chats.append(
            ChatResult(content=content, model=self.model, finish_reason=finish_reason, usage=usage)
        )

    def queue_stream(self, *chunks: StreamChunk) -> None:
        self._streams.append(chunks)

    def queue_structured(self, value: str | Mapping[str, object]) -> None:
        self._structured.append(value)

    def queue_error(self, operation: Operation, error: LLMError) -> None:
        if operation == "chat":
            self._chats.append(error)
        elif operation == "stream":
            self._streams.append(error)
        elif operation == "structured_output":
            self._structured.append(error)
        else:
            raise LLMConfigurationError() from None

    async def chat(
        self,
        messages: Sequence[LLMMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> ChatResult:
        del messages, temperature
        if not self._chats:
            raise LLMConfigurationError() from None
        result = self._chats.popleft()
        if isinstance(result, LLMError):
            raise result
        if model is not None:
            return result.model_copy(update={"model": model})
        return result

    async def stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[StreamChunk]:
        del messages, temperature
        if not self._streams:
            raise LLMConfigurationError() from None
        result = self._streams.popleft()
        if isinstance(result, LLMError):
            raise result
        for chunk in result:
            yield chunk.model_copy(update={"model": model}) if model is not None else chunk

    async def structured_output(
        self,
        messages: Sequence[LLMMessage],
        schema: type[SchemaT],
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> SchemaT:
        del messages, model, temperature
        if not self._structured:
            raise LLMConfigurationError() from None
        result = self._structured.popleft()
        if isinstance(result, LLMError):
            raise result
        try:
            content = result if isinstance(result, str) else json.dumps(result)
        except (TypeError, ValueError):
            raise LLMStructuredOutputError() from None
        return validate_structured_output(content, schema)
