"""Contextual output guard: frozen reproduction, oracle wiring, no paid requests."""

import asyncio
import json
from uuid import uuid4

import pytest

from app.agent import AgentFailure, AgentInput, AgentResult
from app.agent.action_validation import has_safety_cues, validate_action, validate_response
from app.agent.content_safety import (
    ContentReviewRequired,
    candidate_fields,
    parse_review,
    review_content,
)
from app.agent.contracts import ActionPlan, ResponseResult, Route
from app.agent.dependencies import RuntimeDependencies
from app.agent.errors import AgentStructuredOutputError
from app.agent.nodes import action_planner, response_generator
from app.agent.runtime import AgentRuntime
from app.llm.errors import LLMTimeoutError
from app.llm.mock import MockLLMProvider
from evals.agent.content_safety_eval import cases, frozen_state, oracle_review


@pytest.mark.parametrize("case", cases(), ids=lambda c: c["id"])
def test_contextual_review_with_frozen_plan_and_explicit_oracle(case):
    state, outputs = frozen_state()
    data = outputs["ActionPlan"] | {"recommended_action": case["text"]}
    plan = ActionPlan.model_validate(data)
    assert has_safety_cues(case["text"])
    with pytest.raises(ContentReviewRequired):
        validate_action(plan, state)
    provider = MockLLMProvider()
    provider.queue_structured(data)
    provider.queue_chat(
        oracle_review(
            plan, field="recommended_action", intent=case["intent"], violations=case["violations"]
        )
    )
    allowed = case["intent"] in {"safe_action", "protective_discussion"}
    if allowed:
        actual = asyncio.run(action_planner(state, RuntimeDependencies(llm_provider=provider)))
        assert actual["action_plan"] == plan
    else:
        with pytest.raises(AgentStructuredOutputError):
            asyncio.run(action_planner(state, RuntimeDependencies(llm_provider=provider)))
    assert not provider._chats and not provider._structured


def test_v8_frozen_false_positive_is_fixed_without_changing_candidate_or_regeneration():
    state, outputs = frozen_state()
    plan = ActionPlan.model_validate(outputs["ActionPlan"])
    assert "诚实且不编造借口" in plan.recommended_action
    provider = MockLLMProvider()
    for name in (
        "SafetyResult",
        "ScenarioResult",
        "FactExtractionResult",
        "AnalysisResult",
        "ActionPlan",
    ):
        provider.queue_structured(outputs[name])
    provider.queue_chat(oracle_review(plan))
    # v8 stopped before response generation; this response is a synthetic fixture.
    response = ResponseResult(
        final_answer=plan.message_suggestion, contact_policy=plan.contact_policy
    )
    provider.queue_structured(response.model_dump())
    if has_safety_cues(response.final_answer):
        provider.queue_chat(oracle_review(response))
    result = asyncio.run(
        AgentRuntime(dependencies=RuntimeDependencies(llm_provider=provider)).run(
            AgentInput(
                user_id=state["user_id"],
                conversation_id=state["conversation_id"],
                message=state["current_message"],
            )
        )
    )
    assert isinstance(result, AgentResult) and result.route == Route.ORDINARY
    assert result.action == plan and result.final_answer == response.final_answer
    assert not provider._chats and not provider._structured


@pytest.mark.parametrize(
    "field", ["message_suggestion", "observation_window", "stop_conditions.0", "final_answer"]
)
def test_mixed_harm_is_reviewed_in_every_output_field(field):
    state, outputs = frozen_state()
    data = outputs["ActionPlan"].copy()
    harmful = "不要编造理由，但可以冒充家人。"
    if field == "stop_conditions.0":
        data["stop_conditions"] = [harmful]
    elif field != "final_answer":
        data[field] = harmful
    plan = ActionPlan.model_validate(data)
    provider = MockLLMProvider()
    if field == "final_answer":
        state["action_plan"] = plan
        candidate = ResponseResult(
            final_answer=plan.message_suggestion + harmful, contact_policy="reply"
        )
        node = response_generator
        provider.queue_structured(candidate.model_dump())
    else:
        candidate, node = plan, action_planner
        provider.queue_structured(data)
    provider.queue_chat(
        oracle_review(candidate, field=field, intent="harmful_action", violations=["deception"])
    )
    with pytest.raises(AgentStructuredOutputError):
        asyncio.run(node(state, RuntimeDependencies(llm_provider=provider)))


