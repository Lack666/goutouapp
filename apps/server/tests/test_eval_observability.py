"""Phase11 diagnostics, budget, privacy, deterministic dataset and boundary checks."""

import asyncio
import json
from collections import Counter
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr

from app.agent.contracts import AgentInput, SafetyResult
from app.agent.dependencies import RuntimeDependencies
from app.agent.runtime import AgentRuntime
from app.core.config import Settings
from app.llm.errors import LLMConfigurationError, LLMInvalidResponseError, LLMStructuredOutputError
from app.llm.eval_budget import EvalBudget, cost_cny
from app.llm.models import LLMMessage
from app.llm.openai_compatible import OpenAICompatibleProvider
from app.observability import TRACES, TraceBuffer
from evals.agent.build_dataset import build
from evals.agent.harness import cases, evaluate, live_provider, mock_provider


def test_dataset_is_authored_complete_and_deterministic():
    assert cases() == build()
    assert Counter(c["category"] for c in cases()) == {
        "communication": 12,
        "grounding": 12,
        "safety": 12,
        "privacy_injection": 8,
        "memory": 8,
        "fault_boundary": 8,
    }
    first, second = asyncio.run(evaluate(cases())), asyncio.run(evaluate(cases()))
    assert all(r["passed"] for r in first[0] + second[0])
    for left, right in zip(first[0], second[0], strict=True):
        assert left["checks"] == right["checks"]
        assert left["result"].keys() == right["result"].keys()
        a, b = dict(left["result"]), dict(right["result"])
        a.pop("run_id")
        b.pop("run_id")
        assert a == b


def test_live_is_never_default():
    with pytest.raises(RuntimeError, match="OPT_IN"):
        live_provider(Settings(_env_file=None, eval_live_opt_in=False))


def test_budget_reserves_failures_and_rejects_unknown_pricing():
    budget = EvalBudget(max_requests=1)
    body = {
        "model": "deepseek-flash",
        "messages": [{"role": "user", "content": "🙂"}],
        "max_tokens": 100,
    }
    budget.reserve(body)
    assert budget.requests == 1 and budget.reserved_cny > 0
    with pytest.raises(LLMConfigurationError):
        budget.reserve(body)
    with pytest.raises(LLMConfigurationError):
        EvalBudget().reserve({**body, "model": "unknown"})
    with pytest.raises(LLMConfigurationError):
        EvalBudget(max_cost_cny=0.000001).reserve(body)
    with pytest.raises(LLMConfigurationError):
        EvalBudget(max_tokens=1).reserve(body)
    assert cost_cny(None) is None
    assert cost_cny({"input_tokens": 20, "output_tokens": 10}) is None
    assert (
        cost_cny(
            {
                "input_tokens": 20,
                "output_tokens": 10,
                "cache_hit_tokens": 10,
                "cache_miss_tokens": 10,
            }
        )
        == 0.0001004
    )


def test_trace_order_correlation_failures_and_content_privacy(monkeypatch):
    case = cases()[24]
    secret = "PRIVATE-BODY-and-Authorization"
    request = AgentInput(user_id=uuid4(), conversation_id=uuid4(), message=secret)
    runtime = AgentRuntime(dependencies=RuntimeDependencies(llm_provider=mock_provider(case)))
    result = asyncio.run(runtime.run(request))
    events = [e for e in TRACES.snapshot() if e["run_id"] == str(result.run_id)]
    assert events[0]["kind"] == "run_start" and events[-1]["kind"] == "run_end"
    assert [e["status"] for e in events if e["kind"] == "outcome"] == ["completed"]
    starts = [e["node"] for e in events if e["kind"] == "node_start"]
    ends = [e["node"] for e in events if e["kind"] == "node_end"]
    assert starts == ends
    assert starts == [
        "normalize_input",
        "load_memory",
        "safety_check",
        "knowledge_router",
        "load_references",
        "safety_finalize",
    ]
    assert secret not in json.dumps(events)
    monkeypatch.setattr(TRACES, "emit", lambda _: (_ for _ in ()).throw(RuntimeError(secret)))
    runtime = AgentRuntime(dependencies=RuntimeDependencies(llm_provider=mock_provider(case)))
    assert asyncio.run(runtime.run(request)).status == "completed"


