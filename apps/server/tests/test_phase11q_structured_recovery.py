"""Frozen failures stay failures; explicit new fixtures exercise the formal contracts."""

import asyncio
import copy
import json
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.agent.action_validation import has_safety_cues, validate_action, validate_response
from app.agent.analysis_validation import validate_analysis
from app.agent.content_safety import ContentReviewRequired, review_content
from app.agent.contracts import (
    ActionPlan,
    AgentInput,
    AnalysisResult,
    FactExtractionResult,
    ResponseResult,
    Route,
    SafetyResult,
    ScenarioResult,
)
from app.agent.dependencies import RuntimeDependencies
from app.agent.errors import AgentStructuredOutputError
from app.agent.knowledge import ContextBudget, ReferenceRegistry
from app.agent.nodes import knowledge_router, load_reference_context, response_generator
from app.agent.prompts import action, analysis, response
from app.agent.response_composition import compose_response
from app.agent.state import initial_state
from app.llm.mock import MockLLMProvider
from app.observability import TRACES, node_scope, run_scope
from evals.agent.content_safety_eval import oracle_review

RESULTS = Path(__file__).resolve().parents[3] / "evals/agent/results"


def frozen(case_id):
    row = json.loads((RESULTS / f"independent-{case_id}-v1.json").read_text(encoding="utf-8"))
    outputs = {
        item["schema"]: json.loads(raw["content"])
        for item, raw in zip(row["pydantic"], row["raw_visible_outputs"], strict=True)
    }
    state = initial_state(
        AgentInput(user_id=uuid4(), conversation_id=uuid4(), message=row["input"])
    )
    state["safety"] = SafetyResult.model_validate_json(json.dumps(outputs["SafetyResult"]))
    state["scenario"] = ScenarioResult.model_validate_json(json.dumps(outputs["ScenarioResult"]))
    state["route"] = Route(row["route"])
    fiu = FactExtractionResult.model_validate(outputs["FactExtractionResult"])
    state.update(facts=fiu.facts, inferences=fiu.inferences, unknowns=fiu.unknowns)
    registry, budget = ReferenceRegistry(), ContextBudget()
    state.update(knowledge_router(state, registry, budget))
    state.update(load_reference_context(state, registry, budget))
    return state, outputs


@pytest.mark.parametrize("case_id", ["iq-n07", "iq-n12"])
def test_frozen_response_omission_composes_plan_without_discarding_model_candidate(case_id):
    state, outputs = frozen(case_id)
    state["analysis_result"] = AnalysisResult.model_validate(outputs["AnalysisResult"])
    state["action_plan"] = ActionPlan.model_validate(outputs["ActionPlan"])
    raw = ResponseResult.model_validate(outputs["ResponseResult"])
    with pytest.raises(AgentStructuredOutputError):
        validate_response(raw, state)
    validate_action(state["action_plan"], state)
    provider = MockLLMProvider()
    provider.queue_structured(outputs["ResponseResult"])
    with run_scope(state["run_id"]), node_scope("response_generator"):
        update = asyncio.run(response_generator(state, RuntimeDependencies(llm_provider=provider)))
    approved = state["action_plan"].message_suggestion or state["action_plan"].recommended_action
    assert update["final_answer"] == f"{approved}\n\n{raw.final_answer}"
    validate_response(
        ResponseResult(final_answer=update["final_answer"], contact_policy=raw.contact_policy),
        state,
    )
    assert not provider._structured and not provider._chats
    events = [
        e
        for e in TRACES.snapshot()
        if e["run_id"] == str(state["run_id"]) and e["kind"] == "response_composition"
    ]
    assert len(events) == 1 and events[0]["changed"] is True and events[0]["retries"] == 0
    assert set(events[0]) == {"kind", "time", "run_id", "node", "changed", "retries"}


@pytest.mark.parametrize(
    "clause",
    ["参考 F999。", "她肯定爱你。", "但换平台联系她。", "也可以冒充朋友。"],
)
def test_composition_cannot_hide_invalid_or_dangerous_additions(clause):
    state, outputs = frozen("iq-n12")
    state["analysis_result"] = AnalysisResult.model_validate(outputs["AnalysisResult"])
    state["action_plan"] = ActionPlan.model_validate(outputs["ActionPlan"])
    raw = ResponseResult(final_answer=clause, contact_policy="reply")
    composed = compose_response(raw, state)
    assert clause in composed.final_answer
    with pytest.raises(AgentStructuredOutputError):
        validate_response(composed, state)


def test_composition_retains_length_and_policy_guards_and_leaves_already_valid_answer_alone():
    state, outputs = frozen("iq-n12")
    state["action_plan"] = ActionPlan.model_validate(outputs["ActionPlan"])
    required = state["action_plan"].message_suggestion
    valid = ResponseResult(final_answer=required, contact_policy="reply")
    assert compose_response(valid, state) == valid
    with pytest.raises(AgentStructuredOutputError):
        compose_response(ResponseResult(final_answer="字" * 3000, contact_policy="reply"), state)
    with pytest.raises(AgentStructuredOutputError):
        compose_response(ResponseResult(final_answer=required, contact_policy="observe"), state)


