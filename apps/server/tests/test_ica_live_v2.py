"""Plan-bound v2 sends use synthetic keys and HTTP MockTransport only."""

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import pytest
from pydantic import SecretStr

from app.agent.imported_quote import STAGE_SCHEMAS
from app.llm.errors import LLMConfigurationError, LLMTimeoutError
from app.llm.models import ChatResult, LLMMessage, Usage
from evals.ica import live_v2
from evals.ica.live import BatchBudget, RecordedProvider, write_new


@pytest.fixture
def frozen(tmp_path, monkeypatch):
    # Source stability is controlled here; no test modifies a frozen source file.
    monkeypatch.setattr(live_v2, "fingerprint", lambda: "f" * 64)
    plan = live_v2.build_plan()
    write_new(tmp_path / "plan.json", plan)
    return tmp_path, plan


def approve(directory):
    # This is a synthetic unit-test approval, never a real paid-batch authorization.
    return live_v2.authorize(
        directory, confirmed=True, approval_reference="synthetic test-only explicit approval"
    )


def budget_for(directory):
    approve(directory)
    plan, digest = live_v2.read_plan(directory)
    return live_v2.FrozenBudget(directory, plan, digest)


def messages(body="匿名合成😀"):
    return (LLMMessage(role="user", content=body),)


def result(*, usage=True):
    value = {
        "model": "deepseek-flash",
        "choices": [
            {
                "message": {
                    "content": '{"decision":"normal","risks":[]}',
                    "reasoning_content": "HIDDEN_REASONING_CANARY",
                },
                "finish_reason": "stop",
            }
        ],
    }
    if usage:
        value["usage"] = {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12}
    return httpx.Response(200, json=value)


async def call_provider(budget, handler, count=1, body="匿名合成😀"):
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = RecordedProvider(
            base_url="https://api.deepseek.com",
            api_key=SecretStr("synthetic-secret-never-real"),
            model="deepseek-flash",
            max_output_tokens=4096,
            temperature=0,
            thinking="disabled",
            client=client,
            budget=budget,
        )
        return [
            await provider.structured_output(messages(body), STAGE_SCHEMAS["safety"])
            for _ in range(count)
        ]


def test_v2_plan_freezes_new_inventory_wire_schemas_and_balanced_order(frozen):
    directory, plan = frozen
    assert plan["version"] == "ica-bq-batch-v2"
    assert plan["case_set"] == "v2" and plan["evidence_protocol"] == "quote-v2"
    assert len(plan["case_ids"]) == 32 and len(set(plan["case_ids"])) == 32
    assert all(cid.startswith("ica-v2-") for cid in plan["case_ids"])
    assert plan["wire_schema_sha256"] == live_v2.schemas()
    assert set(plan["wire_schema_sha256"]) == set(STAGE_SCHEMAS)
    assert plan["tariff"] == live_v2.TARIFF and plan["model"] == plan["tariff"]["model"]
    assert len(plan["execution_order"]) == 64
    for i, cid in enumerate(plan["case_ids"]):
        expected = ["event", "baseline"] if i % 2 == 0 else ["baseline", "event"]
        pair = plan["execution_order"][2 * i : 2 * i + 2]
        assert [item["case_id"] for item in pair] == [cid, cid]
        assert [item["arm"] for item in pair] == expected
    assert plan["graph_requests_upper"] == 2 * sum(3 * s["K"] + 2 for s in plan["scopes"])
    assert plan["scope_requests_upper"] == 2 * sum(3 * s["K"] + 8 for s in plan["scopes"])
    assert plan["full_completion_guaranteed"] is False
    assert plan["new_budget_approval_required"] is True
    assert plan["max_cost_cny"] == "20"
    loaded, digest = live_v2.read_plan(directory)
    assert loaded == plan and digest == live_v2.sha((directory / "plan.json").read_bytes())
    assert not (directory / "authorization.json").exists()


@pytest.mark.parametrize(
    "key,value",
    [
        ("version", "ica-bq-batch-v1"),
        ("case_set", "v1"),
        ("evidence_protocol", "span-v1"),
        ("source_fingerprint", "0" * 64),
        ("model", "deepseek-v4-pro"),
        ("provider_base_url", "https://example.invalid"),
        ("max_cost_cny", "21"),
        ("max_cost_cny", 20),
        ("max_requests", 401),
        ("max_requests", 400.0),
        ("max_reserved_tokens", 10_000_001),
        ("max_output_tokens", 8192),
        ("max_input_bytes", 128 * 1024 + 1),
        ("no_retries", False),
        ("no_retries", 1),
        ("synthetic_only", 1),
        ("new_budget_approval_required", 1),
        ("temperature", False),
        ("temperature", 0.0),
        ("thinking", "enabled"),
        ("cases_sha256", "a" * 64),
        ("manifest_sha256", "b" * 64),
        ("wire_schema_sha256", {}),
        ("extra_approval_override", True),
    ],
)
def test_plan_tampering_and_boolean_numeric_aliases_reject(frozen, key, value):
    _, plan = frozen
    changed = {**plan, key: value}
    with pytest.raises(ValueError, match="Frozen v2"):
        live_v2.validate_plan(changed)


