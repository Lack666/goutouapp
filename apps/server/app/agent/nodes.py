"""Safety-first semantic nodes with typed provider output and scoped updates."""

from typing import TypedDict

from app.agent.action_validation import validate_action, validate_response
from app.agent.analysis_validation import validate_analysis
from app.agent.capabilities import boundary_plan, imported_chat_plan
from app.agent.content_safety import ContentReviewRequired, review_content
from app.agent.contracts import (
    ActionPlan,
    AnalysisResult,
    Fact,
    FactExtractionResult,
    Inference,
    KnowledgeRouteResult,
    LoadedReference,
    ResponseResult,
    Route,
    SafetyResult,
    Scenario,
    ScenarioResult,
    Unknown,
)
from app.agent.dependencies import RuntimeDependencies
from app.agent.errors import AgentInputError, AgentStructuredOutputError
from app.agent.knowledge import ContextBudget, ReferenceRegistry, load_references, route_knowledge
from app.agent.prompts import action, analysis, fiu, response, safety, scenario
from app.agent.prompts.common import context_payload
from app.agent.safety_validation import safety_answer, verified_safety
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


class KnowledgeRouteUpdate(TypedDict):
    knowledge_route: KnowledgeRouteResult
    selected_references: list[str]


class LoadedContextUpdate(TypedDict):
    retrieved_context: list[LoadedReference]


class AnalysisUpdate(TypedDict):
    analysis_result: AnalysisResult


class ActionUpdate(TypedDict):
    action_plan: ActionPlan


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
    result = verified_safety(result, state)
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


def knowledge_router(
    state: AgentState, registry: ReferenceRegistry, budget: ContextBudget
) -> KnowledgeRouteUpdate:
    safety_result = state["safety"]
    route = state["route"]
    if safety_result is None or route is None:
        raise RuntimeError("safety decision is unavailable")
    result = route_knowledge(
        safety=safety_result,
        route=route,
        scenario=state["scenario"],
        current_message=state["current_message"],
        max_references=budget.max_references,
    )
    for alias in result.selected_references:
        registry.get(alias)
    return {"knowledge_route": result, "selected_references": result.selected_references}


def load_reference_context(
    state: AgentState, registry: ReferenceRegistry, budget: ContextBudget
) -> LoadedContextUpdate:
    return {"retrieved_context": load_references(state["selected_references"], registry, budget)}


async def relationship_analysis(
    state: AgentState, dependencies: RuntimeDependencies
) -> AnalysisUpdate:
    if (
        state["scenario"] is None
        or state["safety"] is None
        or state["safety"].safety_route_required
    ):
        raise AgentStructuredOutputError() from None
    if not state["retrieved_context"]:
        raise AgentStructuredOutputError() from None
    result = await dependencies.llm_provider.structured_output(
        [
            LLMMessage(role="system", content=analysis.SYSTEM),
            LLMMessage(role="user", content=analysis.input_payload(state)),
        ],
        AnalysisResult,
    )
    if not isinstance(result, AnalysisResult):
        raise AgentStructuredOutputError() from None
    validate_analysis(result, state)
    return {"analysis_result": result}


async def action_planner(state: AgentState, dependencies: RuntimeDependencies) -> ActionUpdate:
    if state["analysis_result"] is None or state["scenario"] is None:
        raise AgentStructuredOutputError() from None
    if state["scenario"].primary == Scenario.CHAT_IMPORT:
        result = imported_chat_plan(state)
        validate_action(result, state)
        return {"action_plan": result}
    if state["route"] == Route.BOUNDARY:
        result = boundary_plan(state)
        validate_action(result, state)
        return {"action_plan": result}
    result = await dependencies.llm_provider.structured_output(
        [
            LLMMessage(role="system", content=action.SYSTEM),
            LLMMessage(role="user", content=action.input_payload(state)),
        ],
        ActionPlan,
    )
    if not isinstance(result, ActionPlan):
        raise AgentStructuredOutputError() from None
    try:
        validate_action(result, state)
    except ContentReviewRequired:
        approval = await review_content(result, state, dependencies.llm_provider)
        validate_action(result, state, approval=approval)
    return {"action_plan": result}


async def response_generator(state: AgentState, dependencies: RuntimeDependencies) -> FinalUpdate:
    if state["action_plan"] is None or state["analysis_result"] is None:
        raise AgentStructuredOutputError() from None
    if state["route"] == Route.BOUNDARY or (
        state["scenario"] and state["scenario"].primary == Scenario.CHAT_IMPORT
    ):
        plan = state["action_plan"]
        result = ResponseResult(
            final_answer=plan.message_suggestion or plan.recommended_action,
            contact_policy=plan.contact_policy,
        )
        validate_response(result, state)
        return {"final_answer": result.final_answer}
    result = await dependencies.llm_provider.structured_output(
        [
            LLMMessage(role="system", content=response.SYSTEM),
            LLMMessage(role="user", content=response.input_payload(state)),
        ],
        ResponseResult,
    )
    if not isinstance(result, ResponseResult):
        raise AgentStructuredOutputError() from None
    try:
        validate_response(result, state)
    except ContentReviewRequired:
        approval = await review_content(result, state, dependencies.llm_provider)
        validate_response(result, state, approval=approval)
    return {"final_answer": result.final_answer}


def safety_finalize(state: AgentState) -> SafetyFinalUpdate:
    if state["safety"] is None or state["route"] != Route.SAFETY:
        raise RuntimeError("safety finalizer received another route")
    return {
        "scenario": ScenarioResult(primary=Scenario.SAFETY, reason_summary="Safety takes priority"),
        "final_answer": safety_answer(state),
    }


def route_after_safety(state: AgentState) -> str:
    if state["route"] == Route.SAFETY:
        return "safety"
    if state["route"] in {Route.ORDINARY, Route.BOUNDARY}:
        return "ordinary"
    raise RuntimeError("safety check did not choose a route")
