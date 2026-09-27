"""Standalone graph architecture regression after semantic nodes replace fixtures."""

import ast
import asyncio
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.agent import AgentFailure, AgentInput, AgentResult, initial_state
from app.agent.contracts import AgentRunStatus, Route, Scenario
from app.agent.dependencies import RuntimeDependencies
from app.agent.errors import AgentErrorCode
from app.agent.knowledge import SCENARIO_ALIASES
from app.agent.nodes import normalize_input
from app.agent.runtime import NODE_READS, NODE_WRITES, AgentRuntime, _bind
from app.llm.errors import LLMUnavailableError
from app.llm.mock import MockLLMProvider

ROOT = Path(__file__).resolve().parents[3]


def run_async(function):
    def wrapper():
        asyncio.run(function())

    return wrapper


def request(message: str = "What is this relationship?", **metadata: str) -> AgentInput:
    return AgentInput(user_id=uuid4(), conversation_id=uuid4(), message=message, metadata=metadata)


def scripted_provider(*, high: bool = False, scenario: str = "relationship") -> MockLLMProvider:
    provider = MockLLMProvider()
    provider.queue_structured(
        {
            "risk_level": "high" if high else "normal",
            "risk_categories": ["violence"] if high else [],
            "safety_route_required": high,
        }
    )
    if not high:
        provider.queue_structured({"primary": scenario, "reason_summary": "Replay cue"})
        provider.queue_structured({"facts": [], "inferences": [], "unknowns": []})
        alias = SCENARIO_ALIASES[Scenario(scenario)]
        provider.queue_structured(
            {
                "core_issue": "The case details are insufficient",
                "core_reference_ids": [alias],
                "insufficient_evidence": True,
                "constraints": [
                    {
                        "statement": "The source offers a lens, not a case fact",
                        "kind": "framework",
                        "dimension": "evidence_quality",
                        "reference_ids": [alias],
                    }
                ],
            }
        )
    return provider


def runtime(provider: MockLLMProvider | None = None) -> AgentRuntime:
    return AgentRuntime(
        dependencies=RuntimeDependencies(llm_provider=provider or scripted_provider())
    )


def test_scoped_nodes_and_runtime_wrapper() -> None:
    assert set(NODE_READS) == set(NODE_WRITES)
    assert normalize_input({"current_message": "  hello "}) == {"current_message": "hello"}
    assert NODE_WRITES["safety_check"] == {"safety", "route"}
    assert NODE_WRITES["classify_scenario"] == {"scenario"}
    assert NODE_WRITES["extract_fiu"] == {"facts", "inferences", "unknowns"}
    assert NODE_WRITES["relationship_analysis"] == {"analysis_result"}
    assert not {"action_plan", "memory_candidates"} & set().union(*NODE_WRITES.values())

    def bad_read(state):
        return {"current_message": state["facts"]}

    with pytest.raises(KeyError):
        _bind("normalize_input", bad_read)(initial_state(request()))

    def bad_write(state):
        return {"facts": [], "current_message": state["current_message"]}

    with pytest.raises(RuntimeError, match="outside its declared update"):
        _bind("normalize_input", bad_write)(initial_state(request()))


def test_graph_conditional_structure() -> None:
    graph = runtime().graph.get_graph()
    assert {
        "normalize_input",
        "safety_check",
        "classify_scenario",
        "extract_fiu",
        "relationship_analysis",
        "knowledge_router",
        "load_references",
        "minimal_finalize",
        "safety_finalize",
        "__start__",
        "__end__",
    } <= set(graph.nodes)
    edges = {(edge.source, edge.target, edge.conditional) for edge in graph.edges}
    assert ("__start__", "normalize_input", False) in edges
    assert ("normalize_input", "safety_check", False) in edges
    assert ("safety_check", "classify_scenario", True) in edges
    assert ("safety_check", "knowledge_router", True) in edges
    assert ("classify_scenario", "extract_fiu", False) in edges
    assert ("extract_fiu", "knowledge_router", False) in edges
    assert ("knowledge_router", "load_references", False) in edges
    assert ("load_references", "relationship_analysis", True) in edges
    assert ("load_references", "safety_finalize", True) in edges
    assert ("relationship_analysis", "minimal_finalize", False) in edges
    assert ("minimal_finalize", "__end__", False) in edges
    assert ("safety_finalize", "__end__", False) in edges


def test_no_database_transport_or_vendor_import_in_agent() -> None:
    agent_dir = ROOT / "apps/server/app/agent"
    forbidden = ("app.db", "app.api", "app.main", "fastapi", "sqlalchemy", "openai")
    for path in agent_dir.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = [
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        ]
        imports += [
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        ]
        assert not any(name.startswith(forbidden) for name in imports), path


