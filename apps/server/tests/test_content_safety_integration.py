"""Frozen full-graph integration; live reviewer accuracy is recorded separately."""

import asyncio
import json

import httpx
import pytest
from pydantic import SecretStr

from app.agent.contracts import ActionPlan, ResponseResult
from app.llm.errors import LLMTimeoutError
from app.llm.eval_budget import EvalBudget
from app.llm.mock import MockLLMProvider
from evals.agent.content_safety_eval import ROOT, oracle_review
from evals.agent.content_safety_integration import DATASET, fixtures, run_case
from evals.agent.harness import SyntheticEvalProvider

CASES = json.loads(DATASET.read_text("utf-8"))["cases"]
PREFIX = [
    "normalize_input",
    "load_memory",
    "safety_check",
    "classify_scenario",
    "extract_fiu",
    "knowledge_router",
    "load_references",
    "relationship_analysis",
    "action_planner",
]


def queue_allow(reviewer, outputs, *, response=True):
    reviewer.queue_chat(oracle_review(ActionPlan.model_validate(outputs["ActionPlan"])))
    if response:
        reviewer.queue_chat(oracle_review(ResponseResult.model_validate(outputs["ResponseResult"])))


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_full_graph_really_hits_cues_reviews_then_completes_or_rejects(case):
    outputs = fixtures(case)
    reviewer = MockLLMProvider()
    if case["expected"] == "allow":
        queue_allow(reviewer, outputs)
    else:
        reviewer.queue_chat(
            oracle_review(
                ActionPlan.model_validate(outputs["ActionPlan"]),
                field="recommended_action",
                intent="harmful_action",
                violations=["stalking", "coercion"],
            )
        )
    row = asyncio.run(run_case(case, reviewer))
    assert row["passed"] and not reviewer._chats
    trace = row["traces"]
    assert all(t["run_id"] == row["run_id"] for t in trace)
    assert [t["status"] for t in trace if t["kind"] == "outcome"] == [row["result"]["status"]]
    if case["expected"] == "allow":
        assert row["nodes"] == PREFIX + [
            "response_generator",
            "memory_intent_resolver",
            "memory_candidate_extractor",
            "memory_persist",
        ]
        assert row["provider_counts"] == {
            "frozen_structured": 6,
            "review_calls": 2,
            "observed_real_http_calls": 0,
        }
        events = [(t["kind"], t["node"]) for t in trace]
        assert (
            events.index(("fixture_provider", "action_planner"))
            < events.index(("content_safety_review", "action_planner"))
            < events.index(("fixture_provider", "response_generator"))
            < events.index(("content_safety_review", "response_generator"))
        )
    else:
        assert row["nodes"] == PREFIX
        assert row["provider_counts"]["frozen_structured"] == 5
        assert row["provider_counts"]["review_calls"] == 1
        assert row["diagnosis"] == "safety_rejection"
    assert row["memory"]["read_count"] >= 1 and row["memory"]["write_attempts"] == 0


@pytest.mark.parametrize("stage", ["action", "response"])
@pytest.mark.parametrize("consented", [False, True])
@pytest.mark.parametrize("fault", ["timeout", "invalid_decision", "truncated"])
def test_review_faults_fail_closed_without_memory_changes_or_published_answer(
    stage, consented, fault
):
    case = CASES[0] | {"expected": "review_fault"}
    reviewer = MockLLMProvider()
    if stage == "response":
        queue_allow(reviewer, fixtures(case), response=False)
    if fault == "timeout":
        reviewer.queue_error("chat", LLMTimeoutError())
    else:
        reviewer.queue_chat("{}", finish_reason="length" if fault == "truncated" else "stop")
    row = asyncio.run(run_case(case, reviewer, consented=consented, stream=True))
    assert row["passed"] and row["diagnosis"] == "review_fault"
    assert row["stream_event_types"][-1] == "failed"
    assert not {"final_response", "completed", "memory_status"} & set(row["stream_event_types"])
    assert row["memory"]["unchanged"] and row["memory"]["write_attempts"] == 0
    assert not reviewer._chats


def test_formal_schema_failure_has_separate_diagnosis_and_never_calls_reviewer():
    case = CASES[0] | {"expected": "schema_error"}
    outputs = fixtures(case)
    outputs["ActionPlan"] = {"recommended_action": "不编造借口。"}
    reviewer = MockLLMProvider()
    reviewer.queue_chat('{"fields": []}')
    row = asyncio.run(run_case(case, reviewer, outputs=outputs))
    assert row["passed"] and row["diagnosis"] == "schema_error"
    assert row["provider_counts"]["review_calls"] == 0 and len(reviewer._chats) == 1
    assert row["result"]["code"] == "structured_output_failure"


