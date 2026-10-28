"""Frozen live failures remain failures; the fix never repairs or retries outputs."""

import asyncio
import json
from pathlib import Path
from uuid import uuid4

import pytest

from app.agent.analysis_validation import (
    ACTION_CUES,
    BOUNDARY_BYPASS_CUES,
    UNSUPPORTED_CERTAINTY_CUES,
    has_unsupported_certainty,
)
from app.agent.content_safety import candidate_fields
from app.agent.contracts import ActionPlan, AgentInput, AnalysisResult, ResponseResult
from app.agent.dependencies import RuntimeDependencies
from app.agent.runtime import AgentRuntime
from app.llm.errors import LLMStructuredOutputError
from app.llm.mock import MockLLMProvider
from app.llm.validation import validate_structured_output
from app.observability import TRACES
from evals.agent.content_safety_eval import oracle_review, queue_safe_fixture_review
from scripts.diagnose_phase11_structured import diagnose

ROOT = Path(__file__).resolve().parents[3]


def test_original_five_failures_have_reproducible_distinct_causes():
    failures = diagnose()
    assert {f["case_id"] for f in failures} == {
        "communication-02",
        "communication-04",
        "communication-05",
        "grounding-01",
        "grounding-07",
    }
    for failure in failures:
        assert failure["node"] == "relationship_analysis"
        assert failure["finish_reason"] == "stop"
        assert failure["usage"]["output_tokens"] < failure["max_output_tokens"]
        if failure["case_id"] == "grounding-01":
            assert not failure["pydantic_errors"]
            assert len(failure["guard_matches"]) == 1
            assert "证据不足以支持该结论" in failure["guard_matches"][0]["statement"]
        else:
            assert not failure["guard_matches"]
            assert len(failure["pydantic_errors"]) == 1
            error = failure["pydantic_errors"][0]
            assert error["loc"][0] == "risks"
            assert error["input"]["kind"] == "tentative"
            assert all(i.startswith("U") for i in error["input"]["evidence_ids"])


@pytest.mark.parametrize("group", ["communication", "grounding"])
def test_historical_invalid_outputs_are_still_rejected(group):
    run = json.loads((ROOT / f"evals/agent/results/final-live-{group}.json").read_text("utf-8"))
    failed = {c["run_id"] for c in run["cases"] if c["status"] != "completed"}
    for trace, output in zip(
        [t for t in run["traces"] if t["kind"] == "provider"],
        run["synthetic_visible_outputs"],
        strict=True,
    ):
        if trace["run_id"] not in failed or trace.get("schema") != "AnalysisResult":
            continue
        if trace["status"] == "failed":
            with pytest.raises(LLMStructuredOutputError):
                validate_structured_output(output["content"], AnalysisResult)
        else:
            analysis = validate_structured_output(output["content"], AnalysisResult)
            assert any(p.search(analysis.core_issue) for p in UNSUPPORTED_CERTAINTY_CUES)


