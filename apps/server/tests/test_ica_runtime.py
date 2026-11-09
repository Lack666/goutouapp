"""Validate real ICA graph barriers and evidence rejection with keyless queued outputs."""

import asyncio
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.agent.imported_analysis import ImportedAnalysisError, ImportedAnalysisRuntime
from app.chat_import.analysis_scope import AnalysisScope, ScopeMessage, prepare_context
from app.llm.mock import MockLLMProvider

REVIEW = dict(
    approved=True,
    grounded=True,
    respects_boundaries=True,
    preserves_counterevidence=True,
    reason_codes=[],
)


def context(count=2):
    owner, person, dataset = uuid4(), uuid4(), uuid4()
    start = datetime(2026, 1, 1, tzinfo=UTC)
    scope = AnalysisScope(owner, person, dataset, "Asia/Shanghai", start, start + timedelta(days=3))
    messages = [
        ScopeMessage(
            uuid4(),
            owner,
            person,
            dataset,
            start + timedelta(seconds=i),
            "person" if i % 2 == 0 else "self",
            "我很难过😀" if i % 2 == 0 else "你应该早点安排",
        )
        for i in range(count)
    ]
    return prepare_context(scope, messages)


def candidate(ctx):
    return {
        "kind": "emotional_mismatch",
        "facts": [
            {
                "statement": "对方表达难过后，用户给出安排建议。",
                "evidence": [
                    {
                        "evidence_id": "w0-m00001",
                        "speaker": "person",
                        "start": 0,
                        "end": 5,
                        "quote": ctx.messages[0].content,
                    },
                    {
                        "evidence_id": "w0-m00002",
                        "speaker": "self",
                        "start": 0,
                        "end": 7,
                        "quote": ctx.messages[1].content,
                    },
                ],
            }
        ],
        "hypothesis": "可能先需要被倾听，回应方式尚未对上。",
        "unknowns": ["不知道之后是否有线下安慰。"],
        "alternative_explanations": ["用户可能通过解决问题表达关心。"],
        "repair": {
            "action": "询问对方更需要倾听还是建议。",
            "observe": "看对方是否愿意说明需求。",
            "stop_when": "对方不愿继续时暂停。",
        },
    }


def finding_provider(
    ctx,
    *,
    counter_decision="no_evidence",
    counter_facts=(),
    finding=None,
    review=None,
    checks_override=None,
    quote_only=False,
):
    provider = MockLLMProvider()
    if quote_only:
        from app.agent.imported_quote import quote_payload

        original_queue = provider.queue_structured
        provider.queue_structured = lambda value: original_queue(quote_payload(value))
    item = candidate(ctx)
    key = ctx.chunks[0].id + ":0"
    for _ in ctx.chunks:
        provider.queue_structured({"decision": "normal", "risks": []})
    for index, _ in enumerate(ctx.chunks):
        provider.queue_structured({"candidates": [item] if index == 0 else []})
    for _ in ctx.chunks:
        provider.queue_structured(
            {
                "checks": checks_override
                if checks_override is not None
                else [
                    {
                        "candidate_id": key,
                        "decision": counter_decision,
                        "facts": list(counter_facts),
                    }
                ]
            }
        )
    proposal = (
        finding
        if finding is not None
        else {
            **item,
            "candidate_ids": [key],
            "counterevidence": list(counter_facts),
        }
    )
    provider.queue_structured({"findings": [proposal]})
    provider.queue_structured(review or REVIEW)
    return provider


def run(ctx, provider, contexts=None):
    events = []

    async def before(stage, chunk_id, messages, schema):
        events.append((stage, chunk_id, messages))
        return str(len(events))

    async def after(call_id, output, error):
        pass

    result = asyncio.run(
        ImportedAnalysisRuntime(provider, evidence_protocol="span-v1").run(
            contexts or (ctx,), "匿名合成复盘", "mock", before, after
        )
    )
    return result, events


def test_real_graph_findings_and_unicode_lineage():
    ctx = context()
    result, events = run(ctx, finding_provider(ctx))
    assert result.report.outcome == "findings"
    assert result.provider_calls == 5
    assert [e[0] for e in events] == [
        "safety",
        "interaction",
        "counterevidence",
        "synthesis",
        "content_review",
    ]
    assert {s.message_id for s in result.report.sources} == {m.id for m in ctx.messages}
    assert result.report.findings[0].facts[0].evidence[0].quote.endswith("😀")
    assert all(e[2][0].role == "system" and e[2][1].role == "user" for e in events)