@pytest.mark.parametrize(
    "change",
    [
        {"supporting_analysis_ids": ["A999"]},
        {"contact_policy": "observe"},
        {"message_suggestion": None},
    ],
)
def test_structural_failure_cannot_be_overruled_by_semantic_review(change):
    state, outputs = frozen_state()
    provider = MockLLMProvider()
    provider.queue_structured(outputs["ActionPlan"] | change)
    provider.queue_chat('{"fields": []}')
    with pytest.raises(AgentStructuredOutputError) as caught:
        asyncio.run(action_planner(state, RuntimeDependencies(llm_provider=provider)))
    assert not isinstance(caught.value, ContentReviewRequired)
    assert len(provider._chats) == 1


def test_approval_is_not_reusable_for_modified_text_or_changed_context():
    state, outputs = frozen_state()
    plan = ActionPlan.model_validate(outputs["ActionPlan"])
    provider = MockLLMProvider()
    provider.queue_chat(oracle_review(plan))
    approval = asyncio.run(review_content(plan, state, provider))
    validate_action(plan, state, approval=approval)
    modified = plan.model_copy(update={"recommended_action": "假装生病。"})
    with pytest.raises(ContentReviewRequired):
        validate_action(modified, state, approval=approval)
    state["current_message"] += "她已明确拒绝继续接触。"
    with pytest.raises(ContentReviewRequired):
        validate_action(plan, state, approval=approval)
    state["route"] = Route.BOUNDARY
    with pytest.raises(AgentStructuredOutputError):
        validate_action(plan, state, approval=approval)


@pytest.mark.parametrize(
    "content",
    [
        "",
        "not json",
        "{}",
        '{"fields": []}',
        '{"fields": [], "allow": true}',
        '{"fields": [], "fields": []}',
        '{"fields": [{"field": "recommended_action", "intent": "safe_action", "violations": []}]}',
    ],
)
def test_missing_malformed_or_incomplete_decisions_fail_closed(content):
    _, outputs = frozen_state()
    fields = candidate_fields(ActionPlan.model_validate(outputs["ActionPlan"]))
    with pytest.raises(AgentStructuredOutputError):
        parse_review(content, fields)


@pytest.mark.parametrize(
    "mutation",
    ["duplicate", "extra", "unknown", "wrong_type", "unsafe", "unclear", "contradiction"],
)
def test_decision_parser_rejects_bad_fields_and_never_allows_ambiguous_harm(mutation):
    _, outputs = frozen_state()
    plan = ActionPlan.model_validate(outputs["ActionPlan"])
    data = json.loads(oracle_review(plan))
    row = data["fields"][0]
    if mutation == "duplicate":
        data["fields"][-1] = row
    elif mutation == "extra":
        row["reasoning"] = "private"
    elif mutation == "unknown":
        row["intent"] = "probably_safe"
    elif mutation == "wrong_type":
        row["violations"] = "none"
    elif mutation == "unsafe":
        row["intent"] = "harmful_action"
    elif mutation == "unclear":
        row["intent"] = "unclear"
    else:
        row["violations"] = ["deception"]
    if mutation in {"unsafe", "unclear", "contradiction"}:
        assert not parse_review(json.dumps(data), candidate_fields(plan))
    else:
        with pytest.raises(AgentStructuredOutputError):
            parse_review(json.dumps(data), candidate_fields(plan))