@pytest.mark.parametrize(
    "name",
    [
        "final-live-communication",
        "final-live-grounding",
        "reliability-fix-v3-original-five",
        "reliability-fix-v4-original-five",
        "reliability-fix-v5-original-five",
        "reliability-fix-v5-regression",
    ],
)
def test_archived_outputs_replay_current_pipeline_with_explicit_review_fixtures(name):
    run = json.loads((ROOT / f"evals/agent/results/{name}.json").read_text("utf-8"))
    questions = {
        c["id"]: c["input"]
        for c in map(
            json.loads, (ROOT / "evals/agent/cases.v1.jsonl").read_text("utf-8").splitlines()
        )
    }
    for case in run["cases"]:
        provider = MockLLMProvider()
        for trace, output in zip(
            [t for t in run["traces"] if t["kind"] == "provider"],
            run["synthetic_visible_outputs"],
            strict=True,
        ):
            if trace["run_id"] == case["run_id"]:
                provider.queue_structured(output["content"])
                if trace.get("schema") == "AnalysisResult":
                    try:
                        candidate = AnalysisResult.model_validate_json(output["content"])
                    except ValueError:
                        continue
                    if any(
                        pattern.search(text)
                        for text in candidate_fields(candidate).values()
                        for pattern in (
                            *ACTION_CUES,
                            *BOUNDARY_BYPASS_CUES,
                            *UNSUPPORTED_CERTAINTY_CUES,
                        )
                    ):
                        # The two matching archived analyses reject user certainty.
                        # This explicit current-protocol wiring oracle changes no
                        # archived provider output and proves no model accuracy.
                        provider.queue_chat(oracle_review(candidate))
                if trace.get("schema") in {"ActionPlan", "ResponseResult"}:
                    schema = ActionPlan if trace["schema"] == "ActionPlan" else ResponseResult
                    queue_safe_fixture_review(
                        provider, schema.model_validate_json(output["content"])
                    )
        run_id = uuid4()
        result = asyncio.run(
            AgentRuntime(dependencies=RuntimeDependencies(llm_provider=provider)).run(
                AgentInput(
                    run_id=run_id,
                    user_id=uuid4(),
                    conversation_id=uuid4(),
                    message=questions[case["id"]],
                )
            )
        )
        corrected_protective_mention = (
            name == "reliability-fix-v3-original-five" and case["id"] == "communication-04"
        )
        retained_unresolved_refusal = (
            name == "reliability-fix-v5-regression" and case["id"] == "communication-01"
        )
        if corrected_protective_mention:
            # The historical FAIL is immutable; contextual review now permits the
            # protective stop condition mentioning threats in this frozen response.
            assert case["status"] == "failed" and result.status == "completed"
        elif retained_unresolved_refusal:
            # The old scheduling-only regex exception is gone. Replaying the
            # archived explicit_refusal retains boundary, with a locally owned
            # stop template. This is a current-pipeline result, not an archive
            # status/oracle change and not evidence the old classifier was right.
            assert case["status"] == "failed" and result.status == "completed"
            assert result.route.value == "boundary"
            assert "explicit_refusal" in result.safety.risk_categories
        else:
            assert result.status == case["status"]
        if case["id"] == "grounding-12":
            # The unsupported capability now has validated local Action/Response;
            # neither of the two historical generated outputs should be consumed.
            from app.agent.capabilities import imported_chat_reply

            assert len(provider._structured) == 2
            assert result.action.stop_conditions
            assert result.final_answer == imported_chat_reply(questions[case["id"]])
        elif retained_unresolved_refusal:
            # Current boundary uses the archived boundary analysis and owned
            # template; the historical model ActionPlan remains unconsumed.
            assert len(provider._structured) == 1
        else:
            assert not provider._structured
        original_failure = [
            t["node"]
            for t in run["traces"]
            if t["run_id"] == case["run_id"] and t["kind"] == "node_end" and t["status"] == "failed"
        ]
        replay_failure = [
            t["node"]
            for t in TRACES.snapshot()
            if t["run_id"] == str(run_id) and t["kind"] == "node_end" and t["status"] == "failed"
        ]
        if corrected_protective_mention:
            assert original_failure == ["response_generator"] and not replay_failure
        elif original_failure == ["relationship_analysis"] and case["id"] == "grounding-01":
            # The precise false positive is fixed, but absent later provider outputs
            # must still fail, rather than fabricating a completed historical answer.
            assert replay_failure == ["action_planner"]
        elif retained_unresolved_refusal:
            assert original_failure == ["action_planner"] and not replay_failure
        elif name == "reliability-fix-v5-regression" and case["id"] == "communication-03":
            # The formerly rejected ActionPlan is now accepted. No frozen response
            # exists, so it must fail at Response rather than fabricate completion.
            assert replay_failure == ["response_generator"]
        else:
            assert replay_failure == original_failure


@pytest.mark.parametrize(
    "statement",
    [
        "她一定不爱你。",
        "对方肯定故意冷落你。",
        "INTJ一定忠诚。",
        "用户推断对方一定不爱你，证据不足以支持该结论。",
        "对方‘一定不爱你’。",
        "对方“一定不爱你”。",
        "用户推断对方“一定不爱你”。",
        "用户推断对方“一定不爱你”，证据不足以支持该结论，但我认为她一定不爱你。",
        "用户推断对方“一定不爱你”，证据不足以支持该结论。她一定不爱你。",
        "用户推断“她一定不爱你”，证据不足以支持该结论。",
        "用户将对方“一定不爱你”等同于事实，无法支持该结论；她一定不爱你。",
        "用户推断对方“一定不爱你”，无法支持该结论；其实这个结论正确。",
    ],
)
def test_certainty_cues_select_review_for_assertions_and_quoted_discussion(statement):
    assert has_unsupported_certainty(statement)


def test_rejected_cross_quotes_are_review_triggers_without_sentence_exemptions():
    original = next(f for f in diagnose() if f["case_id"] == "grounding-01")
    statement = original["guard_matches"][0]["statement"]
    assert has_unsupported_certainty(statement)
    assert has_unsupported_certainty(
        "用户将对方两小时未回消息与“一定不爱我”直接等同；"
        "现有材料只能确认回复间隔与用户的疑问，无法支撑关于对方感情状态的任何确定结论。"
    )
    assert has_unsupported_certainty(statement + "她一定不爱你。")
