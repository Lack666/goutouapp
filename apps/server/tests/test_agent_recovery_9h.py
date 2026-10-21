"""Actual worker death around LangGraph/Mock commits, not age-based SQL recovery."""

import asyncio
import multiprocessing
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from test_agent_rest import headers, settings
from test_import_api import scope

from app.agent.dependencies import RuntimeDependencies
from app.agent.memory import MemoryService
from app.agent.runtime import AgentRuntime
from app.auth.jwt_verifier import JWTBearerVerifier
from app.db.models import AgentRun, MemoryRecordRow, Message, RunRecoveryReceipt
from app.db.repositories.memory import SQLAlchemyMemoryStore
from app.main import create_app
from app.services.agent_recovery import AgentRunRecovery
from app.services.agent_service import AgentService, actor_from_verified_identity
from app.services.agent_stream import ServiceFinalResponse, ServiceMemoryStatus
from app.services.agent_writer import AgentWriterRegistry
from app.services.backup_restore import RecoveryError, dump_synthetic, restore_synthetic
from app.services.erasure import ErasureError


@pytest.fixture(name="database_engine")
def isolated_recovery_engine(recovery_database_engine):
    return recovery_database_engine


def worker(pipe):
    """Pipe receives only synthetic credentials, never CLI argv or logged payloads."""
    from memory_phase6_support import Phase6Mock

    async def run():
        url, root, credential, conversation, relationship, stage = pipe.recv()
        engine = create_engine(url, hide_parameters=True)
        config = settings(engine, chat_import_artifact_root=Path(root))
        actor = actor_from_verified_identity(JWTBearerVerifier(config).verify(credential).user_id)
        writers = AgentWriterRegistry(Path(root))

        class HeldStore(SQLAlchemyMemoryStore):
            def save_record(self, record):
                if stage == "memory_thread":
                    pipe.send({"run_id": record.evidence.split(":", 1)[0], "stage": stage})
                    Event().wait()
                return super().save_record(record)

        class HeldMock(Phase6Mock):
            async def structured_output(self, messages, schema, **kwargs):
                if stage == "provider" and schema.__name__ == "SafetyResult":
                    with Session(engine) as db:
                        run_id = db.scalar(
                            select(AgentRun.id).where(
                                AgentRun.conversation_id == UUID(conversation)
                            )
                        )
                    pipe.send({"run_id": str(run_id), "stage": stage})
                    await asyncio.Event().wait()
                return await super().structured_output(messages, schema, **kwargs)

        runtime = AgentRuntime(
            dependencies=RuntimeDependencies(
                llm_provider=HeldMock(),
                memory_service=MemoryService(HeldStore(lambda: Session(engine))),
            )
        )
        service = AgentService(lambda: Session(engine), runtime, writers=writers)
        if stage == "memory_thread":
            task = asyncio.create_task(
                service.execute(
                    actor=actor,
                    conversation_id=UUID(conversation),
                    relationship_id=UUID(relationship),
                    message="我们计划第一周见面。请存入长期记忆。",
                    operation_key="synthetic-recovery-original-key",
                )
            )
            assert await asyncio.to_thread(pipe.recv) == "cancel"
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            pipe.send({"cancelled": True})
            await asyncio.Event().wait()
        stream = await service.stream(
            actor=actor,
            conversation_id=UUID(conversation),
            relationship_id=UUID(relationship),
            message="我们计划第一周见面。请存入长期记忆。",
            operation_key="synthetic-recovery-original-key",
        )
        async for event in stream.events:
            if (stage == "answer" and isinstance(event, ServiceFinalResponse)) or (
                stage == "memory" and isinstance(event, ServiceMemoryStatus)
            ):
                pipe.send({"run_id": str(stream.run_id), "stage": stage})
                await asyncio.Event().wait()

    try:
        asyncio.run(run())
    except Exception:
        pipe.send({"error": "synthetic_worker_failed"})


