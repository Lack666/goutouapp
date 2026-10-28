"""Frozen v8 reproduction and explicit oracle decisions for offline wiring tests."""

import json
from pathlib import Path
from uuid import uuid4

from app.agent import AgentInput, initial_state
from app.agent.content_safety import candidate_fields
from app.agent.contracts import (
    AnalysisResult,
    FactExtractionResult,
    Route,
    SafetyResult,
    ScenarioResult,
)

ROOT = Path(__file__).resolve().parents[2]
DATASET = Path(__file__).with_name("content-safety-cases.v1.jsonl")
FROZEN = ROOT / "evals/agent/results/closeout-v8-live.json"


def cases():
    return [json.loads(line) for line in DATASET.read_text("utf-8").splitlines()]


def frozen_state():
    run = json.loads(FROZEN.read_text("utf-8"))
    case = next(c for c in run["cases"] if c["id"] == "communication-03")
    outputs = {
        trace["schema"]: json.loads(output["content"])
        for trace, output in zip(
            [t for t in run["traces"] if t["kind"] == "provider"],
            run["synthetic_visible_outputs"],
            strict=True,
        )
        if trace["run_id"] == case["run_id"]
    }
    state = initial_state(
        AgentInput(user_id=uuid4(), conversation_id=uuid4(), message="我想拒绝邀约又不想编借口。")
    )
    state["safety"] = SafetyResult.model_validate_json(json.dumps(outputs["SafetyResult"]))
    state["scenario"] = ScenarioResult.model_validate_json(json.dumps(outputs["ScenarioResult"]))
    state["route"] = Route.ORDINARY
    state["analysis_result"] = AnalysisResult.model_validate(outputs["AnalysisResult"])
    fiu = FactExtractionResult.model_validate(outputs["FactExtractionResult"])
    state.update(facts=fiu.facts, inferences=fiu.inferences, unknowns=fiu.unknowns)
    return state, outputs


def oracle_review(candidate, *, field=None, intent="safe_action", violations=()):
    """Test oracle, NOT a model output or evidence of semantic model accuracy."""
    contact = getattr(candidate, "contact_policy", None) in {"observe", "pause", "stop_contact"}
    return json.dumps(
        {
            **({"policy_version": "contact-v1"} if contact else {}),
            "fields": [
                {
                    "field": name,
                    "intent": intent if name == field else "safe_action",
                    "violations": list(violations) if name == field else [],
                    **({"contact_effects": []} if contact else {}),
                }
                for name in candidate_fields(candidate)
            ],
        },
        ensure_ascii=False,
    )


def queue_safe_fixture_review(provider, candidate):
    """Call only for manually reviewed safe synthetic fixtures, never production."""
    from app.agent.action_validation import has_safety_cues

    if getattr(candidate, "contact_policy", None) in {"observe", "pause", "stop_contact"} or any(
        has_safety_cues(v) for v in candidate_fields(candidate).values()
    ):
        provider.queue_chat(oracle_review(candidate))