def test_plan_case_order_tariff_schema_and_scope_tampering_reject(frozen):
    _, plan = frozen
    changes = []
    for path, value in [
        (("tariff", "miss_per_million"), "0"),
        (("tariff", "output_per_million"), "1"),
        (("wire_schema_sha256", "safety"), "0" * 64),
        (("execution_order", 0, "arm"), "baseline"),
        (("scopes", 0, "K"), 999),
    ]:
        changed = deepcopy(plan)
        cursor = changed
        for step in path[:-1]:
            cursor = cursor[step]
        cursor[path[-1]] = value
        changes.append(changed)
    changes.append({**plan, "case_ids": plan["case_ids"][::-1]})
    changes.append({**plan, "arms": ["event", "event"]})
    for changed in changes:
        with pytest.raises(ValueError, match="Frozen v2"):
            live_v2.validate_plan(changed)


@pytest.mark.parametrize("confirmation", [False, 1, "true", None])
def test_approval_must_be_literal_true_before_artifact(frozen, confirmation):
    directory, _ = frozen
    with pytest.raises(ValueError, match="Fresh explicit"):
        live_v2.authorize(directory, confirmed=confirmation, approval_reference="test")
    assert not (directory / "authorization.json").exists()


@pytest.mark.parametrize("reference", ["", "  ", None, 123])
def test_approval_requires_explicit_reference(frozen, reference):
    directory, _ = frozen
    with pytest.raises(ValueError, match="Fresh explicit"):
        live_v2.authorize(directory, confirmed=True, approval_reference=reference)


def test_approval_hash_ttl_and_exclusive_consumption(frozen):
    directory, _ = frozen
    now = datetime.now(UTC)
    document = live_v2.authorize(
        directory, confirmed=True, approval_reference="synthetic test-only", now=now
    )
    plan, digest = live_v2.read_plan(directory)
    assert live_v2.check_authorization(directory, plan, digest, now=now) == document
    for clock in (now - timedelta(microseconds=1), now + timedelta(hours=24)):
        with pytest.raises(ValueError, match="Missing, expired"):
            live_v2.check_authorization(directory, plan, digest, now=clock)
    with pytest.raises(ValueError, match="Missing, expired"):
        live_v2.check_authorization(directory, plan, "0" * 64, now=now)
    with pytest.raises(FileExistsError):
        approve(directory)
    write_new(directory / "claimed.json", {"existing": True})
    with pytest.raises(ValueError, match="Claimed batch"):
        approve(directory)


@pytest.mark.parametrize(
    "field,value",
    [
        ("confirmed", 1),
        ("no_retries", 1),
        ("model", "deepseek-v4-pro"),
        ("max_cost_cny", "21"),
        ("approval_reference", " "),
        ("approved_at", "invalid"),
        ("expires_at", "2030-01-01T00:00:00+00:00"),
    ],
)
def test_changed_approval_rejected(frozen, field, value):
    directory, plan = frozen
    document = approve(directory)
    document[field] = value
    (directory / "authorization.json").write_text(json.dumps(document), encoding="utf-8")
    _, digest = live_v2.read_plan(directory)
    with pytest.raises(ValueError, match="Missing, expired"):
        live_v2.check_authorization(directory, plan, digest)


def test_missing_approval_stops_before_claim_key_or_provider(frozen, monkeypatch):
    directory, _ = frozen

    def forbidden(*args, **kwargs):
        pytest.fail("No key access or Provider construction without fresh authorization")

    monkeypatch.setattr(live_v2, "private_key", forbidden)
    monkeypatch.setattr(live_v2, "RecordedProvider", forbidden)
    with pytest.raises(ValueError, match="Missing, expired"):
        asyncio.run(live_v2.run_batch(directory))
    assert not (directory / "claimed.json").exists()
    assert not (directory / "calls.jsonl").exists()


