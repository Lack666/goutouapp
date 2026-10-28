"""Replay saved candidates through current guards with explicit MOCK review decisions.

This is wiring evidence, never a claim that a live reviewer/model reclassified text.
Historical generation, routes, failures and oracles are not edited.
"""

import argparse
import asyncio
import json
from pathlib import Path
from uuid import UUID

from app.agent.action_validation import validate_action, validate_response
from app.agent.capabilities import boundary_plan
from app.agent.content_safety import (
    ContentReviewRequired,
    candidate_fields,
    requires_contact_review,
    review_content,
)
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
from app.agent.response_composition import compose_response
from app.agent.state import initial_state
from app.llm.mock import MockLLMProvider
from evals.agent.independent import ROOT, sha, write_new

RESULTS = Path(__file__).with_name("results")
OUTPUT = RESULTS / "r11-offline-replay-v1.json"


def frozen_state(case_id):
    path = RESULTS / f"q11-case-q11-iq-{case_id}-v1.json"
    saved = json.loads(path.read_text("utf-8"))
    outputs = {}
    keys = {
        "risk_level": "safety",
        "primary": "scenario",
        "facts": "fiu",
        "core_issue": "analysis",
        "recommended_action": "action",
        "final_answer": "response",
    }
    for raw in saved["raw_visible_outputs"]:
        value = json.loads(raw["content"])
        for key, name in keys.items():
            if key in value:
                outputs[name] = value
    state = initial_state(
        AgentInput(
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            conversation_id=UUID("00000000-0000-0000-0000-000000000002"),
            message=saved["input"],
        )
    )
    state["safety"] = SafetyResult.model_validate_json(json.dumps(outputs["safety"]))
    state["scenario"] = ScenarioResult.model_validate_json(json.dumps(outputs["scenario"]))
    state["route"] = Route(saved["route"])
    fiu = FactExtractionResult.model_validate(outputs["fiu"])
    state.update(facts=fiu.facts, inferences=fiu.inferences, unknowns=fiu.unknowns)
    state["analysis_result"] = AnalysisResult.model_validate(outputs["analysis"])
    return state, outputs, saved, path


def mock_safe_discussion(candidate, state):
    """Manually assigned safe-fixture oracle, NOT production semantic authorization."""
    contact = requires_contact_review(candidate, state)
    fields = [
        {
            "field": name,
            "intent": "protective_discussion",
            "violations": [],
            **({"contact_effects": []} if contact else {}),
        }
        for name in candidate_fields(candidate)
    ]
    return json.dumps({**({"policy_version": "contact-v1"} if contact else {}), "fields": fields})


async def checked(candidate, state, validator):
    review_count = 0
    try:
        validator(candidate, state)
    except ContentReviewRequired:
        provider = MockLLMProvider()
        provider.queue_chat(mock_safe_discussion(candidate, state))
        approval = await review_content(candidate, state, provider)
        validator(candidate, state, approval=approval)
        review_count = 1
    return review_count


