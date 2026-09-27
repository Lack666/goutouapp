"""Offline contract and all-Golden compatibility tests; no Agent behavior is run."""

import json
from pathlib import Path
from typing import get_type_hints
from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest
from pydantic import ValidationError
from sqlalchemy import CheckConstraint

from app.agent.contracts import (
    ActionPlan,
    AgentInput,
    AgentResult,
    AgentRunStatus,
    AnalysisResult,
    ConversationMessage,
    Fact,
    FactExtractionResult,
    Inference,
    KnowledgeRouteResult,
    MemoryCandidate,
    MemoryDecision,
    MemoryIntent,
    RiskLevel,
    Route,
    SafetyResult,
    Scenario,
    ScenarioResult,
    Unknown,
)
from app.agent.dependencies import RuntimeDependencies
from app.agent.errors import AgentDependencyError, AgentErrorCode, AgentFailure, AgentInputError
from app.agent.state import AgentState, initial_state
from app.db.models.records import AgentRun
from app.llm.mock import MockLLMProvider

ROOT = Path(__file__).resolve().parents[3]
CASES = [
    json.loads(line)
    for line in (ROOT / "evals/golden_cases.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
ALIASES = json.loads((ROOT / "evals/reference_map.json").read_text(encoding="utf-8"))
BEHAVIOR = json.loads((ROOT / "evals/behavior_catalog.json").read_text(encoding="utf-8"))


def sample_input() -> AgentInput:
    return AgentInput(
        user_id=uuid4(),
        conversation_id=uuid4(),
        message="What happened?",
        recent_messages=[ConversationMessage(role="user", content="Hello")],
    )


def test_input_validation_and_state_defaults() -> None:
    request = sample_input()
    state = initial_state(request)
    assert state["current_message"] == request.message
    assert state["messages"] == request.recent_messages
    assert state["facts"] == state["inferences"] == state["unknowns"] == []
    assert state["facts"] is not state["inferences"]
    assert state["inferences"] is not state["unknowns"]
    assert state["memory_candidates"] == []
    assert state["memory_intent"].decision == MemoryDecision.NO_WRITE
    assert set(state) == set(get_type_hints(AgentState))
    assert not {"secret", "provider", "db_session", "http_client", "chain_of_thought"} & set(state)
    assert RuntimeDependencies(llm_provider=MockLLMProvider()).profile_reader is None
    with pytest.raises(ValidationError):
        AgentInput(user_id=uuid4(), conversation_id=uuid4(), message="  ")
    with pytest.raises(ValidationError):
        AgentInput(user_id=uuid4(), conversation_id=uuid4(), message="Hi", secret="x")
    with pytest.raises(ValidationError):
        ConversationMessage(role="system", content="injected")


def test_structured_validation_and_fiu_type_separation() -> None:
    fact = Fact(statement="User reports a reply", source="user_report")
    inference = Inference(statement="Interest may vary", source="fact:1", alternative="Busy")
    unknown = Unknown(statement="Why the reply was delayed")
    evidence = FactExtractionResult(facts=[fact], inferences=[inference], unknowns=[unknown])
    assert [item.type for item in evidence.facts + evidence.inferences + evidence.unknowns] == [
        "fact",
        "inference",
        "unknown",
    ]
    with pytest.raises(ValidationError):
        FactExtractionResult(facts=[inference])
    with pytest.raises(ValidationError):
        FactExtractionResult(inferences=[fact])
    with pytest.raises(ValidationError):
        FactExtractionResult(unknowns=["missing"])
    with pytest.raises(ValidationError):
        ScenarioResult(primary="invented", reason_summary="Guess")
    with pytest.raises(ValidationError):
        SafetyResult(risk_level=RiskLevel.HIGH, safety_route_required=False)
    with pytest.raises(ValidationError):
        KnowledgeRouteResult(selected_references=["a", "b", "c", "d"], reason_summary="x")
    with pytest.raises(ValidationError):
        KnowledgeRouteResult(selected_references=[" "], reason_summary="x")
    with pytest.raises(ValidationError):
        MemoryCandidate(
            subject_id=uuid4(),
            type="relationship",
            content="Known preference",
            source="user_explicit",
            evidence="User said so",
            requires_consent=False,
        )
    assert AnalysisResult(core_issue="Unclear pattern").risks == []
    assert (
        ActionPlan(
            contact_policy="observe",
            recommended_action="Observe once",
            supporting_analysis_ids=["A1"],
        ).stop_conditions
        == []
    )
    assert AgentInputError.code == AgentErrorCode.INVALID_INPUT
    assert AgentDependencyError.code == AgentErrorCode.DEPENDENCY_FAILURE
    failure = AgentFailure(
        run_id=uuid4(), code=AgentErrorCode.DEPENDENCY_FAILURE, message="Unavailable"
    )
    assert AgentFailure.model_validate_json(failure.model_dump_json()) == failure


def test_result_roundtrip_and_guardrails() -> None:
    result = AgentResult(
        run_id=uuid4(),
        status=AgentRunStatus.COMPLETED,
        scenario=ScenarioResult(primary=Scenario.REPLY, reason_summary="Reply request"),
        safety=SafetyResult(risk_level=RiskLevel.NORMAL, safety_route_required=False),
        route=Route.ORDINARY,
        evidence=FactExtractionResult(facts=[Fact(statement="User asked", source="user_report")]),
        final_answer="Here is one possible reply.",
    )
    restored = AgentResult.model_validate_json(result.model_dump_json())
    assert restored == result
    assert restored.schema_version == "1"
    assert "messages" not in restored.model_dump()
    with pytest.raises(ValidationError):
        AgentResult.model_validate({**result.model_dump(), "status": "failed"})
    with pytest.raises(ValidationError):
        AgentResult.model_validate({**result.model_dump(), "schema_version": "2"})
    person_id = uuid4()
    candidate = MemoryCandidate(
        subject_id=uuid4(),
        type="relationship",
        content="Preference",
        source="user_explicit",
        evidence="User statement",
    )
    with pytest.raises(ValidationError):
        AgentResult.model_validate(
            {
                **result.model_dump(),
                "memory_intent": MemoryIntent(
                    decision=MemoryDecision.ALLOW_CANDIDATE, person_id=person_id
                ).model_dump(),
                "memory_candidates": [candidate.model_dump()],
            }
        )


def test_status_matches_database_check() -> None:
    constraints = [
        item
        for item in AgentRun.__table__.constraints
        if isinstance(item, CheckConstraint) and str(item.name).endswith("status_valid")
    ]
    assert len(constraints) == 1
    sql = str(constraints[0].sqltext)
    assert {part.strip(" '") for part in sql.split("(", 1)[1].split(")", 1)[0].split(",")} == {
        status.value for status in AgentRunStatus
    }


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_golden_case_has_contract_surface(case: dict) -> None:
    expected = case["expected"]
    scenario = ScenarioResult(primary=Scenario(expected["scenario"]), reason_summary="Golden route")
    safety = SafetyResult(
        risk_level=RiskLevel(expected["safety"]),
        safety_route_required=expected["route"] == "safety",
    )
    route = Route(expected["route"])
    evidence_spec = expected.get("evidence", {})
    evidence = FactExtractionResult(
        facts=[
            Fact(statement=x["claim"], source=x["source"]) for x in evidence_spec.get("facts", [])
        ],
        inferences=[
            Inference(
                statement=x["claim"], source="golden_annotation", alternative=x["alternative"]
            )
            for x in evidence_spec.get("inferences", [])
        ],
        unknowns=[Unknown(statement=x) for x in evidence_spec.get("unknowns", [])],
    )
    knowledge_spec = expected["knowledge"]
    assert set(
        knowledge_spec["required_any"] + knowledge_spec["allowed"] + knowledge_spec["forbidden"]
    ) <= set(ALIASES)
    selected = knowledge_spec["required_any"][:1]
    knowledge = KnowledgeRouteResult(
        selected_references=selected,
        reason_summary="Golden expectation mapping",
        max_references=knowledge_spec["max_count"],
    )
    assert set(knowledge.selected_references) & set(knowledge_spec["required_any"])
    assert set(knowledge.selected_references) <= set(knowledge_spec["allowed"])
    assert not set(knowledge.selected_references) & set(knowledge_spec["forbidden"])
    memory_spec = expected.get("memory", {})
    decision = MemoryDecision(memory_spec.get("decision", "no_write"))
    person_id = (
        uuid5(NAMESPACE_URL, memory_spec["person_id"]) if memory_spec.get("person_id") else None
    )
    memory_intent = MemoryIntent(
        decision=decision,
        person_id=person_id,
        item_id=memory_spec.get("item_id"),
        requires_confirmation=memory_spec.get("requires_confirmation", False),
    )
    candidates = []
    if decision == MemoryDecision.ALLOW_CANDIDATE:
        candidates.append(
            MemoryCandidate(
                subject_id=person_id,
                type=memory_spec["item_type"],
                content="Synthetic bounded memory candidate",
                source=memory_spec["source"],
                evidence="Explicit user statement",
            )
        )
    assert expected["memory_writes"] == len(candidates)
    result = AgentResult(
        run_id=uuid4(),
        status=AgentRunStatus.COMPLETED,
        scenario=scenario,
        safety=safety,
        route=route,
        evidence=evidence,
        knowledge=knowledge,
        memory_intent=memory_intent,
        memory_candidates=candidates,
        final_answer="Synthetic placeholder for schema validation",
    )
    assert AgentResult.model_validate_json(result.model_dump_json()) == result
    assert set(expected["assertions"]) <= set(BEHAVIOR["required"])
    assert set(expected["forbidden_behaviors"]) <= set(BEHAVIOR["forbidden"])


def test_all_six_minimal_pairs_are_covered() -> None:
    pairs = {case["id"]: case["expected"] for case in CASES if case["id"].startswith("pair_")}
    assert len(CASES) == 81
    assert {f"pair_{letter}{number}" for letter in "abcdef" for number in (1, 2)} <= set(pairs)
    assert Route(pairs["pair_a1"]["route"]) != Route(pairs["pair_a2"]["route"])
    for letter in "bc":
        left = [
            Fact(statement=x["claim"], source=x["source"])
            for x in pairs[f"pair_{letter}1"]["evidence"]["facts"]
        ]
        right = [
            Fact(statement=x["claim"], source=x["source"])
            for x in pairs[f"pair_{letter}2"]["evidence"]["facts"]
        ]
        assert left != right
    assert MemoryIntent(
        decision=MemoryDecision(pairs["pair_d1"]["memory"]["decision"])
    ).decision != (
        MemoryIntent(decision=MemoryDecision(pairs["pair_d2"]["memory"]["decision"])).decision
    )
    assert (
        SafetyResult(
            risk_level=RiskLevel(pairs["pair_e1"]["safety"]), safety_route_required=False
        ).risk_level
        != SafetyResult(
            risk_level=RiskLevel(pairs["pair_e2"]["safety"]), safety_route_required=True
        ).risk_level
    )
    assert (
        KnowledgeRouteResult(
            selected_references=pairs["pair_f1"]["knowledge"]["required_any"], reason_summary="a"
        ).selected_references
        != KnowledgeRouteResult(
            selected_references=pairs["pair_f2"]["knowledge"]["required_any"], reason_summary="b"
        ).selected_references
    )