def test_concurrent_claim_allows_only_one_key_access_no_restart(frozen, monkeypatch):
    directory, _ = frozen
    approve(directory)
    key_access = []

    class SyntheticInterrupted(Exception):
        pass

    def key():
        key_access.append("synthetic-only")
        return SecretStr("synthetic-never-real")

    def interrupted_provider(**kwargs):
        raise SyntheticInterrupted()

    def attempt():
        try:
            asyncio.run(live_v2.run_batch(directory))
        except (SyntheticInterrupted, FileExistsError) as exc:
            return type(exc)
        pytest.fail("Synthetic constructor must interrupt before HTTP")

    monkeypatch.setattr(live_v2, "private_key", key)
    monkeypatch.setattr(live_v2, "RecordedProvider", interrupted_provider)
    with ThreadPoolExecutor(2) as pool:
        outcomes = list(pool.map(lambda _: attempt(), range(2)))
    assert set(outcomes) == {SyntheticInterrupted, FileExistsError}
    assert key_access == ["synthetic-only"]
    assert not (directory / "calls.jsonl").exists()
    assert attempt() is FileExistsError and len(key_access) == 1


def test_actual_adapter_wire_reserved_before_mock_send_and_uses_quote_schema(frozen):
    directory, _ = frozen
    budget, sends = budget_for(directory), []

    def handler(request):
        wire = json.loads(request.content)
        sends.append(wire)
        ledger = [json.loads(line) for line in budget.path.read_text().splitlines()]
        assert len(ledger) == 1 and ledger[0]["status"] == "admitted"
        assert "QuotedEvidenceRef" in wire["messages"][0]["content"]
        assert wire["max_tokens"] == 4096 and wire["thinking"] == {"type": "disabled"}
        assert wire["response_format"] == {"type": "json_object"}
        return result()

    outputs = asyncio.run(call_provider(budget, handler))
    assert outputs[0].decision == "normal" and len(sends) == 1
    wire_bytes = len(json.dumps(sends[0], ensure_ascii=False).encode())
    assert budget.calls[0]["wire_bytes"] == wire_bytes
    expected = (Decimal(wire_bytes + 4096) * 2 + 4096 * 8) / 1_000_000
    assert budget.reserved == expected
    assert budget.calls[0]["usage"]["total_tokens"] == 12
    assert not budget.exhausted
    text = budget.path.read_text()
    assert "synthetic-secret-never-real" not in text and "HIDDEN_REASONING_CANARY" not in text


def test_source_drift_on_second_request_admits_no_second_send(frozen, monkeypatch):
    directory, _ = frozen
    budget, sends = budget_for(directory), []

    def handler(request):
        sends.append(request)
        monkeypatch.setattr(live_v2, "fingerprint", lambda: "e" * 64)
        return result()

    with pytest.raises(LLMConfigurationError):
        asyncio.run(call_provider(budget, handler, count=2))
    assert len(sends) == len(budget.calls) == 1 and budget.exhausted
    assert budget.calls[0]["status"] == "returned"


def test_schema_drift_rejects_before_first_send(frozen, monkeypatch):
    directory, _ = frozen
    budget, sends = budget_for(directory), []
    original = live_v2.schemas()
    monkeypatch.setattr(live_v2, "schemas", lambda: {**original, "safety": "0" * 64})

    def handler(request):
        sends.append(request)
        return result()

    with pytest.raises(LLMConfigurationError):
        asyncio.run(call_provider(budget, handler))
    assert not sends and not budget.calls and budget.exhausted
    assert not budget.path.exists()


def test_payload_bytes_plan_bytes_and_approval_changes_fail_before_send(frozen):
    directory, _ = frozen
    budget, sends = budget_for(directory), []

    def handler(request):
        sends.append(request)
        return result()

    with pytest.raises(LLMConfigurationError):
        asyncio.run(call_provider(budget, handler, body="😀" * 40000))
    assert not sends and not budget.calls and budget.exhausted
    # Whitespace changes preserve JSON semantics but invalidate the approved exact plan bytes.
    (directory / "plan.json").write_bytes((directory / "plan.json").read_bytes() + b"\n")
    budget = live_v2.FrozenBudget(directory, *live_v2.read_plan(directory))
    with pytest.raises(LLMConfigurationError):
        asyncio.run(call_provider(budget, handler))
    assert not sends and not budget.calls and budget.exhausted


