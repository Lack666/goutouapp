"""Synthetic real PostgreSQL + AgentService/MockLLM Phase 6C demonstration."""

import asyncio
import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta

from memory_control_demo import create_scope, disposable_database, run_agent
from memory_destructive_control_demo import save
from sqlalchemy.orm import Session

from app.db.models import MemoryConfirmationRow, MemoryRecordRow
from app.db.repositories.memory import SQLAlchemyMemoryStore
from app.services.agent_service import actor_from_verified_identity
from app.services.memory_control import MemoryControlService
from app.services.memory_mutation import MemoryMutationService


def cli(engine, mode):
    env = os.environ.copy()
    env["DATABASE_URL"] = engine.url.render_as_string(hide_password=False)
    output = subprocess.run(
        [sys.executable, "apps/server/cleanup_memory_retention.py", mode, "--batch-size", "1"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(output.stdout)


async def main() -> None:
    with disposable_database() as engine:
        owner, person, relationship, conversation = create_scope(engine)
        actor = actor_from_verified_identity(owner)
        store = SQLAlchemyMemoryStore(lambda: Session(engine))
        controls = MemoryControlService(store)
        controls.grant_consent(actor)
        assert save(store, owner, person, relationship, "我们计划第一周见面").saved_count == 1
        valid = store.list_records(owner)[0]
        assert save(store, owner, person, relationship, "我们计划第二周见面").saved_count == 1
        expired = next(r for r in store.list_records(owner) if r.id != valid.id)
        with Session(engine) as db, db.begin():
            db.get(MemoryRecordRow, expired.id).expires_at = datetime.now(UTC) - timedelta(
                seconds=1
            )
        _, recalled = await run_agent(
            engine, owner, person, relationship, conversation, store, save=False
        )
        assert recalled == 1
        dry = cli(engine, "--dry-run")
        assert dry["counts"]["memory_records"] == 1
        with Session(engine) as db:
            assert db.get(MemoryRecordRow, expired.id) is not None
        executed = cli(engine, "--execute")
        assert executed["counts"]["memory_records"] == executed["counts"]["undo_operations"] == 1
        # New sessions prove primary physical removal rather than an ORM cache view.
        with Session(engine) as db:
            assert db.get(MemoryRecordRow, expired.id) is None
            assert db.get(MemoryRecordRow, valid.id) is not None
        assert len(controls.inspect_memories(actor).items) == 1
        second = cli(engine, "--execute")
        assert second["counts"]["memory_records"] == 0
        mutations = MemoryMutationService(
            lambda: Session(engine), clock=lambda: datetime.now(UTC) - timedelta(days=2)
        )
        challenge = mutations.prepare_delete_all(actor, revoke_consent_after_delete=False)
        receipt = mutations.execute_delete(
            actor, confirmation_id=challenge.confirmation_id, operation_key="retention-demo-delete"
        )
        assert save(store, owner, person, relationship, "我们计划第三周见面").saved_count == 1
        metadata = cli(engine, "--execute")
        assert metadata["counts"]["confirmation_challenges"] == 1
        with Session(engine) as db:
            assert db.get(MemoryConfirmationRow, challenge.confirmation_id) is None
        replay = mutations.execute_delete(
            actor, confirmation_id=challenge.confirmation_id, operation_key="retention-demo-delete"
        )
        assert replay.replayed and replay.mutation_id == receipt.mutation_id
        assert len(controls.inspect_memories(actor).items) == 1
        print(
            json.dumps(
                {
                    "consent_explicit": True,
                    "agent_recall_active_count": recalled,
                    "expired_record_excluded_before_cleanup": True,
                    "dry_run_eligible_records": dry["counts"]["memory_records"],
                    "dry_run_did_not_mutate": True,
                    "physical_records_removed": executed["counts"]["memory_records"],
                    "undo_history_removed": executed["counts"]["undo_operations"],
                    "new_session_inspect_active_count": 1,
                    "second_cleanup_removed": second["counts"]["memory_records"],
                    "consumed_challenges_removed": metadata["counts"]["confirmation_challenges"],
                    "receipt_replay_after_challenge_cleanup": replay.replayed,
                    "new_memory_survives_receipt_retry": True,
                    "automatic_scheduling": "NOT DEPLOYED",
                }
            )
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        print(json.dumps({"status": "failed", "error": "retention_demo_failed"}))
        raise SystemExit(1) from None