def test_forged_allow_cannot_override_existing_formal_action_guard():
    case = CASES[1] | {"expected": "formal_guard_rejection"}
    outputs = fixtures(case)
    outputs["ActionPlan"]["supporting_analysis_ids"] = ["A999"]
    reviewer = MockLLMProvider()
    queue_allow(reviewer, outputs, response=False)
    row = asyncio.run(run_case(case, reviewer, outputs=outputs))
    assert row["passed"] and row["diagnosis"] == "formal_guard_rejection"
    assert row["provider_counts"]["review_calls"] == 0 and len(reviewer._chats) == 1


def test_input_high_risk_still_skips_all_review_and_ordinary_nodes():
    case = CASES[0]
    outputs = fixtures(case)
    outputs["SafetyResult"] = {
        "risk_level": "high",
        "safety_route_required": True,
        "risk_categories": ["coercion"],
    }
    reviewer = MockLLMProvider()
    queue_allow(reviewer, outputs)
    row = asyncio.run(run_case(case, reviewer, outputs=outputs))
    assert row["result"]["route"] == "safety"
    assert row["nodes"] == [
        "normalize_input",
        "load_memory",
        "safety_check",
        "knowledge_router",
        "load_references",
        "safety_finalize",
    ]
    assert row["provider_counts"]["review_calls"] == 0 and len(reviewer._chats) == 2
    assert row["memory"]["unchanged"]


def test_real_adapter_fake_http_accounts_for_only_three_review_calls():
    replies = []
    for case in CASES:
        outputs = fixtures(case)
        plan = ActionPlan.model_validate(outputs["ActionPlan"])
        if case["expected"] == "allow":
            replies.extend(
                [
                    oracle_review(plan),
                    oracle_review(ResponseResult.model_validate(outputs["ResponseResult"])),
                ]
            )
        else:
            replies.append(
                oracle_review(
                    plan,
                    field="recommended_action",
                    intent="harmful_action",
                    violations=["stalking"],
                )
            )

    def respond(request):
        payload = json.loads(request.content)
        assert "Return only a structured ActionPlan" not in payload["messages"][0]["content"]
        return httpx.Response(
            200,
            json={
                "model": "deepseek-flash",
                "choices": [{"message": {"content": replies.pop(0)}, "finish_reason": "stop"}],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 10,
                    "total_tokens": 110,
                    "prompt_cache_hit_tokens": 0,
                    "prompt_cache_miss_tokens": 100,
                },
            },
        )

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            budget = EvalBudget(max_requests=3, max_cost_cny=0.25)
            provider = SyntheticEvalProvider(
                base_url="https://synthetic.invalid",
                api_key=SecretStr("synthetic"),
                model="deepseek-flash",
                client=client,
                budget=budget,
                max_output_tokens=2048,
            )
            rows = [await run_case(case, provider) for case in CASES]
            assert all(row["passed"] for row in rows)
            assert budget.requests == 3 and not replies
            assert sum(r["provider_counts"]["observed_real_http_calls"] for r in rows) == 3
            assert len(provider.synthetic_outputs) == 3

    asyncio.run(execute())


@pytest.mark.parametrize("index", [0, 1])
def test_real_review_decisions_replay_through_whole_graph_without_new_api_calls(index):
    evidence = json.loads(
        (ROOT / "evals/agent/results/content-safety-integration-live-v1.json").read_text("utf-8")
    )
    reviewer = MockLLMProvider()
    outputs = evidence["synthetic_visible_review_outputs"]
    for output in outputs[:2] if index == 0 else outputs[2:]:
        reviewer.queue_chat(output["content"], finish_reason=output["finish_reason"])
    row = asyncio.run(run_case(CASES[index], reviewer))
    assert row["passed"] and not reviewer._chats
    assert row["diagnosis"] == evidence["cases"][index]["diagnosis"]
    assert row["nodes"] == evidence["cases"][index]["nodes"]


def test_live_evidence_has_exact_counts_same_run_identity_and_ordered_terminal_state():
    evidence = json.loads(
        (ROOT / "evals/agent/results/content-safety-integration-live-v1.json").read_text("utf-8")
    )
    assert evidence["passed"] and evidence["source_stable"]
    assert evidence["accounting"]["requests"] == evidence["accounting"]["responses"] == 3
    assert evidence["accounting"]["unknown_cost_calls"] == 0
    assert len(evidence["synthetic_visible_review_outputs"]) == 3
    for row in evidence["cases"]:
        trace = row["traces"]
        assert all(t["run_id"] == row["run_id"] for t in trace)
        assert row["result"]["run_id"] == row["run_id"]
        assert row["memory"]["write_attempts"] == 0 and row["memory"]["unchanged"]
        assert [t["status"] for t in trace if t["kind"] == "outcome"] == [row["result"]["status"]]
        assert (
            row["provider_counts"]["observed_real_http_calls"]
            == row["provider_counts"]["review_calls"]
        )
