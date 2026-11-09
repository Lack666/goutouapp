"""Exercise quote-only model outputs through the real ICA graph without a Provider API."""

import asyncio
import json
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from test_ica_runtime import REVIEW, candidate, context

from app.agent.imported_analysis import ImportedAnalysisError, ImportedAnalysisRuntime
from app.chat_import.analysis_scope import prepare_context
from app.llm.mock import MockLLMProvider


def quote_only(value):
    """Convert local legacy fixture data; production must reject mixed protocols."""
    if isinstance(value, dict):
        return {key: quote_only(item) for key, item in value.items() if key not in {"start", "end"}}
    if isinstance(value, list):
        return [quote_only(item) for item in value]
    return value


def contains_span(value):
    if isinstance(value, dict):
        return bool({"start", "end"} & value.keys()) or any(
            contains_span(item) for item in value.values()
        )
    if isinstance(value, list):
        return any(contains_span(item) for item in value)
    return False


class RecordedMock(MockLLMProvider):
    def __init__(self):
        super().__init__()
        self.requests = []

    async def structured_output(self, messages, schema, *, model=None, temperature=None):
        self.requests.append((messages, schema))
        return await super().structured_output(
            messages, schema, model=model, temperature=temperature
        )


class Trace:
    def __init__(self, *, fail_after=None):
        self.before_calls = []
        self.after_calls = []
        self.fail_after = fail_after

    async def before(self, stage, chunk_id, messages, schema):
        self.before_calls.append((stage, chunk_id, messages, schema))
        return str(len(self.before_calls))

    async def after(self, call_id, output, error):
        self.after_calls.append((call_id, output, error))
        if self.fail_after == len(self.after_calls):
            raise ImportedAnalysisError("source_changed")

    def run(self, contexts, provider):
        return asyncio.run(
            ImportedAnalysisRuntime(provider).run(
                contexts, "匿名合成关系复盘", "mock", self.before, self.after
            )
        )


def queue_findings(
    ctx,
    *,
    item=None,
    counter_facts=(),
    counter_decision="no_evidence",
    finding=None,
    review=None,
    checks=None,
):
    provider = RecordedMock()
    item = deepcopy(item) if item is not None else quote_only(candidate(ctx))
    key = ctx.chunks[0].id + ":0"
    for _ in ctx.chunks:
        provider.queue_structured({"decision": "normal", "risks": []})
    for index, _ in enumerate(ctx.chunks):
        provider.queue_structured({"candidates": [item] if index == 0 else []})
    for _ in ctx.chunks:
        provider.queue_structured(
            {
                "checks": checks
                if checks is not None
                else [
                    {
                        "candidate_id": key,
                        "decision": counter_decision,
                        "facts": list(counter_facts),
                    }
                ]
            }
        )
    provider.queue_structured(
        {
            "findings": [
                finding
                if finding is not None
                else {**item, "candidate_ids": [key], "counterevidence": list(counter_facts)}
            ]
        }
    )
    provider.queue_structured(review if review is not None else REVIEW)
    return provider


def assert_rejected(contexts, provider, stage, code):
    trace = Trace()
    with pytest.raises(ImportedAnalysisError) as error:
        trace.run(contexts, provider)
    assert error.value.code == code
    assert trace.before_calls[-1][0] == stage
    assert trace.after_calls[-1] == (str(len(trace.before_calls)), None, code)
    assert len(trace.after_calls) == len(trace.before_calls) == len(provider.requests)
    assert all(output is None for _, output, error in trace.after_calls if error)
    return trace


