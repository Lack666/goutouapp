"""Keyless public Agent event demo, without API transport or private dumps."""

import asyncio
import json
import sys
from uuid import uuid4

from agent_demo import CaptureMock, queue_run

from app.agent import AgentInput
from app.agent.dependencies import RuntimeDependencies
from app.agent.events import CompletedEvent, FailedEvent, MemoryStatusEvent, StatusEvent
from app.agent.memory import InMemoryMemoryStore, MemoryService
from app.agent.runtime import AgentRuntime


async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    user_id, person_id, relationship_id = uuid4(), uuid4(), uuid4()
    store = InMemoryMemoryStore()
    store.bind_relationship(user_id, relationship_id, person_id)
    provider = CaptureMock()
    queue_run(provider, first=True, person_id=person_id)
    runtime = AgentRuntime(
        dependencies=RuntimeDependencies(llm_provider=provider, memory_service=MemoryService(store))
    )
    event_types = []
    statuses = []
    memory_status = None
    completed = None
    async for event in runtime.stream(
        AgentInput(
            user_id=user_id,
            conversation_id=uuid4(),
            relationship_id=relationship_id,
            memory_enabled=True,
            message="关于对象A：我们已确认关系。我明确同意把这项稳定信息存入长期关系档案。",
        )
    ):
        event_types.append(event.type)
        if isinstance(event, StatusEvent):
            statuses.append(event.status)
        elif isinstance(event, MemoryStatusEvent):
            memory_status = event.receipt.status
        elif isinstance(event, CompletedEvent):
            completed = event.result
        elif isinstance(event, FailedEvent):
            raise RuntimeError("Standalone stream demo failed")
    if completed is None or completed.memory_receipt.saved_count != 1:
        raise RuntimeError("Standalone stream demo did not persist memory")
    print(
        json.dumps(
            {
                "event_types": event_types,
                "progress_statuses": statuses,
                "memory_status": memory_status,
                "completed": completed.status.value,
                "single_persistent_write": len(store.records) == 1,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
