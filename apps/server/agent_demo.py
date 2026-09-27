"""Keyless, network-free standalone graph demo. Run from the repository root."""

import asyncio
import json
from uuid import uuid4

from app.agent import AgentInput
from app.agent.contracts import AgentResult
from app.agent.dependencies import RuntimeDependencies
from app.agent.runtime import AgentRuntime
from app.llm.mock import MockLLMProvider


async def main() -> None:
    provider = MockLLMProvider()
    provider.queue_structured({"risk_level": "normal", "safety_route_required": False})
    provider.queue_structured(
        {
            "primary": "reply",
            "confidence": 0.5,
            "reason_summary": "The user asks for reply wording",
        }
    )
    provider.queue_structured(
        {
            "facts": [{"statement": "The user asks a synthetic question", "source": "user_report"}],
            "inferences": [],
            "unknowns": [{"statement": "The underlying relationship context"}],
        }
    )
    provider.queue_structured(
        {
            "core_issue": "The synthetic request lacks relationship context",
            "core_evidence_ids": ["F1"],
            "core_reference_ids": ["reply"],
            "insufficient_evidence": True,
            "observations": [
                {
                    "statement": "The user asks a synthetic question",
                    "kind": "observed",
                    "dimension": "evidence_quality",
                    "evidence_ids": ["F1"],
                }
            ],
            "uncertainties": [
                {
                    "statement": "The underlying relationship context is unknown",
                    "kind": "uncertainty",
                    "dimension": "evidence_quality",
                    "evidence_ids": ["U1"],
                }
            ],
            "constraints": [
                {
                    "statement": "The selected reference is general wording guidance",
                    "kind": "framework",
                    "dimension": "communication",
                    "reference_ids": ["reply"],
                }
            ],
        }
    )
    runtime = AgentRuntime(dependencies=RuntimeDependencies(llm_provider=provider))
    result = await runtime.run(
        AgentInput(
            user_id=uuid4(),
            conversation_id=uuid4(),
            message="Synthetic ordinary reply question",
        )
    )
    if not isinstance(result, AgentResult) or result.knowledge is None or result.analysis is None:
        raise RuntimeError("Standalone knowledge demo failed")
    print(
        json.dumps(
            {
                "status": result.status,
                "scenario": result.scenario.primary,
                "route": result.route,
                "selected_references": result.knowledge.selected_references,
                "evidence": result.evidence.model_dump(mode="json"),
                "analysis": result.analysis.model_dump(mode="json"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
