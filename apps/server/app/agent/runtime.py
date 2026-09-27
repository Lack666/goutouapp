"""Reusable safety-first LangGraph runtime for typed semantic nodes."""

from collections.abc import Awaitable, Callable
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agent.contracts import (
    AgentInput,
    AgentResult,
    AgentRunStatus,
    FactExtractionResult,
)
from app.agent.dependencies import RuntimeDependencies
from app.agent.errors import AgentError, AgentErrorCode, AgentFailure
from app.agent.knowledge import ReferenceRegistry
from app.agent.memory_nodes import (
    load_memory,
    memory_candidate_extractor,
    persist_memory,
    resolve_memory_intent,
)
from app.agent.nodes import (
    action_planner,
    classify_scenario,
    extract_fiu,
    knowledge_router,
    load_reference_context,
    normalize_input,
    relationship_analysis,
    response_generator,
    route_after_safety,
    safety_check,
    safety_finalize,
)
from app.agent.state import AgentState, initial_state
from app.llm.errors import LLMError, LLMStructuredOutputError

Node = Callable[[AgentState], dict[str, object]]
AsyncNode = Callable[[AgentState], Awaitable[dict[str, object]]]

NODE_READS: dict[str, frozenset[str]] = {
    "normalize_input": frozenset({"current_message"}),
    "load_memory": frozenset({"user_id", "relationship_id", "memory_enabled", "warnings"}),
    "safety_check": frozenset({"current_message", "messages"}),
    "classify_scenario": frozenset({"current_message", "messages", "safety"}),
    "extract_fiu": frozenset({"current_message", "messages", "scenario", "safety"}),
    "knowledge_router": frozenset({"current_message", "safety", "route", "scenario"}),
    "load_references": frozenset({"selected_references"}),
    "relationship_analysis": frozenset(
        {
            "current_message",
            "scenario",
            "safety",
            "route",
            "facts",
            "inferences",
            "unknowns",
            "retrieved_context",
            "loaded_memories",
            "user_profile",
            "relationship_profile",
        }
    ),
    "action_planner": frozenset(
        {
            "current_message",
            "scenario",
            "route",
            "facts",
            "inferences",
            "unknowns",
            "selected_references",
            "analysis_result",
            "user_profile",
            "relationship_profile",
        }
    ),
    "response_generator": frozenset(
        {
            "current_message",
            "scenario",
            "route",
            "facts",
            "inferences",
            "unknowns",
            "analysis_result",
            "action_plan",
        }
    ),
    "safety_finalize": frozenset({"safety", "route"}),
    "memory_intent_resolver": frozenset(
        {
            "current_message",
            "user_id",
            "relationship_id",
            "memory_enabled",
            "memory_control",
            "route",
            "warnings",
        }
    ),
    "memory_candidate_extractor": frozenset(
        {"current_message", "facts", "memory_intent", "memory_control", "user_id", "warnings"}
    ),
    "memory_persist": frozenset(
        {
            "user_id",
            "relationship_id",
            "run_id",
            "memory_enabled",
            "memory_intent",
            "memory_candidates",
            "memory_receipt",
            "facts",
            "current_message",
            "warnings",
        }
    ),
}
NODE_WRITES: dict[str, frozenset[str]] = {
    "normalize_input": frozenset({"current_message"}),
    "load_memory": frozenset({"loaded_memories", "memory_control", "warnings"}),
    "safety_check": frozenset({"safety", "route"}),
    "classify_scenario": frozenset({"scenario"}),
    "extract_fiu": frozenset({"facts", "inferences", "unknowns"}),
    "knowledge_router": frozenset({"knowledge_route", "selected_references"}),
    "load_references": frozenset({"retrieved_context"}),
    "relationship_analysis": frozenset({"analysis_result"}),
    "action_planner": frozenset({"action_plan"}),
    "response_generator": frozenset({"final_answer"}),
    "safety_finalize": frozenset({"scenario", "final_answer"}),
    "memory_intent_resolver": frozenset({"memory_intent", "warnings"}),
    "memory_candidate_extractor": frozenset({"memory_candidates", "memory_receipt", "warnings"}),
    "memory_persist": frozenset({"memory_receipt", "warnings"}),
}


def _view(state: AgentState, name: str) -> AgentState:
    """Give each node only its declared read fields, including at runtime."""
    return AgentState(**{key: state[key] for key in NODE_READS[name]})


def _check_update(name: str, update: dict[str, object]) -> dict[str, object]:
    if set(update) != NODE_WRITES[name]:
        raise RuntimeError("node returned fields outside its declared update")
    return update


def _bind(name: str, node: Node) -> Node:
    def guarded(state: AgentState) -> dict[str, object]:
        return _check_update(name, node(_view(state, name)))

    return guarded


def _bind_async(name: str, node: AsyncNode) -> AsyncNode:
    async def guarded(state: AgentState) -> dict[str, object]:
        return _check_update(name, await node(_view(state, name)))

    return guarded


