"""Text-only OpenAI-compatible Chat Completions transport and normalization."""

import json
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from time import perf_counter

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError

from app.llm.errors import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMInvalidResponseError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.llm.models import ChatResult, LLMMessage, StreamChunk, Usage
from app.llm.provider import SchemaT
from app.llm.validation import validate_structured_output
from app.observability import capture_response, provider_scope


class _WireModel(BaseModel):
    # Provider-specific fields, including hidden reasoning content, are discarded.
    model_config = ConfigDict(strict=True, extra="ignore")


class _WireUsage(_WireModel):
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    prompt_cache_hit_tokens: int | None = Field(default=None, ge=0)
    prompt_cache_miss_tokens: int | None = Field(default=None, ge=0)


class _WireMessage(_WireModel):
    content: str


class _WireChoice(_WireModel):
    message: _WireMessage
    finish_reason: str | None = None


class _WireChat(_WireModel):
    model: str = Field(min_length=1, max_length=128)
    choices: list[_WireChoice]
    usage: _WireUsage | None = None


class _WireDelta(_WireModel):
    content: str | None = None


class _WireStreamChoice(_WireModel):
    delta: _WireDelta
    finish_reason: str | None = None


class _WireStream(_WireModel):
    model: str | None = Field(default=None, min_length=1, max_length=128)
    choices: list[_WireStreamChoice]
    usage: _WireUsage | None = None


def _usage(value: _WireUsage | None) -> Usage | None:
    if value is None:
        return None
    return Usage(
        input_tokens=value.prompt_tokens,
        output_tokens=value.completion_tokens,
        total_tokens=value.total_tokens,
        cache_hit_tokens=value.prompt_cache_hit_tokens,
        cache_miss_tokens=value.prompt_cache_miss_tokens,
    )


def _normalize_chat(content: bytes) -> ChatResult:
    try:
        response = _WireChat.model_validate_json(content)
    except ValidationError:
        raise LLMInvalidResponseError() from None
    if not response.choices or not response.model:
        raise LLMInvalidResponseError() from None
    choice = response.choices[0]
    if not choice.message.content.strip() or choice.finish_reason != "stop":
        raise LLMInvalidResponseError() from None
    return ChatResult(
        content=choice.message.content,
        model=response.model,
        finish_reason=choice.finish_reason,
        usage=_usage(response.usage),
    )


def _normalize_stream(payload: str, fallback_model: str) -> StreamChunk | None:
    try:
        response = _WireStream.model_validate_json(payload)
    except ValidationError:
        raise LLMInvalidResponseError() from None
    if not response.choices:
        if response.usage is None:
            raise LLMInvalidResponseError() from None
        return StreamChunk(
            content="", model=response.model or fallback_model, usage=_usage(response.usage)
        )
    choice = response.choices[0]
    if choice.delta.content is None and choice.finish_reason is None and response.usage is None:
        return None  # A role-only frame carries no incremental text or finish state.
    return StreamChunk(
        content=choice.delta.content or "",
        model=response.model or fallback_model,
        finish_reason=choice.finish_reason,
        usage=_usage(response.usage),
    )


async def _sse_payloads(lines: AsyncIterator[str]) -> AsyncIterator[str]:
    parts: list[str] = []
    async for line in lines:
        if line == "":
            if parts:
                yield "\n".join(parts)
                parts.clear()
        elif line.startswith("data:"):
            parts.append(line[5:].lstrip())
    if parts:
        yield "\n".join(parts)