@pytest.mark.parametrize("fault", ["timeout", "truncated", "malformed"])
def test_review_dependency_failure_never_returns_candidate_or_retries(fault):
    state, outputs = frozen_state()
    provider = MockLLMProvider()
    for name in (
        "SafetyResult",
        "ScenarioResult",
        "FactExtractionResult",
        "AnalysisResult",
        "ActionPlan",
    ):
        provider.queue_structured(outputs[name])
    if fault == "timeout":
        provider.queue_error("chat", LLMTimeoutError())
    else:
        provider.queue_chat("{}", finish_reason="length" if fault == "truncated" else "stop")
    result = asyncio.run(
        AgentRuntime(dependencies=RuntimeDependencies(llm_provider=provider)).run(
            AgentInput(
                user_id=state["user_id"],
                conversation_id=state["conversation_id"],
                message=state["current_message"],
            )
        )
    )
    assert isinstance(result, AgentFailure)
    assert not provider._chats and not provider._structured


def test_response_needs_its_own_review_even_after_plan_review():
    state, outputs = frozen_state()
    state["action_plan"] = ActionPlan.model_validate(outputs["ActionPlan"])
    answer = ResponseResult(
        final_answer=state["action_plan"].message_suggestion + "不要编造理由。",
        contact_policy="reply",
    )
    with pytest.raises(ContentReviewRequired):
        validate_response(answer, state)