@pytest.mark.parametrize("stage", ["provider", "answer", "memory", "memory_thread"])
def test_proved_worker_stop_preserves_committed_effects_and_original_key(
    database_engine, tmp_path, stage
):
    engine = database_engine
    a, b = scope(engine), scope(engine)
    root = tmp_path / "artifacts"
    config = settings(engine, chat_import_artifact_root=root)
    with TestClient(create_app(config)) as client:
        assert (
            client.post(
                "/api/v1/memory/consent", headers=headers(a[0]), json={"enabled": True}
            ).status_code
            == 200
        )
        assert client.post("/api/v1/memory/resume", headers=headers(a[0])).status_code == 200
        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe()
        process = context.Process(target=worker, args=(child,))
        process.start()
        child.close()
        parent.send(
            (
                engine.url.render_as_string(hide_password=False),
                str(root),
                headers(a[0])["Authorization"].removeprefix("Bearer "),
                str(a[3]),
                str(a[2]),
                stage,
            )
        )
        try:
            assert parent.poll(30), "Synthetic worker did not reach the controlled commit point"
            proof = parent.recv()
            assert "run_id" in proof, proof
            if stage == "memory_thread":
                parent.send("cancel")
                assert parent.poll(10)
                assert parent.recv() == {"cancelled": True}
            run_id = UUID(proof["run_id"])
            recovery = AgentRunRecovery(lambda: Session(engine), AgentWriterRegistry(root))
            actor = actor_from_verified_identity(a[0])
            key = uuid4().hex
            with Session(engine) as db, db.begin():
                db.get(AgentRun, run_id).created_at = datetime.now(UTC) - timedelta(days=30)
            with pytest.raises(ErasureError, match="writer_proof_unavailable"):
                recovery.recover(actor, a[3], run_id, key)
            # Losing every pooled DB connection still is not an OS writer-stop proof.
            engine.dispose()
            with pytest.raises(ErasureError, match="writer_proof_unavailable"):
                recovery.recover(actor, a[3], run_id, key)
            with pytest.raises(ErasureError, match="not_found"):
                recovery.recover(actor_from_verified_identity(b[0]), a[3], run_id, key)
            archive = tmp_path / "run-synthetic.dump"
            dump_synthetic(engine, archive)
            restore_root = tmp_path / "restore-empty"
            restore_root.mkdir()
            with restore_synthetic(engine, archive, restore_root) as quarantine:
                with pytest.raises(RecoveryError):
                    quarantine.reconcile()
                assert not quarantine.released
            process.terminate()
            process.join(10)
            assert not process.is_alive()
            result = recovery.recover(actor, a[3], run_id, key)
            assert result == recovery.recover(actor, a[3], run_id, key)
            assert result["assistant_preserved"] == (stage in {"answer", "memory"})
            assert result["observed_memory_count"] == (1 if stage == "memory" else 0)
            with restore_synthetic(engine, archive, restore_root) as quarantine:
                restored = quarantine.reconcile()
                restored_recovery = AgentRunRecovery(
                    lambda: Session(restored), AgentWriterRegistry(restore_root)
                )
                assert restored_recovery.recover(actor, a[3], run_id, key) == result
                with Session(restored) as db:
                    assert db.get(AgentRun, run_id).failure_code == "writer_stopped"
                    assert (
                        db.scalar(
                            select(func.count())
                            .select_from(RunRecoveryReceipt)
                            .where(RunRecoveryReceipt.run_id == run_id)
                        )
                        == 1
                    )
            archive.unlink(missing_ok=True)
            with Session(engine) as db:
                row = db.get(AgentRun, run_id)
                assert row.status == "failed" and row.failure_code == "writer_stopped"
                assert row.operation_key == "synthetic-recovery-original-key"
                assert row.recovered_at is not None
                assert db.scalar(
                    select(func.count()).select_from(Message).where(Message.conversation_id == a[3])
                ) == (2 if stage in {"answer", "memory"} else 1)
                assert db.scalar(
                    select(func.count())
                    .select_from(MemoryRecordRow)
                    .where(MemoryRecordRow.first_run_id == run_id)
                ) == (1 if stage == "memory" else 0)
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(RunRecoveryReceipt)
                        .where(RunRecoveryReceipt.run_id == run_id)
                    )
                    == 1
                )
            body = {
                "message": "我们计划第一周见面。请存入长期记忆。",
                "operation_key": "synthetic-recovery-original-key",
                "expected_relationship_id": str(a[2]),
            }
            for suffix in ("", "/stream"):
                response = client.post(
                    f"/api/v1/conversations/{a[3]}/agent-runs{suffix}",
                    headers=headers(a[0]),
                    json=body,
                )
                assert (
                    response.status_code == 409
                    and response.json()["error"]["code"] == "operation_failed"
                )
            target = {
                "domain": "conversation",
                "target_id": str(a[3]),
                "relationship_id": str(a[2]),
            }
            challenge = client.post("/api/v1/erasures/prepare", headers=headers(a[0]), json=target)
            assert challenge.status_code == 200, challenge.text
        finally:
            if process.is_alive():
                process.terminate()
                process.join(10)
            parent.close()


@pytest.mark.parametrize("proof_fault", ["legacy", "missing_fence", "wrong_root", "tampered_scope"])
def test_missing_legacy_and_wrong_root_proof_stays_fail_closed(
    database_engine, tmp_path, proof_fault
):
    a = scope(database_engine)
    registry = AgentWriterRegistry(tmp_path / "correct-root")
    token = uuid4()
    if proof_fault in {"wrong_root", "tampered_scope"}:
        registry.start(token).close()
    with Session(database_engine) as db, db.begin():
        row = AgentRun(user_id=a[0], conversation_id=a[3], status="running")
        if proof_fault != "legacy":
            row.writer_token = token
            row.writer_scope = registry.scope if proof_fault != "tampered_scope" else "0" * 64
        db.add(row)
        db.flush()
        rid = row.id
    if proof_fault == "wrong_root":
        registry = AgentWriterRegistry(tmp_path / "wrong-root")
    recovery = AgentRunRecovery(lambda: Session(database_engine), registry)
    with pytest.raises(ErasureError, match="writer_proof_unavailable"):
        recovery.recover(actor_from_verified_identity(a[0]), a[3], rid, uuid4().hex)
    with Session(database_engine) as db:
        assert db.get(AgentRun, rid).status == "running"