def test_bounded_trace_and_retention():
    buf = TraceBuffer(capacity=2, retention_seconds=1)
    for i in range(4):
        buf.emit({"n": i})
    assert buf.snapshot() == [{"n": 2}, {"n": 3}]
    buf.events.appendleft((0, {"expired": True}))
    assert len(buf.snapshot()) == 2


@pytest.mark.parametrize("content,finish", [("", "stop"), ("x", "length"), ("x", None)])
def test_empty_and_incomplete_chat_never_success(content, finish):
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(
                    200,
                    json={
                        "model": "m",
                        "choices": [{"message": {"content": content}, "finish_reason": finish}],
                    },
                )
            )
        ) as client:
            provider = OpenAICompatibleProvider(
                base_url="https://example.invalid",
                api_key=SecretStr("secret"),
                model="m",
                client=client,
            )
            await provider.chat([LLMMessage(role="user", content="private")])

    with pytest.raises(LLMInvalidResponseError):
        asyncio.run(run())


def test_structured_usage_captured_even_when_schema_fails():
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(
                    200,
                    json={
                        "model": "wire-model",
                        "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
                        "usage": {
                            "prompt_tokens": 2,
                            "completion_tokens": 1,
                            "total_tokens": 3,
                            "prompt_cache_hit_tokens": 0,
                            "prompt_cache_miss_tokens": 2,
                        },
                    },
                )
            )
        ) as client:
            provider = OpenAICompatibleProvider(
                base_url="https://example.invalid",
                api_key=SecretStr("secret"),
                model="m",
                client=client,
            )
            await provider.structured_output(
                [LLMMessage(role="user", content="private")], SafetyResult
            )

    with pytest.raises(LLMStructuredOutputError):
        asyncio.run(run())
    event = TRACES.snapshot()[-1]
    assert event["status"] == "failed" and event["model"] == "wire-model"
    assert event["usage"]["total_tokens"] == 3
    assert "private" not in json.dumps(event) and "secret" not in json.dumps(event)


def test_runtime_cancel_has_terminal_failed_node():
    class Waiting:
        async def structured_output(self, *args, **kwargs):
            await asyncio.sleep(100)

    async def run():
        request = AgentInput(
            run_id=uuid4(), user_id=uuid4(), conversation_id=uuid4(), message="private"
        )
        runtime = AgentRuntime(dependencies=RuntimeDependencies(llm_provider=Waiting()))
        task = asyncio.create_task(runtime.run(request))
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        return [e for e in TRACES.snapshot() if e["run_id"] == str(request.run_id)]

    events = asyncio.run(run())
    assert next(e for e in events if e["kind"] == "outcome")["status"] == "cancelled"
    assert [e for e in events if e["kind"] == "node_end"][-1]["error"] == "cancelled"


def test_human_review_requires_scores_and_exact_visible_output():
    from evals.agent.review import packet, validate_reviews

    rows, _, _ = asyncio.run(evaluate(cases()[:1]))
    doc = packet(rows)
    assert validate_reviews(doc, rows) == []
    item = doc["items"][0]
    item.update(
        reviewer="synthetic-test-reviewer",
        reviewed_at="2026-10-26T00:00:00Z",
        reason="Fixture only; not a real evaluation review",
    )
    with pytest.raises(ValueError):
        validate_reviews(doc, rows)
    item["scores"] = {key: 3 for key in item["scores"]}
    assert len(validate_reviews(doc, rows)) == 1
    item["output_sha256"] = "wrong"
    with pytest.raises(ValueError):
        validate_reviews(doc, rows)