@pytest.mark.parametrize("mode", ["timeout", "missing_usage"])
def test_unknown_or_missing_usage_stops_without_refund_or_retry(frozen, mode):
    directory, _ = frozen
    budget, sends = budget_for(directory), []

    def handler(request):
        sends.append(request)
        if mode == "timeout":
            raise httpx.ReadTimeout("synthetic timeout")
        return result(usage=False)

    expected_error = LLMTimeoutError if mode == "timeout" else LLMConfigurationError
    with pytest.raises(expected_error):
        asyncio.run(call_provider(budget, handler, count=2))
    assert len(sends) == len(budget.calls) == 1 and budget.exhausted
    reserved = budget.reserved
    assert reserved > 0
    assert budget.calls[0]["status"] == ("unknown" if mode == "timeout" else "returned")
    assert budget.calls[0]["usage"] is None
    with pytest.raises(LLMConfigurationError):
        asyncio.run(call_provider(budget, handler))
    assert budget.reserved == reserved and len(sends) == 1


def test_shared_budget_uses_frozen_tariff_for_reservation_and_observed_usage(tmp_path):
    plan = {
        "model": "synthetic-priced-model",
        "max_output_tokens": 100,
        "max_requests": 1,
        "max_reserved_tokens": 100000,
        "max_cost_cny": "20",
        "tariff": {"miss_per_million": "9.25", "output_per_million": "27.5"},
    }
    budget = BatchBudget(tmp_path, plan)
    payload = {"model": plan["model"], "max_tokens": 100, "messages": [{"content": "😀"}]}
    budget.reserve(payload)
    inputs = len(json.dumps(payload, ensure_ascii=False).encode()) + 4096
    assert budget.reserved == (inputs * Decimal("9.25") + 100 * Decimal("27.5")) / 1_000_000
    budget.finish(
        0,
        ChatResult(
            content="synthetic",
            model=plan["model"],
            usage=Usage(input_tokens=10, output_tokens=2, total_tokens=12),
        ),
        None,
        0.001,
    )
    assert (
        Decimal(budget.calls[0]["observed_peak_cost_upper_cny"])
        == (10 * Decimal("9.25") + 2 * Decimal("27.5")) / 1_000_000
    )


def test_run_batch_safety_route_tripwire_preserves_all_64_denominators(frozen, monkeypatch):
    directory, plan = frozen
    approve(directory)
    sends, keys = [], []

    def handler(request):
        sends.append(request)
        return result()

    def synthetic_key():
        keys.append("test-only")
        return SecretStr("synthetic-secret-never-real")

    async def fake_graph(case, provider, model, *, arm, before_call, **kwargs):
        # This stub tests orchestration, not ICA semantic/report quality. It emits
        # one real adapter MockTransport call and deliberately misses the risk route.
        assert kwargs == {"evidence_protocol": "quote-v2", "case_set": "v2"}
        schema = STAGE_SCHEMAS["safety"]
        await before_call("safety", None, messages(), schema)
        await provider.structured_output(messages(), schema, model=model, temperature=0)
        return {
            "case_id": case["case_id"],
            "arm": arm,
            "status": "completed",
            "result": {"outcome": "insufficient_evidence"},
            "calls": [],
        }

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            monkeypatch.setattr(
                live_v2,
                "RecordedProvider",
                lambda **kwargs: RecordedProvider(client=client, **kwargs),
            )
            await live_v2.run_batch(directory)

    monkeypatch.setattr(live_v2, "private_key", synthetic_key)
    monkeypatch.setattr(live_v2, "evaluate_case", fake_graph)
    asyncio.run(exercise())
    rows = [json.loads(line) for line in (directory / "results.jsonl").read_text().splitlines()]
    summary = json.loads((directory / "budget-summary.json").read_text())
    _, digest = live_v2.read_plan(directory)
    assert keys == ["test-only"]
    assert len(rows) == len(plan["execution_order"]) == 64
    assert [(r["case_id"], r["arm"]) for r in rows] == [
        (r["case_id"], r["arm"]) for r in plan["execution_order"]
    ]
    failed_route = [i for i, r in enumerate(rows) if r.get("safety_oracle_route_match") is False]
    assert failed_route == [44]  # The first safety_role follows22 ordinary cases/two arms.
    assert all(row["status"] == "not_run" and row["result"] is None for row in rows[45:])
    assert all(row["batch_plan_sha256"] == digest for row in rows)
    assert all(row["case_set"] == "v2" and row["evidence_protocol"] == "quote-v2" for row in rows)
    assert summary["stopped"] is True
    assert summary["external_provider_calls"] == len(sends) == 45
    assert summary["unknown_calls"] == 0 and summary["no_retries"] is True
    assert all(row["calls"] == [] for row in rows[45:])
