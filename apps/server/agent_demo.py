"""Keyless, network-free standalone graph demo. Run from the repository root."""

import asyncio
from uuid import uuid4

from app.agent import AgentInput
from app.agent.dependencies import RuntimeDependencies
from app.agent.runtime import AgentRuntime
from app.llm.mock import MockLLMProvider


async def main() -> None:
    provider = MockLLMProvider()
    provider.queue_structured({"risk_level": "normal", "safety_route_required": False})
    provider.queue_structured(
        {
            "primary": "relationship",
            "confidence": 0.5,
            "reason_summary": "The user asks about a relationship",
        }
    )
    provider.queue_structured(
        {
            "facts": [{"statement": "The user asks a synthetic question", "source": "user_report"}],
            "inferences": [],
            "unknowns": [{"statement": "The underlying relationship context"}],
        }
    )
    runtime = AgentRuntime(dependencies=RuntimeDependencies(llm_provider=provider))
    result = await runtime.run(
        AgentInput(
            user_id=uuid4(),
            conversation_id=uuid4(),
            message="Synthetic ordinary relationship question",
        )
    )
    print(result.model_dump_json())


if __name__ == "__main__":
    asyncio.run(main())
