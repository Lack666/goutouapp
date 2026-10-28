"""Keyless two-conversation memory demo with the standalone Agent runtime."""

import asyncio
import json
import sys
from uuid import uuid4

from app.agent import AgentInput
from app.agent.contracts import ActionPlan, AgentResult, ResponseResult
from app.agent.dependencies import RuntimeDependencies
from app.agent.memory import InMemoryMemoryStore, MemoryService
from app.agent.runtime import AgentRuntime
from app.llm.mock import MockLLMProvider
from evals.agent.content_safety_eval import queue_safe_fixture_review


class CaptureMock(MockLLMProvider):
    def __init__(self) -> None:
        super().__init__()
        self.analysis_payloads: list[dict] = []

    async def structured_output(self, messages, schema, **kwargs):
        if schema.__name__ == "AnalysisResult":
            self.analysis_payloads.append(json.loads(messages[1].content))
        return await super().structured_output(messages, schema, **kwargs)


def queue_run(provider: CaptureMock, *, first: bool, person_id) -> None:
    scenario = "memory" if first else "relationship"
    alias = scenario
    provider.queue_structured({"risk_level": "normal", "safety_route_required": False})
    provider.queue_structured({"primary": scenario, "reason_summary": "Synthetic demo"})
    provider.queue_structured(
        {
            "facts": [{"statement": "我们已确认关系", "source": "user_explicit"}] if first else [],
            "inferences": [],
            "unknowns": [],
        }
    )
    analysis = {
        "core_issue": "Only source-limited relationship context is available",
        "core_reference_ids": [alias],
        "insufficient_evidence": not first,
        "constraints": [
            {
                "statement": "The reference is general context, not a case fact",
                "kind": "framework",
                "dimension": "evidence_quality",
                "reference_ids": [alias],
            }
        ],
    }
    if first:
        analysis["core_evidence_ids"] = ["F1"]
        analysis["observations"] = [
            {
                "statement": "我们已确认关系",
                "kind": "observed",
                "dimension": "communication",
                "evidence_ids": ["F1"],
            }
        ]
    provider.queue_structured(analysis)
    action = {
        "contact_policy": "observe",
        "recommended_action": "观察接下来双方的真实互动，再决定是否调整投入。",
        "supporting_analysis_ids": ["A1"],
        "observation_window": "接下来的两次自然互动。",
        "stop_conditions": ["出现明确拒绝时停止推进。"],
    }
    provider.queue_structured(action)
    queue_safe_fixture_review(provider, ActionPlan.model_validate(action))
    response = {
        "contact_policy": "observe",
        "final_answer": action["recommended_action"] + "旧信息可能变化，请结合现在的情况判断。",
    }
    provider.queue_structured(response)
    queue_safe_fixture_review(provider, ResponseResult.model_validate(response))
    if first:
        provider.queue_structured(
            {
                "candidates": [
                    {
                        "subject_id": str(person_id),
                        "type": "relationship",
                        "content": "我们已确认关系",
                        "source": "user_explicit",
                        "evidence": "F1",
                    }
                ]
            }
        )


async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    user_id, person_id, relationship_id = uuid4(), uuid4(), uuid4()
    first_conversation, second_conversation = uuid4(), uuid4()
    store = InMemoryMemoryStore()
    store.bind_relationship(user_id, relationship_id, person_id)
    service = MemoryService(store)
    provider = CaptureMock()
    queue_run(provider, first=True, person_id=person_id)
    queue_run(provider, first=False, person_id=person_id)
    runtime = AgentRuntime(
        dependencies=RuntimeDependencies(llm_provider=provider, memory_service=service)
    )
    first = await runtime.run(
        AgentInput(
            user_id=user_id,
            conversation_id=first_conversation,
            relationship_id=relationship_id,
            memory_enabled=True,
            message="关于对象A：我们已确认关系。我明确同意把这项稳定信息存入长期关系档案。",
        )
    )
    second = await runtime.run(
        AgentInput(
            user_id=user_id,
            conversation_id=second_conversation,
            relationship_id=relationship_id,
            memory_enabled=True,
            message="请根据之前的关系背景分析现状。",
        )
    )
    if not isinstance(first, AgentResult) or not isinstance(second, AgentResult):
        raise RuntimeError("Standalone memory demo failed")
    historical_count = len(provider.analysis_payloads[1]["historical_memory"])
    if first.memory_receipt.saved_count != 1 or historical_count != 1:
        raise RuntimeError("Cross-conversation memory was not loaded")
    print(
        json.dumps(
            {
                "first_run_memory_status": first.memory_receipt.status,
                "first_run_saved_count": first.memory_receipt.saved_count,
                "new_conversation": first_conversation != second_conversation,
                "second_run_historical_memory_loaded": historical_count,
                "second_run_final_answer": second.final_answer,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
