"""Keyless provider behavior with deterministic, injectable responses."""

import asyncio

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.config import Settings
from app.llm import LLMMessage, StreamChunk, Usage, create_llm_provider
from app.llm.errors import (
    LLMConfigurationError,
    LLMStructuredOutputError,
    LLMTimeoutError,
)
from app.llm.mock import MockLLMProvider
from app.main import create_app

MESSAGES = [LLMMessage(role="user", content="synthetic input")]


class SmallSchema(BaseModel):
    label: str
    count: int


def test_factory_selects_mock_without_key_and_rejects_unknown() -> None:
    provider = create_llm_provider(Settings(llm_provider="mock", llm_api_key=None, _env_file=None))
    assert isinstance(provider, MockLLMProvider)
    with pytest.raises(LLMConfigurationError):
        create_llm_provider(Settings(llm_provider="other", _env_file=None))


def test_mock_configuration_starts_server_without_key() -> None:
    settings = Settings(llm_provider="mock", llm_api_key=None, _env_file=None)
    with TestClient(create_app(settings)) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/api/v1/status").status_code == 200


def test_mock_chat_queue_and_typed_usage() -> None:
    provider = MockLLMProvider()
    provider.queue_chat("first", usage=Usage(input_tokens=2, output_tokens=3, total_tokens=5))
    provider.queue_chat("second")
    first = asyncio.run(provider.chat(MESSAGES, model="test-model", temperature=0.4))
    second = asyncio.run(provider.chat(MESSAGES))
    assert first.content == "first"
    assert first.model == "test-model"
    assert first.finish_reason == "stop"
    assert first.usage.total_tokens == 5
    assert second.content == "second"
    assert second.model == "mock"
    with pytest.raises(LLMConfigurationError):
        asyncio.run(provider.chat(MESSAGES))


def test_mock_stream_yields_ordered_chunks_and_finish() -> None:
    provider = MockLLMProvider()
    provider.queue_stream(
        StreamChunk(content="one"),
        StreamChunk(content="two"),
        StreamChunk(content="", finish_reason="stop"),
    )

    async def collect() -> list[StreamChunk]:
        return [chunk async for chunk in provider.stream(MESSAGES)]

    chunks = asyncio.run(collect())
    assert [chunk.content for chunk in chunks] == ["one", "two", ""]
    assert chunks[-1].finish_reason == "stop"


def test_mock_structured_output_is_strictly_validated() -> None:
    provider = MockLLMProvider()
    provider.queue_structured({"label": "ok", "count": 3})
    provider.queue_structured("{not-json")
    provider.queue_structured({"label": "missing"})
    provider.queue_structured({"label": "wrong type", "count": "3"})
    value = asyncio.run(provider.structured_output(MESSAGES, SmallSchema))
    assert value == SmallSchema(label="ok", count=3)
    for _ in range(3):
        with pytest.raises(LLMStructuredOutputError):
            asyncio.run(provider.structured_output(MESSAGES, SmallSchema))


def test_mock_can_inject_predefined_errors() -> None:
    provider = MockLLMProvider()
    provider.queue_error("chat", LLMTimeoutError())
    provider.queue_error("stream", LLMTimeoutError())
    provider.queue_error("structured_output", LLMTimeoutError())
    with pytest.raises(LLMTimeoutError):
        asyncio.run(provider.chat(MESSAGES))

    async def consume() -> None:
        async for _ in provider.stream(MESSAGES):
            pass

    with pytest.raises(LLMTimeoutError):
        asyncio.run(consume())
    with pytest.raises(LLMTimeoutError):
        asyncio.run(provider.structured_output(MESSAGES, SmallSchema))