def test_all_core_safety_barrier_and_full_counter_round():
    ctx = context(210)
    result, events = run(ctx, finding_provider(ctx))
    k = len(ctx.chunks)
    assert [e[0] for e in events[:k]] == ["safety"] * k
    assert result.provider_calls == 3 * k + 2
    assert len([r for r in result.receipts if r.stage == "counterevidence"]) == k


def test_safety_exit_never_runs_ordinary_nodes():
    ctx = context(210)
    provider = MockLLMProvider()
    provider.queue_structured(
        {
            "decision": "uncertain",
            "risks": [
                {
                    "actor": "unknown",
                    "user_role": "unclear",
                    "temporality": "unknown",
                    "category": "uncertain",
                    "source": "question",
                    "evidence": [],
                }
            ],
        }
    )
    for _ in ctx.chunks[1:]:
        provider.queue_structured({"decision": "normal", "risks": []})
    provider.queue_structured(REVIEW)
    result, events = run(ctx, provider)
    assert result.report.outcome == "safety_blocked" and result.report.findings == []
    assert [e[0] for e in events] == ["safety"] * len(ctx.chunks) + ["content_review"]
    assert all(r.stage not in {"interaction", "counterevidence"} for r in result.receipts)


@pytest.mark.parametrize(
    "change,code",
    [
        ("alias", "invalid_evidence"),
        ("span", "invalid_evidence"),
        ("speaker", "invalid_attribution"),
        ("review", "content_review_rejected"),
        ("counter_missing", "incomplete_counterevidence"),
        ("refuted", "refuted_finding"),
        ("facts", "unverified_fact"),
        ("one_sided", "one_sided_finding"),
        ("temporal", "incomparable_windows"),
        ("recurring", "insufficient_episodes"),
        ("counter_omitted", "counterevidence_omitted"),
    ],
)
def test_untrusted_outputs_fail_closed(change, code):
    ctx = context()
    proposal = {**candidate(ctx), "candidate_ids": [ctx.chunks[0].id + ":0"], "counterevidence": []}
    kwargs = {}
    if change == "review":
        kwargs["review"] = {**REVIEW, "approved": False, "reason_codes": ["unsupported"]}
    elif change == "counter_missing":
        kwargs["checks_override"] = []
    elif change == "refuted":
        kwargs.update(counter_decision="refutes", counter_facts=proposal["facts"])
        proposal["counterevidence"] = deepcopy(proposal["facts"])
    elif change == "counter_omitted":
        kwargs.update(counter_decision="repair", counter_facts=proposal["facts"])
    elif change == "facts":
        proposal["facts"] = deepcopy(proposal["facts"])
        proposal["facts"][0]["statement"] = "没有验证的新增事实。"
    elif change == "one_sided":
        proposal["facts"] = deepcopy(proposal["facts"])
        proposal["facts"][0]["evidence"] = proposal["facts"][0]["evidence"][:1]
        # To reach the sidedness validator this is itself a validated candidate.
        provider = finding_provider(ctx)
        provider._structured[1] = {"candidates": [proposal | {}]}
        provider._structured[1]["candidates"][0].pop("candidate_ids")
        provider._structured[1]["candidates"][0].pop("counterevidence")
        provider._structured[3] = {"findings": [proposal]}
        with pytest.raises(ImportedAnalysisError, match=code):
            run(ctx, provider)
        return
    elif change in {"temporal", "recurring"}:
        kind = "temporal_change" if change == "temporal" else "recurring_conflict"
        proposal["kind"] = kind
        provider = finding_provider(ctx)
        provider._structured[1]["candidates"][0]["kind"] = kind
        provider._structured[3] = {"findings": [proposal]}
        with pytest.raises(ImportedAnalysisError, match=code):
            run(ctx, provider)
        return
    else:
        provider = finding_provider(ctx)
        ref = provider._structured[1]["candidates"][0]["facts"][0]["evidence"][0]
        if change == "alias":
            ref["evidence_id"] = "w0-m99999"
        if change == "span":
            ref["end"] += 1
        if change == "speaker":
            ref["speaker"] = "self"
        with pytest.raises(ImportedAnalysisError, match=code):
            run(ctx, provider)
        return
    with pytest.raises(ImportedAnalysisError, match=code):
        run(ctx, finding_provider(ctx, finding=proposal, **kwargs))


def test_mixed_resource_context_and_forged_manifest_rejected_before_provider():
    ctx = context()
    for contexts in [(ctx, context()), (replace(ctx, snapshot_digest="forged"),)]:
        with pytest.raises(ImportedAnalysisError, match="invalid_context"):
            run(ctx, MockLLMProvider(), contexts)
