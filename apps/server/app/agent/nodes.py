"""Safety-first semantic nodes with typed provider output and scoped updates."""

from typing import TypedDict

from app.agent.contracts import (
    Fact,
    FactExtractionResult,
    Inference,
    Route,
    SafetyResult,
    Scenario,
    ScenarioResult,
    Unknown,
)
from app.agent.dependencies import RuntimeDependencies
from app.agent.errors import AgentInputError, AgentStructuredOutputError
from app.agent.prompts import fiu, safety, scenario
from app.agent.prompts.common import context_payload
from app.agent.state import AgentState
from app.llm.models import LLMMessage

BOUNDARY_CATEGORIES = frozenset({"explicit_refusal", "consent_withdrawal"})
FACT_SOURCES = frozenset(
    {
        "user_report",
        "user_report_quote",
        "user_self_report",
        "chat_message",
        "screenshot",
        "tool_result",
        "user_explicit",
    }
)


class NormalizeUpdate(TypedDict):
    current_message: str


class SafetyUpdate(TypedDict):
    safety: SafetyResult
    route: Route


class ScenarioUpdate(TypedDict):
    scenario: ScenarioResult


class FiuUpdate(TypedDict):
    facts: list[Fact]
    inferences: list[Inference]
    unknowns: list[Unknown]


class FinalUpdate(TypedDict):
    final_answer: str


class SafetyFinalUpdate(ScenarioUpdate, FinalUpdate):
    pass


def normalize_input(state: AgentState) -> NormalizeUpdate:
    message = state["current_message"].strip()
    if not message:
        raise AgentInputError() from None
    return {"current_message": message}


async def safety_check(state: AgentState, dependencies: RuntimeDependencies) -> SafetyUpdate:
    result = await dependencies.llm_provider.structured_output(
        [
            LLMMessage(role="system", content=safety.SYSTEM),
            LLMMessage(
                role="user", content=context_payload(state["current_message"], state["messages"])
            ),
        ],
        SafetyResult,
    )
    if not isinstance(result, SafetyResult):
        raise AgentStructuredOutputError() from None
    if result.safety_route_required:
        route = Route.SAFETY
    elif BOUNDARY_CATEGORIES.intersection(result.risk_categories):
        route = Route.BOUNDARY
    else:
        route = Route.ORDINARY
    return {"safety": result, "route": route}


async def classify_scenario(state: AgentState, dependencies: RuntimeDependencies) -> ScenarioUpdate:
    if state["safety"] is None or state["safety"].safety_route_required:
        raise AgentStructuredOutputError() from None
    result = await dependencies.llm_provider.structured_output(
        [
            LLMMessage(role="system", content=scenario.SYSTEM),
            LLMMessage(
                role="user", content=context_payload(state["current_message"], state["messages"])
            ),
        ],
        ScenarioResult,
    )
    if not isinstance(result, ScenarioResult) or result.primary == Scenario.SAFETY:
        raise AgentStructuredOutputError() from None
    return {"scenario": result}


async def extract_fiu(state: AgentState, dependencies: RuntimeDependencies) -> FiuUpdate:
    if state["scenario"] is None or state["safety"] is None:
        raise AgentStructuredOutputError() from None
    result = await dependencies.llm_provider.structured_output(
        [
            LLMMessage(role="system", content=fiu.SYSTEM),
            LLMMessage(
                role="user", content=context_payload(state["current_message"], state["messages"])
            ),
        ],
        FactExtractionResult,
    )
    if not isinstance(result, FactExtractionResult):
        raise AgentStructuredOutputError() from None
    if any(fact.source not in FACT_SOURCES for fact in result.facts):
        raise AgentStructuredOutputError() from None
    return {"facts": result.facts, "inferences": result.inferences, "unknowns": result.unknowns}


def minimal_finalize(state: AgentState) -> FinalUpdate:
    if state["scenario"] is None or state["safety"] is None:
        raise RuntimeError("semantic result is incomplete")
    if state["route"] not in {Route.ORDINARY, Route.BOUNDARY}:
        raise RuntimeError("ordinary finalizer received safety route")
    return {
        "final_answer": (
            "Semantic classification and evidence extraction completed; "
            "relationship advice is not yet available."
        )
    }


def safety_finalize(state: AgentState) -> SafetyFinalUpdate:
    if state["safety"] is None or state["route"] != Route.SAFETY:
        raise RuntimeError("safety finalizer received another route")
    return {
        "scenario": ScenarioResult(primary=Scenario.SAFETY, reason_summary="Safety takes priority"),
        "final_answer": (
            "Safety takes priority. Stop harmful actions; if there is immediate danger, "
            "seek a safe place and contact trusted or local emergency support."
        ),
    }


def route_after_safety(state: AgentState) -> str:
    if state["route"] == Route.SAFETY:
        return "safety"
    if state["route"] in {Route.ORDINARY, Route.BOUNDARY}:
        return "ordinary"
    raise RuntimeError("safety check did not choose a route")