def test_default_quote_protocol_five_stages_publish_canonical_unicode_and_counterfacts():
    original = context(4)
    texts = (
        "👩‍💻前缀：我很难过😀。",
        "🙂前缀：你应该早点安排。",
        "其实我知道你是关心我。",
        "我先听你说，刚才急着给建议了。",
    )
    ctx = prepare_context(
        original.scope,
        [
            replace(message, content=text)
            for message, text in zip(original.messages, texts, strict=True)
        ],
    )
    item = quote_only(candidate(ctx))
    item["facts"][0]["evidence"][0]["quote"] = "我很难过😀"
    item["facts"][0]["evidence"][1]["quote"] = "你应该早点安排"
    counter = {
        "statement": "用户随后表示愿意先倾听。",
        "evidence": [{"evidence_id": "w0-m00004", "speaker": "self", "quote": "我先听你说"}],
    }
    provider = queue_findings(ctx, item=item, counter_facts=[counter], counter_decision="repair")
    trace = Trace()
    result = trace.run((ctx,), provider)

    stages = ["safety", "interaction", "counterevidence", "synthesis", "content_review"]
    assert [entry[0] for entry in trace.before_calls] == stages
    assert [receipt.stage for receipt in result.receipts] == stages
    assert all(receipt.status == "completed" for receipt in result.receipts)
    assert result.provider_calls == 5 and result.report.outcome == "findings"
    refs = result.report.findings[0].facts[0].evidence
    assert [(ref.start, ref.end, ref.quote) for ref in refs] == [
        (6, 11, "我很难过😀"),
        (4, 11, "你应该早点安排"),
    ]
    counter_ref = result.report.findings[0].counterevidence[0].evidence[0]
    assert (counter_ref.start, counter_ref.end, counter_ref.quote) == (0, 5, "我先听你说")
    assert {source.message_id for source in result.report.sources} == {
        ctx.messages[index].id for index in (0, 1, 3)
    }
    assert all(output is not None and error is None for _, output, error in trace.after_calls)

    for before, (messages, schema) in zip(trace.before_calls, provider.requests, strict=True):
        assert messages == before[2] and schema is before[3]
        assert not contains_span(schema.model_json_schema())
        payload = json.loads(messages[1].content)
        if before[0] in {"counterevidence", "synthesis"}:
            assert not contains_span(payload["candidates"])
        if before[0] == "synthesis":
            assert not contains_span(payload["counterevidence"])
        if before[0] == "content_review":
            assert not contains_span(payload["report"])
            assert payload["report"]["findings"][0]["facts"][0]["evidence"] == [
                {"evidence_id": "w0-m00001", "speaker": "person", "quote": "我很难过😀"},
                {"evidence_id": "w0-m00002", "speaker": "self", "quote": "你应该早点安排"},
            ]


@pytest.mark.parametrize(
    "change,code",
    [
        ({"evidence_id": "w0-m99999"}, "invalid_evidence"),
        ({"speaker": "self"}, "invalid_attribution"),
        ({"quote": "从未出现的原话"}, "invalid_evidence"),
        ({"start": 0, "end": 5}, "invalid_model_output"),
    ],
    ids=["unknown-alias", "wrong-speaker", "missing-quote", "mixed-numeric-spans"],
)
def test_quote_protocol_rejects_invalid_reference_before_success_callback(change, code):
    ctx = context()
    item = quote_only(candidate(ctx))
    item["facts"][0]["evidence"][0].update(change)
    assert_rejected((ctx,), queue_findings(ctx, item=item), "interaction", code)


@pytest.mark.parametrize(
    "content,quote",
    [("同一句，同一句", "同一句"), ("aaa", "aa"), ("e\u0301", "é")],
    ids=["multiple-occurrences", "overlapping-occurrences", "no-unicode-normalization"],
)
def test_quote_protocol_rejects_ambiguous_or_nonexact_source(content, quote):
    original = context()
    ctx = prepare_context(
        original.scope,
        [replace(original.messages[0], content=content), original.messages[1]],
    )
    item = quote_only(candidate(ctx))
    item["facts"][0]["evidence"][0]["quote"] = quote
    assert_rejected((ctx,), queue_findings(ctx, item=item), "interaction", "invalid_evidence")


def test_identical_bodies_keep_distinct_aliases_and_canonical_uuids():
    original = context(4)
    ctx = prepare_context(
        original.scope,
        [replace(message, content="同一正文😀") for message in original.messages],
    )
    result = Trace().run((ctx,), queue_findings(ctx))
    refs = result.report.findings[0].facts[0].evidence
    assert [ref.evidence_id for ref in refs] == ["w0-m00001", "w0-m00002"]
    assert [(ref.start, ref.end) for ref in refs] == [(0, 5), (0, 5)]
    assert len({source.message_id for source in result.report.sources}) == 2
    assert result.report.coverage[0].message_count == result.report.coverage[0].core_count == 4


