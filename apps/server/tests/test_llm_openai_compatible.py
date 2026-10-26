"""All compatible-provider tests use HTTPX MockTransport; no external requests."""

import asyncio
import hmac
import json
import logging

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, SecretStr

from app.core.config import Settings
from app.llm import LLMMessage, create_llm_provider
from app.llm.errors import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMInvalidResponseError,
    LLMProviderError,
    LLMRateLimitError,
    LLMStructuredOutputError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.llm.openai_compatible import OpenAICompatibleProvider
from app.main import create_app

KEY = "phase2c-secret-key"
MESSAGES = [LLMMessage(role="system", content="test"), LLMMessage(role="user", content="hello")]


class SmallSchema(BaseModel):
    label: str
    count: int


def assert_secret_hidden(value: str) -> None:
    if KEY in value:
        pytest.fail("Secret exposure detected", pytrace=False)


def wire_response(content: str = "hello back") -> dict[str, object]:
    return {
        "model": "server-model",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": content,
                    "reasoning_content": "hidden reasoning must be discarded",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 4, "completion_tokens": 6, "total_tokens": 10},
    }


def make_provider(client: httpx.AsyncClient) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        base_url="https://compatible.example/v1",
        api_key=SecretStr(KEY),
        model="configured-model",
        client=client,
    )


def test_factory_creates_compatible_provider_and_requires_configuration() -> None:
    settings = Settings(
        llm_provider="openai_compatible",
        llm_base_url="https://compatible.example/v1",
        llm_model="configured-model",
        llm_api_key=KEY,
        _env_file=None,
    )
    provider = create_llm_provider(settings)
    assert isinstance(provider, OpenAICompatibleProvider)
    assert_secret_hidden(repr(provider))
    assert_secret_hidden(repr(settings))
    with pytest.raises(LLMConfigurationError):
        create_llm_provider(
            Settings(llm_provider="openai_compatible", llm_api_key=None, _env_file=None)
        )
    with pytest.raises(LLMConfigurationError):
        OpenAICompatibleProvider(
            base_url="http://remote.example/v1", api_key=SecretStr(KEY), model="m"
        )


def test_chat_builds_request_and_normalizes_response() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=wire_response())

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await make_provider(client).chat(MESSAGES, model="override", temperature=0.3)

    result = asyncio.run(run())
    request = captured[0]
    assert request.method == "POST"
    assert str(request.url) == "https://compatible.example/v1/chat/completions"
    if not hmac.compare_digest(request.headers.get("Authorization", ""), f"Bearer {KEY}"):
        pytest.fail("Authorization header mismatch", pytrace=False)
    assert json.loads(request.content) == {
        "model": "override",
        "messages": [{"role": "system", "content": "test"}, {"role": "user", "content": "hello"}],
        "temperature": 0.3,
    }
    assert result.content == "hello back"
    assert result.model == "server-model"
    assert result.finish_reason == "stop"
    assert result.usage.input_tokens == 4
    assert result.usage.output_tokens == 6
    assert result.usage.total_tokens == 10
    assert "hidden reasoning" not in repr(result)


@pytest.mark.parametrize(
    ("base_url", "expected_url"),
    [
        ("https://api.openai.com/v1", "https://api.openai.com/v1/chat/completions"),
        ("https://api.deepseek.com", "https://api.deepseek.com/chat/completions"),
        (
            "https://workspace.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
            "https://workspace.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/chat/completions",
        ),
    ],
)
def test_compatible_base_url_shapes(base_url: str, expected_url: str) -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json=wire_response())

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleProvider(
                base_url=base_url, api_key=SecretStr(KEY), model="m", client=client
            )
            return await provider.chat(MESSAGES)

    assert asyncio.run(run()).content == "hello back"
    assert seen == [expected_url]


def test_structured_output_requests_json_mode_and_validates() -> None:
    bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=wire_response('{"label":"ok","count":2}'))

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await make_provider(client).structured_output(MESSAGES, SmallSchema)

    assert asyncio.run(run()) == SmallSchema(label="ok", count=2)
    assert bodies[0]["response_format"] == {"type": "json_object"}


@pytest.mark.parametrize(
    "content", ["{not-json", '{"label":"missing"}', '{"label":"x","count":"2"}']
)
def test_structured_output_rejects_invalid_json_and_schema(content: str) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=wire_response(content))

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await make_provider(client).structured_output(MESSAGES, SmallSchema)

    with pytest.raises(LLMStructuredOutputError) as caught:
        asyncio.run(run())
    assert content not in str(caught.value)


