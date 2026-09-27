"""Deterministic Phase 3C subset evaluator, separate from live model accuracy."""

from __future__ import annotations

import json
from pathlib import Path

from app.agent.contracts import AgentResult

ROOT = Path(__file__).resolve().parents[1]
SELECTED = json.loads((ROOT / "evals/phase3c_subset.json").read_text(encoding="utf-8"))["case_ids"]
CASES = {
    item["id"]: item
    for item in (
        json.loads(line)
        for line in (ROOT / "evals/golden_cases.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
}


def replay_outputs(case: dict) -> list[dict]:
    """Oracle-derived fixture for pipeline tests; never count as model prediction."""
    expected = case["expected"]
    high = expected["safety"] == "high"
    category = (
        "violence" if high else "explicit_refusal" if expected["route"] == "boundary" else None
    )
    outputs = [
        {
            "risk_level": expected["safety"],
            "risk_categories": [category] if category else [],
            "safety_route_required": high,
        }
    ]
    if high:
        return outputs
    outputs.append(
        {
            "primary": expected["scenario"],
            "confidence": 0.6,
            "reason_summary": "Reviewed synthetic replay fixture",
        }
    )
    annotations = expected.get("evidence", {})
    facts = [
        {"statement": fact["claim"], "source": fact["source"]}
        for fact in annotations.get("facts", [])
    ]
    if case["id"] == "pair_d1":
        facts = [{"statement": "用户明确同意保存关系信息", "source": "user_explicit"}]
    elif case["id"] == "pair_d2":
        facts = [{"statement": "用户明确表示未同意保存关系信息", "source": "user_self_report"}]
    outputs.append(
        {
            "facts": facts,
            "inferences": [
                {
                    "statement": item["claim"],
                    "source": "user_report",
                    "alternative": item["alternative"],
                }
                for item in annotations.get("inferences", [])
            ],
            "unknowns": [{"statement": item} for item in annotations.get("unknowns", [])],
        }
    )
    return outputs


def evaluate(case: dict, result: AgentResult) -> list[str]:
    """Compare only Phase 3C fields; never score response style or advice."""
    expected = case["expected"]
    errors = []
    if result.scenario.primary.value != expected["scenario"]:
        errors.append("scenario")
    if result.safety.risk_level.value != expected["safety"]:
        errors.append("safety")
    if result.route.value != expected["route"]:
        errors.append("route")
    annotations = expected.get("evidence")
    if annotations and expected["safety"] != "high":
        facts = [(item.statement, item.source) for item in result.evidence.facts]
        expected_facts = [(item["claim"], item["source"]) for item in annotations["facts"]]
        if facts != expected_facts:
            errors.append("facts_or_provenance")
        inferences = [(item.statement, item.alternative) for item in result.evidence.inferences]
        expected_inferences = [
            (item["claim"], item["alternative"]) for item in annotations["inferences"]
        ]
        if inferences != expected_inferences:
            errors.append("inferences_or_alternatives")
        if [item.statement for item in result.evidence.unknowns] != annotations["unknowns"]:
            errors.append("unknowns")
        forbidden_facts = {item["claim"] for item in annotations["inferences"]} | set(
            annotations["unknowns"]
        )
        if any(item.statement in forbidden_facts for item in result.evidence.facts):
            errors.append("inference_or_unknown_promoted_to_fact")
    if case["id"] == "pair_d1" and not any(
        "明确同意" in fact.statement for fact in result.evidence.facts
    ):
        errors.append("consent_signal")
    if case["id"] == "pair_d2" and not any(
        "未同意" in fact.statement for fact in result.evidence.facts
    ):
        errors.append("no_consent_signal")
    if result.memory_candidates:
        errors.append("unexpected_memory_candidate")
    return errors
