"""New case-set integration, no oracle leakage or reuse of disclosed v1 stories."""

import asyncio
import json

import pytest

from app.llm.mock import MockLLMProvider
from evals.ica.review import export_review
from evals.ica.runner import case_to_contexts, evaluate_case, load_cases


def test_v2_case_story_message_ids_and_complete_conversations_do_not_reuse_v1():
    old = [*load_cases("development"), *load_cases("holdout")]
    new = [*load_cases("development", case_set="v2"), *load_cases("holdout", case_set="v2")]
    for key in ("case_id", "story_id"):
        assert not {c[key] for c in old} & {c[key] for c in new}
    assert not {m["message_id"] for c in old for m in c["messages"]} & {
        m["message_id"] for c in new for m in c["messages"]
    }

    # Individual greetings may coincide; complete source conversations must not.
    def bodies(cases):
        return {tuple(m["content"] for m in c["messages"]) for c in cases}

    assert not bodies(old) & bodies(new)


def mock_finding(case):
    context = case_to_contexts(case)[0]
    first, second = context.messages[:2]
    assert {first.speaker, second.speaker} == {"self", "person"}
    item = {
        "kind": "emotional_mismatch",
        "facts": [
            {
                "statement": "双方分别表达了感受和安排。",
                "evidence": [
                    {
                        "evidence_id": f"w0-m{index:05d}",
                        "speaker": message.speaker,
                        "quote": message.content,
                    }
                    for index, message in enumerate((first, second), 1)
                ],
            }
        ],
        "hypothesis": "可能需要先确认对方希望怎样被回应。",
        "unknowns": ["不知道完整交流和线下情况。"],
        "alternative_explanations": ["安排也可能是表达关心的方式。"],
        "repair": {
            "action": "先询问对方希望被倾听还是讨论安排。",
            "observe": "观察对方愿不愿说明需要。",
            "stop_when": "对方不愿继续时暂停。",
        },
    }
    cid = context.chunks[0].id + ":0"
    provider = MockLLMProvider()
    provider.queue_structured({"decision": "normal", "risks": []})
    provider.queue_structured({"candidates": [item]})
    provider.queue_structured(
        {"checks": [{"candidate_id": cid, "decision": "no_evidence", "facts": []}]}
    )
    provider.queue_structured(
        {"findings": [{**item, "candidate_ids": [cid], "counterevidence": []}]}
    )
    provider.queue_structured(
        {
            "approved": True,
            "grounded": True,
            "respects_boundaries": True,
            "preserves_counterevidence": True,
            "reason_codes": [],
        }
    )
    return provider


@pytest.mark.parametrize("arm", ["event", "baseline"])
def test_v2_graph_emits_canonical_sources_and_readable_unscored_mock_review(tmp_path, arm):
    case = load_cases("development", case_set="v2")[0]
    messages = []

    async def before(stage, chunk_id, prompt, schema):
        messages.append(prompt)
        return str(len(messages))

    row = asyncio.run(
        evaluate_case(
            case,
            mock_finding(case),
            "mock",
            arm=arm,
            before_call=before,
            evidence_protocol="quote-v2",
            case_set="v2",
        )
    )
    row["batch_plan_sha256"] = "MOCK_DEMONSTRATION_ONLY"
    assert row["status"] == "completed", row
    assert row["result"]["outcome"] == "findings" and len(row["calls"]) == 5
    refs = row["result"]["findings"][0]["facts"][0]["evidence"]
    for ref, original in zip(refs, case_to_contexts(case)[0].messages, strict=False):
        assert original.content[ref["start"] : ref["end"]] == ref["quote"]
    for prompt in messages:
        payload = json.loads(prompt[1].content)
        assert not payload.keys() & {"expected", "family", "adversarial_input", "story_id"}
        assert "Never output start/end offsets" in prompt[0].content
    destination = export_review([row], [case], tmp_path / "mock-review", demonstration=True)
    text = (destination / "reviewer/reports.md").read_text(encoding="utf-8")
    assert "Mock" in text or "MOCK" in text
    assert "双方分别表达了感受和安排" in text
    packet = json.loads((destination / "reviewer/packet.json").read_text(encoding="utf-8"))
    assert len(packet["items"]) == 2  # Other arm remains not_run in the denominator.
    assert all(item["reviewer"] is None for item in packet["items"])


def test_v2_cannot_silently_use_legacy_spans():
    case = load_cases("development", case_set="v2")[0]
    row = asyncio.run(evaluate_case(case, MockLLMProvider(), "mock", case_set="v2"))
    assert row["error_code"] == "invalid_evidence_protocol" and row["calls"] == []
