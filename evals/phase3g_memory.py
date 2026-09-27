"""Golden-derived Phase 3G replay; asserts actual in-memory writes."""

import asyncio
from uuid import uuid4

from app.agent import AgentInput, AgentResult
from app.agent.contracts import MemoryDecision, MemoryWriteStatus
from app.agent.dependencies import RuntimeDependencies
from app.agent.memory import InMemoryMemoryStore, MemoryService
from app.agent.runtime import AgentRuntime
from app.llm.mock import MockLLMProvider
from evals.phase3c_semantic import CASES, replay_outputs
from evals.phase3e_analysis import fixture_analysis
from evals.phase3f_action_response import fixture_action, fixture_response

SELECTED = (
    "pair_d1",
    "pair_d2",
    "memory_01",
    "memory_02",
    "memory_03",
    "memory_04",
    "memory_05",
    "memory_06",
    "memory_resume_01",
    "memory_revoke_01",
    "memory_delete_all_01",
    "memory_sensitive_01",
    "memory_delete_item_01",
    "pair_b2",
)


def run_memory_case(case_id: str) -> tuple[AgentResult, MemoryService, object, object]:
    case = CASES[case_id]
    user_id, person_id, relationship_id = uuid4(), uuid4(), uuid4()
    store = InMemoryMemoryStore()
    store.bind_relationship(user_id, relationship_id, person_id)
    service = MemoryService(store)
    if case_id in {
        "memory_03",
        "memory_resume_01",
        "memory_revoke_01",
        "memory_04",
        "memory_05",
        "memory_delete_all_01",
        "memory_delete_item_01",
    }:
        service.grant_consent(user_id, confirmed=True)
    if case_id == "memory_resume_01":
        service.apply_control(user_id, MemoryDecision.PAUSE)
    outputs = replay_outputs(case)
    if case_id in {"pair_d1", "memory_02"}:
        phrase = "我们已确认关系" if case_id == "pair_d1" else "我们已经确认关系"
        outputs[2]["facts"] = [{"statement": phrase, "source": "user_explicit"}]
    provider = MockLLMProvider()
    for output in outputs:
        provider.queue_structured(output)
    expected = case["expected"]
    if expected["route"] != "safety":
        provider.queue_structured(
            fixture_analysis(
                alias=expected["knowledge"]["required_any"][0],
                fiu=outputs[2],
                route=expected["route"],
                assertions=expected["assertions"],
            )
        )
        action = fixture_action(
            scenario=expected["scenario"],
            route=expected["route"],
            assertions=expected["assertions"],
        )
        provider.queue_structured(action)
        provider.queue_structured(fixture_response(action))
        if expected["memory_writes"]:
            phrase = "我们已确认关系" if case_id == "pair_d1" else "我们已经确认关系"
            provider.queue_structured(
                {
                    "candidates": [
                        {
                            "subject_id": str(person_id),
                            "type": "relationship",
                            "content": phrase,
                            "source": "user_explicit",
                            "evidence": "F1",
                        }
                    ]
                }
            )
    result = asyncio.run(
        AgentRuntime(
            dependencies=RuntimeDependencies(llm_provider=provider, memory_service=service)
        ).run(
            AgentInput(
                user_id=user_id,
                conversation_id=uuid4(),
                relationship_id=relationship_id,
                message=case["input"],
                memory_enabled=True,
            )
        )
    )
    if not isinstance(result, AgentResult):
        raise AssertionError(f"{case_id}: runtime failure")
    return result, service, user_id, person_id


def evaluate_memory(
    case_id: str, result: AgentResult, service: MemoryService, user_id
) -> list[str]:
    expected = CASES[case_id]["expected"]
    errors = []
    if (
        result.scenario.primary.value != expected["scenario"]
        or result.route.value != expected["route"]
    ):
        errors.append("semantic_route")
    expected_decision = expected.get("memory", {}).get("decision", "no_write")
    if result.memory_intent.decision != MemoryDecision(expected_decision):
        errors.append("memory_intent")
    if result.memory_receipt.saved_count != expected["memory_writes"]:
        errors.append("receipt_write_count")
    if len(service.list_for_user(user_id)) != expected["memory_writes"]:
        errors.append("persistent_write_count")
    if expected["memory_writes"] == 0 and result.memory_receipt.status == MemoryWriteStatus.SAVED:
        errors.append("false_saved_status")
    if expected["memory_writes"] and not all(
        item.evidence.startswith("F") for item in result.memory_candidates
    ):
        errors.append("candidate_grounding")
    if "聊天记录" in " ".join(item.content for item in service.list_for_user(user_id)):
        errors.append("raw_chat_memory")
    return errors
