"""Actual adapter-wire reservations and durable no-replay checks without a network."""

import asyncio
import json

import httpx
import pytest
from pydantic import SecretStr

from app.llm.errors import LLMConfigurationError, LLMTimeoutError
from app.llm.models import LLMMessage
from evals.ica.live import BatchBudget, RecordedProvider, write_new


def plan(**changes):
    return {
        "model": "deepseek-flash",
        "max_output_tokens": 100,
        "max_requests": 2,
        "max_reserved_tokens": 100000,
        "max_cost_cny": "20",
        **changes,
    }


def payload():
    return {
        "model": "deepseek-flash",
        "max_tokens": 100,
        "messages": [{"role": "system", "content": "😀 schema " * 100}],
    }


def test_prepaid_failure_unknown_and_global_caps_are_not_refunded(tmp_path):
    budget = BatchBudget(tmp_path, plan(max_requests=1))
    budget.reserve(payload())
    saved = json.loads(budget.path.read_text().splitlines()[0])
    assert saved["status"] == "admitted"
    assert saved["wire_bytes"] == len(json.dumps(payload(), ensure_ascii=False).encode())
    budget.finish(0, None, "LLMTimeoutError", 1)
    assert budget.calls[0]["status"] == "unknown" and budget.reserved > 0
    with pytest.raises(LLMConfigurationError):
        budget.reserve(payload())
    assert budget.exhausted and len(budget.calls) == 1
    with pytest.raises(ValueError, match="replay forbidden"):
        BatchBudget(tmp_path, plan())


@pytest.mark.parametrize("changes", [{"max_reserved_tokens": 1}, {"max_cost_cny": "0.00001"}])
def test_token_and_money_caps_reject_before_any_admission(tmp_path, changes):
    budget = BatchBudget(tmp_path, plan(**changes))
    with pytest.raises(LLMConfigurationError):
        budget.reserve(payload())
    assert not budget.path.exists() and budget.calls == []


def test_batch_claim_is_exclusive_and_never_overwrites_evidence(tmp_path):
    path = tmp_path / "claimed.json"
    write_new(path, {"first": True})
    with pytest.raises(FileExistsError):
        write_new(path, {"first": False})
    assert json.loads(path.read_text()) == {"first": True}


def test_real_adapter_records_usage_or_unknown_without_retry(tmp_path):
    budget = BatchBudget(tmp_path, plan())
    sends = []

    def handler(request):
        sends.append(json.loads(request.content))
        assert len(budget.calls) == len(sends)
        if len(sends) == 2:
            raise httpx.ReadTimeout("synthetic timeout")
        return httpx.Response(
            200,
            json={
                "model": "DeepSeek-V4.1-Flash-1017",
                "choices": [
                    {
                        "message": {"content": "visible", "reasoning_content": "PRIVATE"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
            },
        )

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = RecordedProvider(
                base_url="https://api.deepseek.com",
                api_key=SecretStr("synthetic-secret"),
                model="deepseek-flash",
                max_output_tokens=100,
                client=client,
                budget=budget,
            )
            messages = [LLMMessage(role="user", content="anonymous")]
            assert (await provider.chat(messages)).content == "visible"
            with pytest.raises(LLMTimeoutError):
                await provider.chat(messages)

    asyncio.run(exercise())
    log = budget.path.read_text()
    assert len(sends) == 2 and budget.calls[0]["usage"]["total_tokens"] == 12
    assert budget.calls[1]["status"] == "unknown"
    assert "PRIVATE" not in log and "synthetic-secret" not in log
