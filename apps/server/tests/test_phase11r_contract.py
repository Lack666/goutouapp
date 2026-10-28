"""Versioned refusal scope and Analysis semantics after Phase11R contract freeze."""

import asyncio
import json
from uuid import uuid4

import pytest
from pydantic import ValidationError
from test_agent_analysis import analysis_state, valid_analysis

from app.agent.analysis_validation import validate_analysis
from app.agent.capabilities import boundary_plan
from app.agent.contact_scope import scope_from_safety
from app.agent.content_safety import ContentReviewRequired, candidate_fields, review_content
from app.agent.contracts import (
    AgentInput,
    AnalysisResult,
    RiskLevel,
    Route,
    SafetyResult,
    ScenarioResult,
)
from app.agent.dependencies import RuntimeDependencies
from app.agent.nodes import safety_check
from app.agent.prompts import scenario
from app.agent.state import initial_state
from app.llm.mock import MockLLMProvider


@pytest.mark.parametrize(
    ("categories", "scope", "route"),
    [
        (["explicit_refusal", "refusal_dating", "necessary_classroom"], "dating", Route.BOUNDARY),
        (["refusal_private", "necessary_work"], "private", Route.BOUNDARY),
        (["refusal_all", "refusal_dating"], "all", Route.BOUNDARY),
        (["explicit_refusal"], "unknown", Route.BOUNDARY),
        (["consent_withdrawal", "necessary_work"], "unknown", Route.BOUNDARY),
        (["schedule_only"], "schedule", Route.ORDINARY),
        (["user_exit"], "user_exit", Route.ORDINARY),
        (["refusal_all", "schedule_only", "user_exit"], "all", Route.BOUNDARY),
        (["refusal_unknown", "refusal_dating"], "unknown", Route.BOUNDARY),
        (["refusal_all_typo"], "unknown", Route.BOUNDARY),
    ],
)
def test_sa03_05_06_scope_precedence(categories, scope, route):
    state = initial_state(
        AgentInput(
            user_id=uuid4(),
            conversation_id=uuid4(),
            message="A synthetic user report",
        )
    )
    output = SafetyResult(
        risk_level=RiskLevel.NORMAL,
        safety_route_required=False,
        risk_categories=categories,
    )
    provider = MockLLMProvider()
    provider.queue_structured(output.model_dump())
    update = asyncio.run(safety_check(state, RuntimeDependencies(llm_provider=provider)))
    assert scope_from_safety(update["safety"]) == scope
    assert update["route"] == route
    assert update["safety"].risk_categories == categories  # never erase a refusal


def test_sa12_high_risk_always_precedes_scope():
    state = analysis_state()
    provider = MockLLMProvider()
    provider.queue_structured(
        dict(
            risk_level="high",
            safety_route_required=True,
            risk_categories=["violence", "refusal_dating", "necessary_classroom"],
        )
    )
    update = asyncio.run(safety_check(state, RuntimeDependencies(llm_provider=provider)))
    assert update["route"] == Route.SAFETY


@pytest.mark.parametrize("category", ["violence", "coercion", "self_harm"])
def test_contradictory_danger_category_cannot_enter_ordinary(category):
    from app.agent.errors import AgentStructuredOutputError

    state = analysis_state()
    provider = MockLLMProvider()
    provider.queue_structured(
        dict(
            risk_level="normal",
            safety_route_required=False,
            risk_categories=[category],
        )
    )
    with pytest.raises(AgentStructuredOutputError):
        asyncio.run(safety_check(state, RuntimeDependencies(llm_provider=provider)))


@pytest.mark.parametrize("scope", ["refusal_all", "refusal_unknown", "consent_withdrawal"])
def test_sa04_no_necessary_exception_for_strict_or_unknown_scope(scope):
    state = analysis_state(route=Route.BOUNDARY)
    state["safety"] = SafetyResult(
        risk_level=RiskLevel.NORMAL,
        safety_route_required=False,
        risk_categories=["explicit_refusal", scope, "necessary_classroom"],
    )
    plan = boundary_plan(state)
    assert "shared classes" not in plan.recommended_action
    assert plan.message_suggestion is None


def test_sa15_schema_is_actual_and_boundary_is_not_scenario():
    assert json.dumps(ScenarioResult.model_json_schema(), ensure_ascii=False) in scenario.SYSTEM
    with pytest.raises(ValidationError):
        ScenarioResult.model_validate_json('{"primary":"boundary","reason_summary":"route"}')
    with pytest.raises(ValueError):
        Route("reply")


def test_sa17_event_window_is_preserved_and_missing_window_rejected():
    from test_phase11r_contact import contact_decision, observe_state

    from app.agent.action_validation import validate_action
    from app.agent.errors import AgentStructuredOutputError

    state = observe_state()
    plan = state["action_plan"]
    assert "下一次自然互动" in plan.observation_window
    provider = MockLLMProvider()
    provider.queue_chat(contact_decision(plan))
    approval = asyncio.run(review_content(plan, state, provider))
    validate_action(plan, state, approval=approval)
    with pytest.raises(AgentStructuredOutputError):
        validate_action(
            plan.model_copy(update={"observation_window": None}), state, approval=approval
        )


@pytest.mark.parametrize(
    ("statement", "safe"),
    [
        ("不能据此认定他一定爱你。", True),
        ("用户引用‘你现在应该发消息’，不代表这是适合当前边界的建议。", True),
        ("他一定爱你。", False),
        ("你现在应该发消息。", False),
        ("不是要绕过拒绝，但可以换平台联系她。", False),
    ],
)
def test_sa08_09_analysis_quote_and_endorsement_are_separate(statement, safe):
    state = analysis_state()
    data = valid_analysis()
    data["core_issue"] = statement
    result = AnalysisResult.model_validate(data)
    with pytest.raises(ContentReviewRequired):
        validate_analysis(result, state)
    provider = MockLLMProvider()
    provider.queue_chat(
        json.dumps(
            {
                "fields": [
                    {
                        "field": key,
                        "intent": "protective_discussion" if safe else "harmful_action",
                        "violations": [] if safe else ["analysis_scope"],
                    }
                    for key in candidate_fields(result)
                ]
            }
        )
    )
    if safe:
        approval = asyncio.run(review_content(result, state, provider))
        validate_analysis(result, state, approval=approval)
        changed = result.model_copy(update={"core_issue": statement + "追加另一个断言"})
        with pytest.raises(ContentReviewRequired):
            validate_analysis(changed, state, approval=approval)
    else:
        from app.agent.errors import AgentStructuredOutputError

        with pytest.raises(AgentStructuredOutputError):
            asyncio.run(review_content(result, state, provider))
