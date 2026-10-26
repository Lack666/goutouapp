"""Frozen live failures remain failures; the fix never repairs or retries outputs."""

import asyncio
import json
from pathlib import Path
from uuid import uuid4

import pytest

from app.agent.analysis_validation import UNSUPPORTED_CERTAINTY_CUES, has_unsupported_certainty
from app.agent.contracts import AgentInput, AnalysisResult
from app.agent.dependencies import RuntimeDependencies
from app.agent.runtime import AgentRuntime
from app.llm.errors import LLMStructuredOutputError
from app.llm.mock import MockLLMProvider
from app.llm.validation import validate_structured_output
from app.observability import TRACES
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
def test_frozen_provider_outputs_replay_original_graph_outcomes_without_retry(name):
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
        assert result.status == case["status"]
        assert not provider._structured  # Every supplied output consumed once, no fallback call.
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
        if original_failure == ["relationship_analysis"] and case["id"] == "grounding-01":
            # The precise false positive is fixed, but absent later provider outputs
            # must still fail, rather than fabricating a completed historical answer.
            assert replay_failure == ["action_planner"]
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
def test_actual_certainty_and_ambiguous_quotation_still_fail_closed(statement):
    assert has_unsupported_certainty(statement)


def test_only_attributed_rejected_cross_quote_is_exempted():
    original = next(f for f in diagnose() if f["case_id"] == "grounding-01")
    statement = original["guard_matches"][0]["statement"]
    assert not has_unsupported_certainty(statement)
    assert not has_unsupported_certainty(
        "用户将对方两小时未回消息与“一定不爱我”直接等同；"
        "现有材料只能确认回复间隔与用户的疑问，无法支撑关于对方感情状态的任何确定结论。"
    )
    assert has_unsupported_certainty(statement + "她一定不爱你。")