async def replay():
    rows = []
    for case_id in ("n07", "n20", "n10"):
        state, outputs, saved, path = frozen_state(case_id)
        action = ActionPlan.model_validate(outputs["action"])
        reviews = await checked(action, state, validate_action)
        state["action_plan"] = action
        candidate = ResponseResult.model_validate(outputs["response"])
        candidate = compose_response(candidate, state)
        reviews += await checked(candidate, state, validate_response)
        rows.append(
            {
                "id": f"r11-offline-{case_id}",
                "source": path.relative_to(ROOT).as_posix(),
                "source_sha256": sha(path),
                "original_status": saved["status"],
                "original_diagnostic": saved["diagnostic"],
                "original_route": saved["route"],
                "original_route_oracle_pass": saved["checks"]["route"],
                "current_action_response_guards_pass": True,
                "mock_review_count": reviews,
                "candidate_text_unchanged": candidate.final_answer
                == outputs["response"]["final_answer"],
                "limitation": (
                    "Recorded generation + MOCK review oracle; "
                    "not new live generation or a new human score"
                ),
            }
        )
    state, _, saved, path = frozen_state("n10")
    state["safety"] = SafetyResult.model_validate_json(
        json.dumps(
            {
                "risk_level": "normal",
                "risk_categories": ["explicit_refusal", "refusal_dating", "necessary_classroom"],
                "safety_route_required": False,
            }
        )
    )
    state["route"] = Route.BOUNDARY
    plan = boundary_plan(state)
    validate_action(plan, state)
    state["action_plan"] = plan
    response = ResponseResult(
        final_answer=plan.recommended_action, contact_policy=plan.contact_policy
    )
    validate_response(response, state)
    rows.append(
        {
            "id": "r11-offline-n10-contract-v1",
            "input_source": path.relative_to(ROOT).as_posix(),
            "input_unchanged": state["current_message"] == saved["input"],
            "mode": (
                "New versioned synthetic scope fixture; not rewritten historical classifier output"
            ),
            "route": state["route"],
            "safety": state["safety"].model_dump(mode="json"),
            "action_plan": plan.model_dump(mode="json"),
            "final_answer": response.final_answer,
            "current_action_response_guards_pass": True,
        }
    )
    return {"version": "phase11r-offline-replay-v1", "paid_calls": 0, "cases": rows}


async def replay_first_live():
    """Replay first-batch raw responses; never substitute new review decisions."""
    from app.agent.contracts import AgentResult
    from app.agent.dependencies import RuntimeDependencies
    from app.agent.memory import MemoryService
    from app.agent.runtime import AgentRuntime
    from app.llm.errors import LLMStructuredOutputError
    from evals.agent.content_safety_integration import scoped_memory

    path = RESULTS / "r11-live-v1.json"
    saved = json.loads(path.read_text("utf-8"))
    rows = []
    for case in saved["cases"]:
        calls = [c for c in case["traces"] if c["kind"] == "provider"]
        outputs = case["raw_visible_outputs"]
        if len(calls) != len(outputs):
            rows.append({"id": case["id"], "supported": False, "reason": "missing response"})
            continue
        provider = MockLLMProvider()
        for call, raw in zip(calls, outputs, strict=True):
            if call["operation"] == "chat":
                provider.queue_chat(raw["content"], finish_reason=raw["finish_reason"])
            elif raw["finish_reason"] != "stop":
                provider.queue_error("structured_output", LLMStructuredOutputError())
            else:
                provider.queue_structured(raw["content"])
        request = AgentInput(
            user_id=UUID("00000000-0000-0000-0000-000000000011"),
            conversation_id=UUID("00000000-0000-0000-0000-000000000012"),
            relationship_id=UUID("00000000-0000-0000-0000-000000000013"),
            message=case["input"],
            memory_enabled=True,
        )
        store, _ = scoped_memory(request, consented=False)
        before = store.snapshot()
        runtime = AgentRuntime(
            dependencies=RuntimeDependencies(
                llm_provider=provider, memory_service=MemoryService(store)
            )
        )
        result = await runtime.run(request)
        completed = isinstance(result, AgentResult)
        checks = {
            "status_same": completed == (case["status"] == "completed"),
            "route_same": not completed or result.route.value == case["route"],
            "answer_same": not completed or result.final_answer == case["final_answer"],
            "all_saved_responses_consumed": not provider._chats and not provider._structured,
            "zero_memory_side_effects": store.writes == 0 and store.snapshot() == before,
        }
        rows.append(
            {"id": case["id"], "supported": True, "checks": checks, "passed": all(checks.values())}
        )
    return {
        "version": "phase11r-first-live-replay-v1",
        "source_sha256": sha(path),
        "paid_calls": 0,
        "review_decisions": "exact recorded first-live decisions; no oracle substitution",
        "cases": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--first-live", action="store_true")
    args = parser.parse_args()
    result = asyncio.run(replay_first_live() if args.first_live else replay())
    if args.write:
        target = RESULTS / "r11-first-live-replay-v1.json" if args.first_live else OUTPUT
        write_new(target, result)
    print(json.dumps({"replayed": len(result["cases"]), "paid_calls": 0}))


if __name__ == "__main__":
    main()
