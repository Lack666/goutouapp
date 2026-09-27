"""Text-only OpenAI-compatible Chat Completions transport and normalization."""

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager

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


class _WireModel(BaseModel):
    # Provider-specific fields, including hidden reasoning content, are discarded.
    model_config = ConfigDict(strict=True, extra="ignore")


class _WireUsage(_WireModel):
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class _WireMessage(_WireModel):
    content: str


class _WireChoice(_WireModel):
    message: _WireMessage
    finish_reason: str | None = None


class _WireChat(_WireModel):
    model: str
    choices: list[_WireChoice]
    usage: _WireUsage | None = None


class _WireDelta(_WireModel):
    content: str | None = None


class _WireStreamChoice(_WireModel):
    delta: _WireDelta
    finish_reason: str | None = None


class _WireStream(_WireModel):
    model: str | None = None
    choices: list[_WireStreamChoice]
    usage: _WireUsage | None = None


def _usage(value: _WireUsage | None) -> Usage | None:
    if value is None:
        return None
    return Usage(
        input_tokens=value.prompt_tokens,
        output_tokens=value.completion_tokens,
        total_tokens=value.total_tokens,
    )


def _normalize_chat(content: bytes) -> ChatResult:
    try:
        response = _WireChat.model_validate_json(content)
    except ValidationError:
        raise LLMInvalidResponseError() from None
    if not response.choices or not response.model:
        raise LLMInvalidResponseError() from None
    choice = response.choices[0]
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
        ):
            raise LLMConfigurationError() from None
        self._endpoint = f"{str(url).rstrip('/')}/chat/completions"
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds
        self._client = client

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
        if stream:
            payload["stream"] = True
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
        return _normalize_chat(response.content)

    async def chat(
        self,
        messages: Sequence[LLMMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> ChatResult:
        return await self._chat_request(messages, model, temperature)

    async def structured_output(
        self,
        messages: Sequence[LLMMessage],
        schema: type[SchemaT],
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> SchemaT:
        result = await self._chat_request(messages, model, temperature, structured=True)
        return validate_structured_output(result.content, schema)

    async def stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[StreamChunk]:
        payload = self._payload(messages, model, temperature, stream=True)
        selected_model = model or self._model
        done = False
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
                            yield chunk
        except httpx.TimeoutException:
            raise LLMTimeoutError() from None
        except httpx.RequestError:
            raise LLMUnavailableError() from None
        if not done:
            raise LLMInvalidResponseError() from None