def test_frozen_n10_has_six_actual_ids_not_an_overlong_id_or_missing_analysis():
    state, outputs = frozen("iq-n10")
    state["analysis_result"] = AnalysisResult.model_validate(outputs["AnalysisResult"])
    raw = outputs["ActionPlan"]
    assert raw["supporting_analysis_ids"] == ["A1", "A2", "A3", "A4", "A8", "A13"]
    with pytest.raises(ValidationError) as error:
        ActionPlan.model_validate(raw)
    assert any(
        e["loc"] == ("supporting_analysis_ids",) and e["type"] == "too_long"
        for e in error.value.errors()
    )
    # New synthetic generation fixture explicitly selects genuine supporting points.
    fixture = copy.deepcopy(raw)
    fixture["supporting_analysis_ids"] = ["A1", "A2", "A4", "A8", "A13"]
    plan = ActionPlan.model_validate(fixture)
    with pytest.raises(ContentReviewRequired):
        validate_action(plan, state)
    reviewer = MockLLMProvider()
    reviewer.queue_chat(oracle_review(plan))
    approval = asyncio.run(review_content(plan, state, reviewer))
    validate_action(plan, state, approval=approval)
    fixture["supporting_analysis_ids"] = ["A999"]
    with pytest.raises(AgentStructuredOutputError):
        validate_action(ActionPlan.model_validate(fixture), state)


def test_frozen_n16_observed_unknown_source_stays_invalid_without_fabricating_fact_ids():
    state, outputs = frozen("iq-n16")
    raw = outputs["AnalysisResult"]
    assert raw["observations"][1]["evidence_ids"] == ["F3", "U1"]
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate(raw)
    # Explicit synthetic split, not runtime coercion of the recorded model output.
    fixture = copy.deepcopy(raw)
    fixture["observations"][1]["statement"] = "用户以假设情形提出问题。"
    fixture["observations"][1]["evidence_ids"] = ["F3"]
    validate_analysis(AnalysisResult.model_validate(fixture), state)
    assert any(p["evidence_ids"] == ["U1"] for p in fixture["uncertainties"])
    fixture["observations"][1]["evidence_ids"] = ["F999"]
    with pytest.raises(AgentStructuredOutputError):
        validate_analysis(AnalysisResult.model_validate(fixture), state)


@pytest.mark.parametrize("case_id,extra", [("iq-n17", "framework"), ("iq-n20", "knowledge_notes")])
def test_frozen_extra_business_fields_not_silently_discarded(case_id, extra):
    state, outputs = frozen(case_id)
    raw = outputs["AnalysisResult"]
    assert extra in raw and raw[extra]
    with pytest.raises(ValidationError) as error:
        AnalysisResult.model_validate(raw)
    assert any(e["type"] == "extra_forbidden" for e in error.value.errors())
    # Hand-authored valid fixture retains every reference statement in a legal list.
    fixture = copy.deepcopy(raw)
    extra_points = fixture.pop(extra)
    fixture["relationship_dynamics"].extend(extra_points)
    parsed = AnalysisResult.model_validate(fixture)
    validate_analysis(parsed, state)
    assert all(p in fixture["relationship_dynamics"] for p in extra_points)


@pytest.mark.parametrize("case_id", ["iq-n10", "iq-n16", "iq-n17", "iq-n20"])
def test_payload_projects_live_schema_and_valid_source_identifiers(case_id):
    state, outputs = frozen(case_id)
    contract = json.loads(analysis.input_payload(state))["output_contract"]
    assert contract["allowed_top_level_keys"] == list(AnalysisResult.model_fields)
    assert contract["additional_keys_forbidden"] is True
    assert contract["source_ids_by_kind"]["observed"]["evidence_ids_only"] == [
        f"F{i}" for i in range(1, len(state["facts"]) + 1)
    ]
    assert contract["source_ids_by_kind"]["observed"]["reference_ids"] == []
    if case_id == "iq-n10":
        state["analysis_result"] = AnalysisResult.model_validate(outputs["AnalysisResult"])
        ids = json.loads(action.input_payload(state))["supporting_analysis_id_contract"]
        assert ids["min_items"] == 1 and ids["max_items"] == 5 and ids["unique"]
        assert set(outputs["ActionPlan"]["supporting_analysis_ids"]) <= set(ids["allowed_ids"])
        state["action_plan"] = ActionPlan.model_validate(
            outputs["ActionPlan"] | {"supporting_analysis_ids": ["A1", "A2"]}
        )
        assert json.loads(response.input_payload(state))["exact_required_text"] == (
            state["action_plan"].recommended_action
        )


@pytest.mark.parametrize("bad", ["文字\ufffd错误", "隐藏\x00控制", "隐藏\x1b控制"])
def test_corrupt_text_is_rejected_in_action_and_final_answer(bad):
    state, outputs = frozen("iq-n12")
    state["analysis_result"] = AnalysisResult.model_validate(outputs["AnalysisResult"])
    state["action_plan"] = ActionPlan.model_validate(outputs["ActionPlan"])
    action_data = outputs["ActionPlan"] | {"observation_window": bad}
    with pytest.raises(AgentStructuredOutputError):
        validate_action(ActionPlan.model_validate(action_data), state)
    candidate = compose_response(ResponseResult(final_answer=bad, contact_policy="reply"), state)
    with pytest.raises(AgentStructuredOutputError):
        validate_response(candidate, state)


@pytest.mark.parametrize(
    "text",
    [
        "你们以前常去那条街，可以提起那次散步。",
        "我们之前经常一起吃饭。",
        "我平时会去附近一家咖啡馆。",
        "We used to visit that place together.",
        "You often met after work.",
    ],
)
def test_personal_experience_claims_trigger_contextual_review_not_automatic_allow(text):
    assert has_safety_cues(text)
