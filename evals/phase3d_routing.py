"""Offline Golden router evaluation using expected semantic labels as fixtures."""

from __future__ import annotations

from app.agent.contracts import (
    KnowledgeRouteResult,
    RiskLevel,
    Route,
    SafetyResult,
    Scenario,
    ScenarioResult,
)
from app.agent.errors import AgentKnowledgeError
from app.agent.knowledge import ReferenceRegistry, route_knowledge
from evals.validate import load_cases


def evaluate_route(
    selected: KnowledgeRouteResult, expectation: dict, registry: ReferenceRegistry
) -> list[str]:
    """Check flexible required/allowed/forbidden constraints, not exact lists."""
    knowledge = expectation["knowledge"]
    aliases = selected.selected_references
    allowed = set(knowledge["allowed"])
    required = set(knowledge["required_any"])
    forbidden = set(knowledge["forbidden"])
    errors: list[str] = []
    if aliases[0] not in required:
        errors.append("required primary reference is not first")
    if not required.intersection(aliases):
        errors.append("required reference is missing")
    if not set(aliases) <= allowed:
        errors.append("reference outside allowed set")
    if set(aliases) & forbidden:
        errors.append("forbidden reference selected")
    if len(aliases) > knowledge["max_count"]:
        errors.append("reference count exceeds Golden maximum")
    for alias in aliases:
        try:
            registry.get(alias)
        except AgentKnowledgeError:
            errors.append("selected alias is absent from registry")
    if expectation["route"] == "safety" and aliases[0] != "safety":
        errors.append("safety reference must be first")
    return errors


def evaluate_all(registry: ReferenceRegistry | None = None) -> tuple[int, list[str]]:
    registry = registry or ReferenceRegistry()
    errors: list[str] = []
    cases = load_cases()
    for case in cases:
        expectation = case["expected"]
        route = Route(expectation["route"])
        high = expectation["safety"] == "high"
        safety = SafetyResult(
            risk_level=RiskLevel.HIGH if high else RiskLevel.NORMAL,
            safety_route_required=high,
        )
        scenario = (
            None
            if high
            else ScenarioResult(
                primary=Scenario(expectation["scenario"]),
                reason_summary="Golden semantic fixture",
            )
        )
        selected = route_knowledge(
            safety=safety,
            route=route,
            scenario=scenario,
            current_message=case["input"],
        )
        errors.extend(
            f"{case['id']}: {error}" for error in evaluate_route(selected, expectation, registry)
        )
    return len(cases), errors