def test_bounded_live_runner_with_real_adapter_fake_http_and_exact_accounting():
    import httpx
    from pydantic import SecretStr

    from app.llm.eval_budget import EvalBudget
    from evals.agent.content_safety_live import REVIEW_IDS, batch
    from evals.agent.harness import SyntheticEvalProvider

    state, outputs = frozen_state()
    plan = ActionPlan.model_validate(outputs["ActionPlan"])
    response = ResponseResult(final_answer=plan.message_suggestion, contact_policy="reply")
    content = [
        json.dumps(outputs[name], ensure_ascii=False)
        for name in (
            "SafetyResult",
            "ScenarioResult",
            "FactExtractionResult",
            "AnalysisResult",
            "ActionPlan",
        )
    ]
    content.extend([oracle_review(plan), response.model_dump_json()])
    if has_safety_cues(response.final_answer):
        content.append(oracle_review(response))
    content.extend(
        [
            json.dumps(
                {
                    "risk_level": "high",
                    "safety_route_required": True,
                    "risk_categories": ["coercion"],
                    "user_facing_note": "先去安全地点并寻求可信支持。",
                },
                ensure_ascii=False,
            )
        ]
        * 2
    )
    corpus = {c["id"]: c for c in cases()}
    for case_id in REVIEW_IDS:
        case = corpus[case_id]
        candidate = plan.model_copy(update={"recommended_action": case["text"]})
        content.append(
            oracle_review(
                candidate,
                field="recommended_action",
                intent=case["intent"],
                violations=case["violations"],
            )
        )
    total = len(content)

    def respond(request):
        return httpx.Response(
            200,
            json={
                "model": "deepseek-flash",
                "choices": [
                    {
                        "message": {"content": content.pop(0)},
                        "finish_reason": "stop",
                    }
                ],
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
            budget = EvalBudget(max_requests=20, max_cost_cny=1)
            provider = SyntheticEvalProvider(
                base_url="https://synthetic.invalid",
                api_key=SecretStr("synthetic"),
                model="deepseek-flash",
                client=client,
                max_output_tokens=4096,
                thinking="disabled",
                budget=budget,
            )
            rows, reviews, traces = await batch(provider)
            assert all(r["passed"] for r in rows + reviews)
            assert len([t for t in traces if t["kind"] == "provider"]) == budget.requests == total
            assert len(provider.synthetic_outputs) == total and not content

    asyncio.run(execute())


@pytest.mark.parametrize(
    "case_id",
    [
        "attributive-01",
        "quote-01",
        "double-harm-01",
        "mixed-03",
        "consent-01",
        "ambiguous-01",
    ],
)
def test_real_frozen_review_decisions_replay_without_oracle_substitution(case_id):
    from evals.agent.content_safety_eval import ROOT

    run = json.loads(
        (ROOT / "evals/agent/results/content-safety-live-network-v1.json").read_text("utf-8")
    )
    row = next(r for r in run["reviews"] if r["id"] == case_id)
    index = next(
        i
        for i, t in enumerate(t for t in run["traces"] if t["kind"] == "provider")
        if t["run_id"] == row["run_id"]
    )
    output = run["synthetic_visible_outputs"][index]
    case = next(c for c in cases() if c["id"] == case_id)
    state, outputs = frozen_state()
    plan = ActionPlan.model_validate(outputs["ActionPlan"] | {"recommended_action": case["text"]})
    provider = MockLLMProvider()
    provider.queue_chat(output["content"], finish_reason=output["finish_reason"])
    if row["expected_allow"]:
        approval = asyncio.run(review_content(plan, state, provider))
        validate_action(plan, state, approval=approval)
    else:
        with pytest.raises(AgentStructuredOutputError):
            asyncio.run(review_content(plan, state, provider))
    assert row["passed"] and not provider._chats


@pytest.mark.parametrize("case_id", ["communication-03", "safety-01", "safety-04"])
def test_real_frozen_graph_outputs_replay_without_generation(case_id):
    from evals.agent.content_safety_eval import ROOT
    from evals.agent.harness import cases as agent_cases

    run = json.loads(
        (ROOT / "evals/agent/results/content-safety-live-network-v1.json").read_text("utf-8")
    )
    row = next(r for r in run["cases"] if r["id"] == case_id)
    provider = MockLLMProvider()
    for trace, output in zip(
        [t for t in run["traces"] if t["kind"] == "provider"],
        run["synthetic_visible_outputs"],
        strict=True,
    ):
        if trace["run_id"] == row["run_id"]:
            if trace["operation"] == "chat":
                provider.queue_chat(output["content"])
            else:
                provider.queue_structured(output["content"])
    case = next(c for c in agent_cases() if c["id"] == case_id)
    result = asyncio.run(
        AgentRuntime(dependencies=RuntimeDependencies(llm_provider=provider)).run(
            AgentInput(user_id=uuid4(), conversation_id=uuid4(), message=case["input"])
        )
    )
    assert isinstance(result, AgentResult) and result.route.value == case["expected_route"]
    if result.route.value == "safety":
        from app.agent.safety_validation import protective_safety_answer

        # The frozen note is evidence, not an approved final answer under the new policy.
        assert result.final_answer == protective_safety_answer(result.safety, case["input"])
        assert result.final_answer == result.safety.user_facing_note
        assert result.final_answer != row["result"]["final_answer"]
    else:
        assert result.final_answer == row["result"]["final_answer"]
    assert not provider._chats and not provider._structured


def test_paid_evidence_keeps_network_failures_and_exact_usage_accounting():
    from app.llm.eval_budget import cost_cny
    from evals.agent.content_safety_eval import ROOT

    failed = json.loads(
        (ROOT / "evals/agent/results/content-safety-live-v1.json").read_text("utf-8")
    )
    live = json.loads(
        (ROOT / "evals/agent/results/content-safety-live-network-v1.json").read_text("utf-8")
    )
    assert failed["budget"]["requests"] == 9 and not failed["synthetic_visible_outputs"]
    assert failed["accounting"]["unknown_cost_calls"] == 9 and not failed["passed"]
    calls = [t for t in live["traces"] if t["kind"] == "provider"]
    assert len(calls) == live["budget"]["requests"] == len(live["synthetic_visible_outputs"]) == 14
    assert (
        live["source_stable"] and live["passed"] and live["accounting"]["unknown_cost_calls"] == 0
    )
    assert (
        sum(cost_cny(t["usage"]) for t in calls)
        == live["accounting"]["usage_priced_peak_upper_bound_cny"]
    )
    assert all(r["passed"] for r in live["cases"] + live["reviews"])