class OpenAICompatibleProvider:
    """One adapter for compatible endpoints; the injected client is caller-owned."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: SecretStr,
        model: str,
        timeout_seconds: float = 30.0,
        client: httpx.AsyncClient | None = None,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
        thinking: str | None = None,
        budget=None,
    ) -> None:
        try:
            url = httpx.URL(base_url)
        except (ValueError, httpx.InvalidURL):
            raise LLMConfigurationError() from None
        if (
            url.scheme not in {"http", "https"}
            or not url.host
            or url.userinfo
            or url.query
            or url.fragment
            or (url.scheme == "http" and url.host not in {"localhost", "127.0.0.1", "::1"})
            or not api_key.get_secret_value()
            or not model.strip()
            or timeout_seconds <= 0
            or (max_output_tokens is not None and not 1 <= max_output_tokens <= 32768)
            or (temperature is not None and not 0 <= temperature <= 2)
            or thinking not in {None, "enabled", "disabled"}
        ):
            raise LLMConfigurationError() from None
        self._endpoint = f"{str(url).rstrip('/')}/chat/completions"
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds
        self._client = client
        self._max_output_tokens = max_output_tokens
        self._temperature = temperature
        self._thinking = thinking
        self._budget = budget

    def __repr__(self) -> str:
        return "OpenAICompatibleProvider(<redacted>)"

    @asynccontextmanager
    async def _client_for_request(self) -> AsyncIterator[httpx.AsyncClient]:
        if self._client is not None:
            yield self._client
        else:
            async with httpx.AsyncClient(timeout=self._timeout, trust_env=False) as client:
                yield client

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }

    def _payload(
        self,
        messages: Sequence[LLMMessage],
        model: str | None,
        temperature: float | None,
        *,
        stream: bool = False,
        structured: bool = False,
    ) -> dict[str, object]:
        if not messages or (temperature is not None and not 0 <= temperature <= 2):
            raise LLMConfigurationError() from None
        selected_model = model or self._model
        if not selected_model.strip():
            raise LLMConfigurationError() from None
        payload: dict[str, object] = {
            "model": selected_model,
            "messages": [message.model_dump() for message in messages],
        }
        if temperature is not None:
            payload["temperature"] = temperature
        elif self._temperature is not None:
            payload["temperature"] = self._temperature
        if self._max_output_tokens is not None:
            payload["max_tokens"] = self._max_output_tokens
        if self._thinking is not None:
            payload["thinking"] = {"type": self._thinking}
        if stream:
            payload["stream"] = True
            payload["stream_options"] = {"include_usage": True}
        if structured:
            payload["response_format"] = {"type": "json_object"}
        return payload

    @staticmethod
    def _check_status(status_code: int) -> None:
        if status_code in {401, 403}:
            raise LLMAuthenticationError() from None
        if status_code == 429:
            raise LLMRateLimitError() from None
        if status_code >= 500 or 300 <= status_code < 400:
            raise LLMUnavailableError() from None
        if status_code >= 400:
            raise LLMProviderError() from None

    async def _chat_request(
        self,
        messages: Sequence[LLMMessage],
        model: str | None,
        temperature: float | None,
        *,
        structured: bool = False,
    ) -> ChatResult:
        payload = self._payload(messages, model, temperature, structured=structured)
        if self._budget is not None:
            self._budget.reserve(payload)
        try:
            async with self._client_for_request() as client:
                response = await client.post(
                    self._endpoint,
                    headers=self._headers(),
                    json=payload,
                    timeout=self._timeout,
                )
        except httpx.TimeoutException:
            raise LLMTimeoutError() from None
        except httpx.RequestError:
            raise LLMUnavailableError() from None
        self._check_status(response.status_code)
        result = _normalize_chat(response.content)
        capture_response(result)
        return result

    async def chat(
        self,
        messages: Sequence[LLMMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> ChatResult:
        with provider_scope(self, "chat"):
            return await self._chat_request(messages, model, temperature)

    async def structured_output(
        self,
        messages: Sequence[LLMMessage],
        schema: type[SchemaT],
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> SchemaT:
        # JSON object mode does not transmit or enforce the caller's Pydantic schema.
        schema_instruction = "Return JSON conforming exactly to this JSON Schema: " + json.dumps(
            schema.model_json_schema(), ensure_ascii=False
        )
        supplied = list(messages)
        if supplied and supplied[0].role == "system":
            supplied[0] = LLMMessage(
                role="system", content=supplied[0].content + "\n" + schema_instruction
            )
        else:
            supplied.insert(0, LLMMessage(role="system", content=schema_instruction))
        with provider_scope(self, "structured_output") as record:
            record["schema"] = schema.__name__
            result = await self._chat_request(supplied, model, temperature, structured=True)
            return validate_structured_output(result.content, schema)

    async def stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[StreamChunk]:
        with provider_scope(self, "stream") as record:
            started = perf_counter()
            inner = self._stream(messages, model=model, temperature=temperature)
            try:
                async for chunk in inner:
                    capture_response(chunk)
                    if chunk.content and record["ttft_ms"] is None:
                        record["ttft_ms"] = (perf_counter() - started) * 1000
                    yield chunk
            finally:
                await inner.aclose()

    async def _stream(self, messages, *, model=None, temperature=None):
        payload = self._payload(messages, model, temperature, stream=True)
        if self._budget is not None:
            self._budget.reserve(payload)
        selected_model = model or self._model
        done = False
        finished = False
        has_content = False
        try:
            async with self._client_for_request() as client:
                async with client.stream(
                    "POST",
                    self._endpoint,
                    headers=self._headers(),
                    json=payload,
                    timeout=self._timeout,
                ) as response:
                    self._check_status(response.status_code)
                    async for event in _sse_payloads(response.aiter_lines()):
                        if event == "[DONE]":
                            done = True
                            break
                        chunk = _normalize_stream(event, selected_model)
                        if chunk is not None:
                            has_content = has_content or bool(chunk.content.strip())
                            if chunk.finish_reason is not None:
                                if chunk.finish_reason != "stop":
                                    raise LLMInvalidResponseError() from None
                                finished = True
                            yield chunk
        except httpx.TimeoutException:
            raise LLMTimeoutError() from None
        except httpx.RequestError:
            raise LLMUnavailableError() from None
        if not done or not finished or not has_content:
            raise LLMInvalidResponseError() from None