def test_quote_reference_cannot_escape_current_chunk_and_halo():
    ctx = context(401)
    assert ctx.messages[-1].id not in (
        ctx.chunks[0].core + ctx.chunks[0].halo_before + ctx.chunks[0].halo_after
    )
    item = quote_only(candidate(ctx))
    item["facts"][0]["evidence"][0]["evidence_id"] = "w0-m00401"
    assert_rejected((ctx,), queue_findings(ctx, item=item), "interaction", "invalid_evidence")


def test_quote_reference_can_use_halo_without_counting_it_as_duplicate_core_coverage():
    ctx = context(401)
    message = ctx.messages[201]
    assert message.id in ctx.chunks[0].halo_after
    item = quote_only(candidate(ctx))
    item["facts"][0]["evidence"][1].update(
        evidence_id="w0-m00202", speaker=message.speaker, quote=message.content
    )
    result = Trace().run((ctx,), queue_findings(ctx, item=item))
    assert result.report.outcome == "findings"
    assert result.provider_calls == 3 * len(ctx.chunks) + 2
    assert result.report.coverage[0].core_count == result.report.coverage[0].message_count == 401
    assert {source.message_id for source in result.report.sources} == {
        ctx.messages[0].id,
        message.id,
    }


def test_quote_reference_cannot_borrow_known_alias_from_other_window():
    first = context()
    second_start = first.scope.end + timedelta(days=1)
    second_scope = replace(first.scope, start=second_start, end=second_start + timedelta(days=3))
    second = prepare_context(
        second_scope,
        [
            replace(message, id=uuid4(), timestamp=second_start + timedelta(seconds=index))
            for index, message in enumerate(first.messages)
        ],
    )
    item = quote_only(candidate(first))
    item["facts"][0]["evidence"][0]["evidence_id"] = "w1-m00003"
    provider = RecordedMock()
    for _ in (first, second):
        provider.queue_structured({"decision": "normal", "risks": []})
    provider.queue_structured({"candidates": [item]})
    assert_rejected((first, second), provider, "interaction", "invalid_evidence")


def test_quote_protocol_still_rejects_halo_only_candidate():
    ctx = context(401)
    halo = ctx.chunks[0].halo_after[:2]
    assert len(halo) == 2
    aliases = {message.id: f"w0-m{index + 1:05d}" for index, message in enumerate(ctx.messages)}
    messages = {message.id: message for message in ctx.messages}
    item = quote_only(candidate(ctx))
    item["facts"][0]["evidence"] = [
        {
            "evidence_id": aliases[message_id],
            "speaker": messages[message_id].speaker,
            "quote": messages[message_id].content,
        }
        for message_id in halo
    ]
    assert_rejected((ctx,), queue_findings(ctx, item=item), "interaction", "halo_only_candidate")


def test_after_callback_failure_stops_graph_before_a_successful_result():
    ctx = context()
    provider = queue_findings(ctx)
    trace = Trace(fail_after=1)
    with pytest.raises(ImportedAnalysisError) as error:
        trace.run((ctx,), provider)
    assert error.value.code == "source_changed"
    assert [entry[0] for entry in trace.before_calls] == ["safety"]
    assert len(provider.requests) == len(trace.after_calls) == 1


@pytest.mark.parametrize(
    "fault,stage,code",
    [
        ("missing-check", "counterevidence", "incomplete_counterevidence"),
        ("refuted", "synthesis", "refuted_finding"),
        ("omitted-counterfact", "synthesis", "counterevidence_omitted"),
        ("review", "content_review", "content_review_rejected"),
    ],
)
def test_quote_protocol_preserves_counterevidence_and_independent_review_rejection(
    fault, stage, code
):
    ctx = context()
    options = {}
    if fault == "missing-check":
        options["checks"] = []
    elif fault in {"refuted", "omitted-counterfact"}:
        counter = {
            "statement": "对方明确表达难过。",
            "evidence": [quote_only(candidate(ctx))["facts"][0]["evidence"][0]],
        }
        options.update(
            counter_facts=[counter],
            counter_decision="refutes" if fault == "refuted" else "qualifies",
        )
        if fault == "omitted-counterfact":
            options["finding"] = {
                **quote_only(candidate(ctx)),
                "candidate_ids": [ctx.chunks[0].id + ":0"],
                "counterevidence": [],
            }
    else:
        options["review"] = {**REVIEW, "approved": False, "reason_codes": ["unsupported"]}
    assert_rejected((ctx,), queue_findings(ctx, **options), stage, code)