@run_async
async def test_success_status_json_and_no_internal_state() -> None:
    agent = runtime()
    compiled = agent.graph
    assert initial_state(request())["run_status"] == AgentRunStatus.PENDING

    class InspectingGraph:
        async def ainvoke(self, state):
            self.run_id = state["run_id"]
            assert state["run_status"] == AgentRunStatus.RUNNING
            return await compiled.ainvoke(state)

    inspecting = InspectingGraph()
    agent._graph = inspecting
    result = await agent.run(request())
    assert isinstance(result, AgentResult)
    assert result.run_id == inspecting.run_id
    assert result.status == AgentRunStatus.COMPLETED
    assert result.schema_version == "1"
    assert result.scenario.primary == Scenario.RELATIONSHIP
    assert result.analysis is not None
    assert result.action is None
    assert AgentResult.model_validate_json(result.model_dump_json()) == result
    assert "current_message" not in result.model_dump()


@run_async
async def test_safety_branch_skips_scenario_and_fiu() -> None:
    result = await runtime(scripted_provider(high=True)).run(request())
    assert isinstance(result, AgentResult)
    assert result.route == Route.SAFETY
    assert result.scenario.primary == Scenario.SAFETY
    assert result.evidence.facts == result.evidence.inferences == result.evidence.unknowns == []
    assert result.analysis is None


@run_async
async def test_failures_are_safe_and_correlated() -> None:
    provider = MockLLMProvider()
    provider.queue_error("structured_output", LLMUnavailableError())
    failed = await runtime(provider).run(request())
    assert isinstance(failed, AgentFailure)
    assert failed.code == AgentErrorCode.DEPENDENCY_FAILURE
    assert failed.status == AgentRunStatus.FAILED
    provider = MockLLMProvider()
    provider.queue_structured({"risk_level": "invented"})
    malformed = await runtime(provider).run(request())
    assert isinstance(malformed, AgentFailure)
    assert malformed.code == AgentErrorCode.STRUCTURED_OUTPUT_FAILURE
    assert AgentFailure.model_validate_json(malformed.model_dump_json()) == malformed

    with patch("app.agent.runtime.minimal_finalize", side_effect=RuntimeError("API_KEY=private")):
        unexpected = await runtime().run(request())
    assert isinstance(unexpected, AgentFailure)
    assert unexpected.code == AgentErrorCode.RUNTIME_FAILURE
    assert "private" not in unexpected.model_dump_json()
    invalid = await runtime().run(None)
    assert isinstance(invalid, AgentFailure)
    assert invalid.code == AgentErrorCode.INVALID_INPUT
    assert invalid.run_id != unexpected.run_id


@run_async
async def test_run_isolation_and_compile_reuse() -> None:
    first, second = await asyncio.gather(
        runtime(scripted_provider(scenario="reply")).run(request("reply")),
        runtime(scripted_provider(scenario="conflict")).run(request("conflict")),
    )
    assert isinstance(first, AgentResult) and isinstance(second, AgentResult)
    assert first.run_id != second.run_id
    assert first.scenario.primary == Scenario.REPLY
    assert second.scenario.primary == Scenario.CONFLICT
    assert first.evidence.facts is not second.evidence.facts
    provider = scripted_provider()
    provider.queue_structured({"risk_level": "normal", "safety_route_required": False})
    provider.queue_structured({"primary": "online", "reason_summary": "Replay cue"})
    provider.queue_structured({"facts": [], "inferences": [], "unknowns": []})
    provider.queue_structured(
        {
            "core_issue": "Case details are insufficient",
            "core_reference_ids": ["online"],
            "insufficient_evidence": True,
            "constraints": [
                {
                    "statement": "Source is general context only",
                    "kind": "framework",
                    "dimension": "evidence_quality",
                    "reference_ids": ["online"],
                }
            ],
        }
    )
    agent = runtime(provider)
    compiled = agent.graph
    third = await agent.run(request("third"))
    fourth = await agent.run(request("fourth"))
    assert isinstance(third, AgentResult) and isinstance(fourth, AgentResult)
    assert third.run_id != fourth.run_id
    assert agent.graph is compiled


@run_async
async def test_synthetic_metadata_no_longer_controls_safety() -> None:
    result = await runtime().run(request("ordinary", synthetic_safety_route="high"))
    assert isinstance(result, AgentResult)
    assert result.route == Route.ORDINARY
