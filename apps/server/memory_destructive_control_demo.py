"""Disposable PostgreSQL and MockLLM Phase 6B undo/deletion demonstration."""

import asyncio
import json
import sys
from uuid import uuid4

from memory_control_demo import create_scope, disposable_database, run_agent
from sqlalchemy.orm import Session

from app.agent.contracts import Fact, MemoryCandidate
from app.agent.memory import MemoryService
from app.db.repositories.memory import SQLAlchemyMemoryStore
from app.services.agent_service import actor_from_verified_identity
from app.services.memory_control import MemoryControlService
from app.services.memory_mutation import MemoryMutationService


def save(store, owner, person, relationship, content):
    return MemoryService(store).persist_candidates(
        user_id=owner,
        relationship_id=relationship,
        run_id=uuid4(),
        candidates=[
            MemoryCandidate(
                subject_id=person,
                type="relationship",
                content=content,
                source="user_explicit",
                evidence="F1",
            )
        ],
        facts=[Fact(statement=content, source="user_explicit")],
        message=f"我明确同意记住：{content}",
        explicit_consent=True,
    )


async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    with disposable_database() as engine:
        owner, person, relationship, conversation = create_scope(engine)
        actor = actor_from_verified_identity(owner)
        store = SQLAlchemyMemoryStore(lambda: Session(engine))
        controls = MemoryControlService(store)
        mutations = MemoryMutationService(lambda: Session(engine))
        controls.grant_consent(actor)
        first = save(store, owner, person, relationship, "我们计划第一周见面")
        second = save(store, owner, person, relationship, "我们计划第二周见面")
        preview = mutations.preview_undo(actor)
        undo = mutations.undo(
            actor, expected_operation_id=preview.latest_operation_id, operation_key="demo-undo"
        )
        retry = mutations.undo(
            actor, expected_operation_id=preview.latest_operation_id, operation_key="demo-undo"
        )
        remaining = controls.inspect_memories(actor)
        challenge = mutations.prepare_delete_person(actor, person_id=person)
        deletion = mutations.execute_delete(
            actor, confirmation_id=challenge.confirmation_id, operation_key="demo-person-delete"
        )
        after = controls.inspect_memories(actor)
        _, recalled = await run_agent(
            engine, owner, person, relationship, conversation, store, save=False
        )
        if not (
            first.saved_count == second.saved_count == 1
            and preview.available
            and undo.status == "undone"
            and retry.mutation_id == undo.mutation_id
            and retry.replayed
            and len(remaining.items) == 1
            and challenge.expected_count == 1
            and deletion.affected_count == 1
            and after.items == []
            and recalled == 0
        ):
            raise RuntimeError("Memory destructive control demonstration failed")
        print(
            json.dumps(
                {
                    "saved_count": 2,
                    "undo_preview_available": preview.available,
                    "undo_status": undo.status,
                    "undo_retry_replayed": retry.replayed,
                    "older_memory_survived_retry": len(remaining.items) == 1,
                    "delete_confirmation_count": challenge.expected_count,
                    "delete_affected_count": deletion.affected_count,
                    "inspect_after_delete_count": len(after.items),
                    "agent_recall_after_delete_count": recalled,
                }
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
