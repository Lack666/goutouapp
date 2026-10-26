"""Real adapter → graph → signed API → PostgreSQL failure/idempotency contract."""

import json
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr
from test_agent_rest import create_client, headers, persisted, scope

from app.llm.openai_compatible import OpenAICompatibleProvider


@pytest.mark.parametrize(
    "fault", ["timeout", "429", "503", "disconnect", "empty", "invalid_json", "schema", "truncated"]
)
def test_provider_failure_is_durable_and_same_key_never_reexecutes(
    database_engine, monkeypatch, fault
):
    calls = []

    def handler(request):
        calls.append(1)
        if fault == "timeout":
            raise httpx.ReadTimeout("private")
        if fault == "disconnect":
            raise httpx.ConnectError("private")
        if fault in {"429", "503"}:
            return httpx.Response(int(fault), text="private-secret")
        content = {
            "empty": "",
            "invalid_json": "{broken",
            "schema": '{"wrong":1}',
            "truncated": "{partial",
        }[fault]
        return httpx.Response(
            200,
            json={
                "model": "fault-model",
                "choices": [
                    {
                        "message": {"content": content},
                        "finish_reason": "length" if fault == "truncated" else "stop",
                    }
                ],
            },
        )

    provider = OpenAICompatibleProvider(
        base_url="https://example.invalid",
        api_key=SecretStr("private-secret"),
        model="m",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    user, conversation, _, _ = scope(database_engine)
    _, client = create_client(database_engine, monkeypatch, provider)
    body = {"message": "匿名合成测试", "operation_key": uuid4().hex}
    path = f"/api/v1/conversations/{conversation}/agent-runs"
    with client:
        first = client.post(path, json=body, headers=headers(user))
        second = client.post(path, json=body, headers=headers(user))
    assert first.status_code != 200 and second.status_code != 200
    assert len(calls) == 1
    messages, runs = persisted(database_engine, conversation)
    assert len(runs) == 1 and runs[0].status == "failed"
    assert [m.role for m in messages] == ["user"]
    assert "private" not in first.text + second.text


@pytest.mark.parametrize(
    "body",
    [
        "data: [DONE]\n\n",
        'data: {"model":"m","choices":[{"delta":{"content":"partial"}}]}\n\ndata: [DONE]\n\n',
        'data: {"model":"m","choices":[{"delta":{},"finish_reason":"length"}]}\n\ndata: [DONE]\n\n',
    ],
)
def test_broken_or_empty_stream_never_completes(body):
    import asyncio

    from app.llm.errors import LLMInvalidResponseError
    from app.llm.models import LLMMessage
    from app.observability import TRACES

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, text=body))
        ) as client:
            provider = OpenAICompatibleProvider(
                base_url="https://example.invalid",
                api_key=SecretStr("secret"),
                model="m",
                client=client,
            )
            return [c async for c in provider.stream([LLMMessage(role="user", content="private")])]

    with pytest.raises(LLMInvalidResponseError):
        asyncio.run(run())
    assert TRACES.snapshot()[-1]["status"] == "failed"
    assert "private" not in json.dumps(TRACES.snapshot()[-1])