def test_stream_normalizes_deltas_finish_usage_and_discards_reasoning() -> None:
    captured: list[dict[str, object]] = []
    frames = [
        {
            "model": "server-model",
            "choices": [{"delta": {"role": "assistant"}, "finish_reason": None}],
        },
        {
            "model": "server-model",
            "choices": [
                {"delta": {"content": "Hel", "reasoning_content": "hidden"}, "finish_reason": None}
            ],
        },
        {"model": "server-model", "choices": [{"delta": {"content": "lo"}, "finish_reason": None}]},
        {"model": "server-model", "choices": [{"delta": {}, "finish_reason": "stop"}]},
        {
            "model": "server-model",
            "choices": [],
            "usage": {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
        },
    ]
    body = "".join(f"data: {json.dumps(frame)}\n\n" for frame in frames) + "data: [DONE]\n\n"

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(json.loads(request.content))
        return httpx.Response(200, text=body, headers={"content-type": "text/event-stream"})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return [chunk async for chunk in make_provider(client).stream(MESSAGES)]

    chunks = asyncio.run(run())
    assert captured[0]["stream"] is True
    assert [chunk.content for chunk in chunks] == ["Hel", "lo", "", ""]
    assert chunks[2].finish_reason == "stop"
    assert chunks[3].usage.total_tokens == 6
    assert all("hidden" not in repr(chunk) for chunk in chunks)


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (401, LLMAuthenticationError),
        (403, LLMAuthenticationError),
        (429, LLMRateLimitError),
        (503, LLMUnavailableError),
        (400, LLMProviderError),
    ],
)
def test_http_failures_are_mapped_without_response_body(
    status: int, error_type: type[Exception], caplog: pytest.LogCaptureFixture
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text=f"{KEY} private request body")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await make_provider(client).chat(MESSAGES)

    with caplog.at_level(logging.DEBUG), pytest.raises(error_type) as caught:
        asyncio.run(run())
    assert_secret_hidden(str(caught.value))
    assert_secret_hidden(repr(caught.value))
    assert "private request body" not in str(caught.value)
    assert_secret_hidden(caplog.text)


@pytest.mark.parametrize(
    ("raised", "expected"),
    [
        (httpx.ReadTimeout("private timeout"), LLMTimeoutError),
        (httpx.ConnectError("private transport"), LLMUnavailableError),
    ],
)
def test_transport_failures_are_mapped(raised: Exception, expected: type[Exception]) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise raised

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await make_provider(client).chat(MESSAGES)

    with pytest.raises(expected) as caught:
        asyncio.run(run())
    assert "private" not in str(caught.value)


@pytest.mark.parametrize("payload", [b"not-json", b'{"model":"m","choices":[]}'])
def test_invalid_chat_response_is_controlled(payload: bytes) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=payload)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await make_provider(client).chat(MESSAGES)

    with pytest.raises(LLMInvalidResponseError):
        asyncio.run(run())


def test_truncated_stream_is_invalid_response() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text='data: {"choices":[{"delta":{"content":"partial"}}]}\n\n')

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return [chunk async for chunk in make_provider(client).stream(MESSAGES)]

    with pytest.raises(LLMInvalidResponseError):
        asyncio.run(run())


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (httpx.Response(401, text="private upstream auth body"), LLMAuthenticationError),
        (httpx.Response(429, text="private upstream rate body"), LLMRateLimitError),
        (httpx.Response(200, text="data: {bad-json}\n\ndata: [DONE]\n\n"), LLMInvalidResponseError),
    ],
)
def test_stream_failures_are_normalized(
    response: httpx.Response, expected: type[Exception]
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return response

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return [chunk async for chunk in make_provider(client).stream(MESSAGES)]

    with pytest.raises(expected):
        asyncio.run(run())


def test_stream_timeout_is_mapped_without_raw_transport_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("private request content")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return [chunk async for chunk in make_provider(client).stream(MESSAGES)]

    with pytest.raises(LLMTimeoutError) as caught:
        asyncio.run(run())
    if "private request content" in str(caught.value):
        pytest.fail("Private transport error leaked", pytrace=False)


def test_server_startup_and_status_do_not_touch_llm_or_expose_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_init(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("LLM provider constructed during app startup")

    monkeypatch.setattr(OpenAICompatibleProvider, "__init__", forbidden_init)
    settings = Settings(llm_provider="openai_compatible", llm_api_key=KEY, _env_file=None)
    with TestClient(create_app(settings)) as client:
        health = client.get("/health")
        status = client.get("/api/v1/status")
    assert health.status_code == 200
    assert status.status_code == 200
    assert_secret_hidden(status.text)


def test_default_http_clients_close_after_chat_and_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    original_client = httpx.AsyncClient
    opened: list[httpx.AsyncClient] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if json.loads(request.content).get("stream"):
            frame = json.dumps({"model": "m", "choices": [{"delta": {"content": "x"}}]})
            end = json.dumps({"model": "m", "choices": [{"delta": {}, "finish_reason": "stop"}]})
            return httpx.Response(200, text=f"data: {frame}\n\ndata: {end}\n\ndata: [DONE]\n\n")
        return httpx.Response(200, json=wire_response())

    def new_client(*_args: object, **kwargs: object) -> httpx.AsyncClient:
        client = original_client(transport=httpx.MockTransport(handler), **kwargs)
        opened.append(client)
        return client

    monkeypatch.setattr("app.llm.openai_compatible.httpx.AsyncClient", new_client)
    provider = OpenAICompatibleProvider(
        base_url="https://compatible.example/v1", api_key=SecretStr(KEY), model="m"
    )

    async def run() -> None:
        await provider.chat(MESSAGES)
        assert [chunk.content async for chunk in provider.stream(MESSAGES)] == ["x", ""]

    asyncio.run(run())
    assert len(opened) == 2
    assert all(client.is_closed for client in opened)