def compile_graph(dependencies: RuntimeDependencies) -> CompiledStateGraph:
    registry = dependencies.reference_registry or ReferenceRegistry()
    builder = StateGraph(AgentState)
    builder.add_node("normalize_input", _bind("normalize_input", normalize_input))
    builder.add_node(
        "load_memory", _bind("load_memory", lambda state: load_memory(state, dependencies))
    )

    async def check_safety(state: AgentState) -> dict[str, object]:
        return await safety_check(state, dependencies)

    async def classify(state: AgentState) -> dict[str, object]:
        return await classify_scenario(state, dependencies)

    async def extract(state: AgentState) -> dict[str, object]:
        return await extract_fiu(state, dependencies)

    async def analyze(state: AgentState) -> dict[str, object]:
        return await relationship_analysis(state, dependencies)

    async def plan(state: AgentState) -> dict[str, object]:
        return await action_planner(state, dependencies)

    async def respond(state: AgentState) -> dict[str, object]:
        return await response_generator(state, dependencies)

    async def extract_memory(state: AgentState) -> dict[str, object]:
        return await memory_candidate_extractor(state, dependencies)

    builder.add_node("safety_check", _bind_async("safety_check", check_safety))
    builder.add_node("classify_scenario", _bind_async("classify_scenario", classify))
    builder.add_node("extract_fiu", _bind_async("extract_fiu", extract))
    builder.add_node("relationship_analysis", _bind_async("relationship_analysis", analyze))
    builder.add_node("action_planner", _bind_async("action_planner", plan))
    builder.add_node("response_generator", _bind_async("response_generator", respond))
    builder.add_node(
        "memory_intent_resolver",
        _bind("memory_intent_resolver", lambda state: resolve_memory_intent(state, dependencies)),
    )
    builder.add_node(
        "memory_candidate_extractor", _bind_async("memory_candidate_extractor", extract_memory)
    )
    builder.add_node(
        "memory_persist", _bind("memory_persist", lambda state: persist_memory(state, dependencies))
    )
    builder.add_node(
        "knowledge_router",
        _bind(
            "knowledge_router",
            lambda state: knowledge_router(state, registry, dependencies.context_budget),
        ),
    )
    builder.add_node(
        "load_references",
        _bind(
            "load_references",
            lambda state: load_reference_context(state, registry, dependencies.context_budget),
        ),
    )
    builder.add_node("safety_finalize", _bind("safety_finalize", safety_finalize))
    builder.add_edge(START, "normalize_input")
    builder.add_edge("normalize_input", "load_memory")
    builder.add_edge("load_memory", "safety_check")
    builder.add_conditional_edges(
        "safety_check",
        route_after_safety,
        {"ordinary": "classify_scenario", "safety": "knowledge_router"},
    )
    builder.add_edge("classify_scenario", "extract_fiu")
    builder.add_edge("extract_fiu", "knowledge_router")
    builder.add_edge("knowledge_router", "load_references")
    builder.add_conditional_edges(
        "load_references",
        route_after_safety,
        {"ordinary": "relationship_analysis", "safety": "safety_finalize"},
    )
    builder.add_edge("relationship_analysis", "action_planner")
    builder.add_edge("action_planner", "response_generator")
    builder.add_edge("response_generator", "memory_intent_resolver")
    builder.add_edge("memory_intent_resolver", "memory_candidate_extractor")
    builder.add_edge("memory_candidate_extractor", "memory_persist")
    builder.add_edge("memory_persist", END)
    builder.add_edge("safety_finalize", END)
    return builder.compile()


class AgentRuntime:
    def __init__(self, *, dependencies: RuntimeDependencies) -> None:
        self._graph = compile_graph(dependencies)

    @property
    def graph(self) -> CompiledStateGraph:
        return self._graph

    async def run(self, request: AgentInput) -> AgentResult | AgentFailure:
        if not isinstance(request, AgentInput):
            return AgentFailure(
                run_id=uuid4(),
                code=AgentErrorCode.INVALID_INPUT,
                message="Agent input is invalid",
            )
        try:
            request = AgentInput.model_validate_json(request.model_dump_json())
        except Exception:
            return AgentFailure(
                run_id=uuid4(),
                code=AgentErrorCode.INVALID_INPUT,
                message="Agent input is invalid",
            )
        state = initial_state(request)
        run_id = state["run_id"]
        state["run_status"] = AgentRunStatus.RUNNING
        try:
            output: AgentState = await self._graph.ainvoke(state)
            if output["run_id"] != run_id:
                raise RuntimeError("graph changed run identity")
            output["run_status"] = AgentRunStatus.COMPLETED
            return AgentResult(
                run_id=run_id,
                status=output["run_status"],
                scenario=output["scenario"],
                safety=output["safety"],
                route=output["route"],
                evidence=FactExtractionResult(
                    facts=output["facts"],
                    inferences=output["inferences"],
                    unknowns=output["unknowns"],
                ),
                knowledge=output["knowledge_route"],
                analysis=output["analysis_result"],
                action=output["action_plan"],
                memory_intent=output["memory_intent"],
                memory_candidates=output["memory_candidates"],
                memory_receipt=output["memory_receipt"],
                final_answer=output["final_answer"],
                warnings=output["warnings"],
            )
        except LLMStructuredOutputError:
            code = AgentErrorCode.STRUCTURED_OUTPUT_FAILURE
        except LLMError:
            code = AgentErrorCode.DEPENDENCY_FAILURE
        except AgentError as exc:
            code = exc.code
        except Exception:
            code = AgentErrorCode.RUNTIME_FAILURE
        state["run_status"] = AgentRunStatus.FAILED
        return AgentFailure(run_id=run_id, code=code, message="Agent run failed")
