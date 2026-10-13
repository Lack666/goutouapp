"""Native PostgreSQL archives/restores; no SQLite, no keys or real transcripts."""

import asyncio
import subprocess
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from threading import Event
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from memory_control_demo import run_agent
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from test_agent_rest import headers, settings
from test_import_api import bind, finalize, scope, upload
from test_memory_control import _save

from app.db.models import (
    ChatImportArtifact,
    ChatImportJob,
    MemoryConfirmationRow,
    MemoryMutationRow,
    MemoryRecordRow,
    RelationshipMessage,
)
from app.db.repositories.memory import SQLAlchemyMemoryStore
from app.main import create_app
from app.services.agent_service import actor_from_verified_identity
from app.services.backup_restore import RecoveryError, _synthetic, dump_synthetic, restore_synthetic
from app.services.memory_mutation import MemoryMutationService


@pytest.fixture
def recovery(database_engine, tmp_path):
    a, b = scope(database_engine), scope(database_engine)
    store = SQLAlchemyMemoryStore(lambda: Session(database_engine))
    _save(store, a[0], a[1], a[2], "Synthetic recovery target")
    _save(store, b[0], b[1], b[2], "Synthetic retained owner")
    config = settings(database_engine, chat_import_artifact_root=tmp_path / "source-artifacts")
    with TestClient(create_app(config)) as client:
        yield database_engine, tmp_path, a, b, store, client


def delete_via_http(client, owner, record, action):
    base = "/api/v1/memory"
    key = uuid4().hex
    if action == "undo":
        preview = client.get(base + "/undo/preview", headers=headers(owner)).json()
        body = {"expected_operation_id": preview["latest_operation_id"], "operation_key": key}
        path = base + "/undo"
    else:
        endpoint, body = {
            "delete_one": (
                "one",
                {
                    "memory_id": str(record.id),
                    "person_id": str(record.person_id),
                    "relationship_id": str(record.relationship_id),
                },
            ),
            "delete_person": ("person", {"person_id": str(record.person_id)}),
            "delete_all": ("all", {"revoke_consent_after_delete": True}),
        }[action]
        prepare = client.post(
            f"{base}/deletions/{endpoint}/prepare", headers=headers(owner), json=body
        )
        assert prepare.status_code == 200
        path = base + "/deletions/" + prepare.json()["confirmation_id"] + "/execute"
        body = {"operation_key": key}
    result = client.post(path, headers=headers(owner), json=body)
    assert result.status_code == 200
    return result.json(), path, body


@contextmanager
def backup_snapshot(engine):
    with (
        engine.connect().execution_options(isolation_level="REPEATABLE READ") as snapshot,
        snapshot.begin(),
    ):
        yield snapshot.scalar(text("SELECT pg_export_snapshot()"))


@pytest.mark.parametrize("timing", ["before", "after", "concurrent_snapshot"])
@pytest.mark.parametrize("action", ["undo", "delete_one", "delete_person", "delete_all"])
def test_real_backup_delete_restore_exact_owner_targets_and_receipts(recovery, timing, action):
    engine, temp, a, b, store, client = recovery
    deleted_record = store.list_records(a[0])[0]
    retained_b = store.list_records(b[0])[0]
    archive = temp / "synthetic.dump"
    if timing == "before":
        receipt, path, body = delete_via_http(client, a[0], deleted_record, action)
        dump_synthetic(engine, archive)
    elif timing == "after":
        dump_synthetic(engine, archive)
        receipt, path, body = delete_via_http(client, a[0], deleted_record, action)
    else:
        # The real dump reads a snapshot from before a concurrently committed delete.
        with backup_snapshot(engine) as snapshot:
            receipt, path, body = delete_via_http(client, a[0], deleted_record, action)
            dump_synthetic(engine, archive, snapshot=snapshot)
    # Delete-all with revoke also pauses writes. A later save needs an explicit
    # regrant AND resume; preserve both guards in this recovery-point-loss test.
    assert (
        client.post(
            "/api/v1/memory/consent", headers=headers(a[0]), json={"enabled": True}
        ).status_code
        == 200
    )
    assert client.post("/api/v1/memory/resume", headers=headers(a[0])).status_code == 200
    _save(store, a[0], a[1], a[2], "Synthetic later post-backup save")
    new_record = store.list_records(a[0])[0]
    # Revoke after the save, so reconciliation cannot resurrect backup consent.
    assert (
        client.post(
            "/api/v1/memory/consent", headers=headers(a[0]), json={"enabled": False}
        ).status_code
        == 200
    )
    root = temp / "restore-artifacts"
    root.mkdir()
    try:
        with restore_synthetic(engine, archive, root) as recovery_state:
            assert not recovery_state.released
            # Privileged offline witness; this target has no application listener.
            with Session(recovery_state._target) as db:
                assert (db.get(MemoryRecordRow, deleted_record.id) is not None) == (
                    timing != "before"
                )
            restored = recovery_state.reconcile()
            assert recovery_state.released
            restored_store = SQLAlchemyMemoryStore(lambda: Session(restored))
            assert restored_store.get_record(a[0], deleted_record.id) is None
            assert (
                restored_store.get_record(a[0], new_record.id) is None
            )  # Explicit recovery-point loss.
            assert restored_store.get_record(b[0], retained_b.id) is not None
            assert restored_store.get_record(a[0], retained_b.id) is None
            assert not restored_store.get_control(a[0]).consent_enabled
            with Session(restored) as db:
                assert db.get(MemoryMutationRow, UUID(receipt["mutation_id"])) is not None
                assert db.scalar(select(func.count()).select_from(MemoryConfirmationRow)) == 0
            restored_app = create_app(settings(restored, chat_import_artifact_root=root))
            with TestClient(restored_app) as restored_client:
                replay = restored_client.post(path, headers=headers(a[0]), json=body)
                assert replay.status_code == 200 and replay.json()["replayed"]
                assert replay.json()["mutation_id"] == receipt["mutation_id"]
                receipt_path = "/api/v1/memory/mutations/" + receipt["mutation_id"]
                assert restored_client.get(receipt_path, headers=headers(a[0])).status_code == 200
                assert restored_client.get(receipt_path, headers=headers(b[0])).status_code == 404
            assert asyncio.run(run_agent(restored, *a, restored_store, save=False))[1] == 0
            assert asyncio.run(run_agent(restored, *b, restored_store, save=False))[1] == 1
            # Do not repeat after Agent creates new target-only messages/runs: reconciliation
            # handles the Memory/control plane and leaves unrelated valid target data intact.
            assert recovery_state.reconcile() == restored
            assert recovery_state.counts["memory_removed"] == 0
    finally:
        archive.unlink(missing_ok=True)
    assert not archive.exists()
    assert store.get_record(a[0], new_record.id) is not None


def test_real_restore_formal_import_history_retained_pending_cancelled_empty_files(recovery):
    engine, temp, a, b, _, client = recovery
    jobs = []
    for user, person, rel, _ in (a, b):
        job = bind(client, user, upload(client, user).json(), person, rel)
        assert finalize(client, user, job).status_code == 200
        jobs.append(job)
    pending = upload(client, a[0]).json()
    archive = temp / "import.dump"
    dump_synthetic(engine, archive)
    root = temp / "restore-artifacts"
    root.mkdir()
    try:
        with restore_synthetic(engine, archive, root) as state:
            restored = state.reconcile()
            with Session(restored) as db:
                assert db.get(ChatImportJob, UUID(pending["id"])).status == "cancelled"
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(ChatImportArtifact)
                        .where(ChatImportArtifact.state == "active")
                    )
                    == 0
                )
                for user, *_ in (a, b):
                    assert (
                        db.scalar(
                            select(func.count())
                            .select_from(RelationshipMessage)
                            .where(RelationshipMessage.owner_user_id == user)
                        )
                        == 2
                    )
            app = create_app(settings(restored, chat_import_artifact_root=root))
            with TestClient(app) as connected:
                assert finalize(connected, a[0], jobs[0]).status_code == 200
                assert finalize(connected, b[0], jobs[0]).status_code == 404
                assert finalize(connected, a[0], pending).status_code == 409
                assert app.state.resource_admission.snapshot()["charged_storage_bytes"] == 0
            assert list(root.iterdir()) == []
    finally:
        archive.unlink(missing_ok=True)


def test_restore_failure_rolls_back_and_does_not_release(recovery, monkeypatch):
    engine, temp, a, _, store, client = recovery
    record = store.list_records(a[0])[0]
    archive = temp / "rollback.dump"
    dump_synthetic(engine, archive)
    delete_via_http(client, a[0], record, "delete_all")
    root = temp / "restore-artifacts"
    root.mkdir()
    try:
        with restore_synthetic(engine, archive, root) as state:
            original = Session.execute

            def injected(self, statement, *args, **kwargs):
                if str(statement).startswith("DELETE FROM memory_confirmations"):
                    raise RuntimeError("private-memory-and-password-" + uuid4().hex)
                return original(self, statement, *args, **kwargs)

            monkeypatch.setattr(Session, "execute", injected)
            with pytest.raises(RecoveryError, match="^synthetic_recovery_failed$"):
                state.reconcile()
            assert not state.released
            with Session(state._target) as db:
                assert db.get(MemoryRecordRow, record.id) is not None
            monkeypatch.setattr(Session, "execute", original)
            assert state.reconcile() is state._target
    finally:
        archive.unlink(missing_ok=True)


def test_reconciliation_waits_for_committed_delete_and_blocks_concurrent_write(
    recovery, monkeypatch
):
    engine, temp, a, _, store, client = recovery
    record = store.list_records(a[0])[0]
    archive = temp / "race.dump"
    dump_synthetic(engine, archive)
    root = temp / "restore-artifacts"
    root.mkdir()
    try:
        with restore_synthetic(engine, archive, root) as state:
            # Pause the FORMAL guarded mutation before its commit, with a durable
            # receipt staged. The source freeze must wait for that transaction.
            mutations = MemoryMutationService(lambda: Session(engine))
            actor = actor_from_verified_identity(a[0])
            challenge = mutations.prepare_delete_all(actor, revoke_consent_after_delete=False)
            staged, finish = Event(), Event()
            original = mutations._add_receipt

            def hold_receipt(db, row):
                original(db, row)
                staged.set()
                assert finish.wait(5)

            monkeypatch.setattr(mutations, "_add_receipt", hold_receipt)
            with ThreadPoolExecutor() as pool:
                deletion = pool.submit(
                    mutations.execute_delete,
                    actor,
                    confirmation_id=challenge.confirmation_id,
                    operation_key=uuid4().hex,
                )
                try:
                    assert staged.wait(5)
                    task = pool.submit(state.reconcile)
                    assert not state.released
                finally:
                    finish.set()
                receipt = deletion.result(timeout=10)
                restored = task.result(timeout=10)
                with Session(restored) as db:
                    assert db.get(MemoryMutationRow, receipt.mutation_id) is not None
            assert (
                SQLAlchemyMemoryStore(lambda: Session(restored)).get_record(a[0], record.id) is None
            )
    finally:
        archive.unlink(missing_ok=True)


def test_corrupt_archive_native_errors_are_private_and_target_dropped(recovery, capsys):
    engine, temp, *_ = recovery
    archive = temp / "bad.dump"
    marker = "private-raw-chat-" + uuid4().hex
    archive.write_bytes(marker.encode())
    root = temp / "restore-artifacts"
    root.mkdir()
    with pytest.raises(RecoveryError) as error, restore_synthetic(engine, archive, root):
        pytest.fail("corrupt backup was accepted")
    assert marker not in str(error.value) + repr(error.value) + capsys.readouterr().out
    archive.unlink()


@pytest.mark.parametrize(
    "database,host",
    [
        ("production", "127.0.0.1"),
        ("goutou_test", "127.0.0.1"),
        ("goutou_test_123456789abc", "remote.example"),
    ],
)
def test_recovery_refuses_non_disposable_or_non_loopback_target(recovery, database, host):
    engine, *_ = recovery
    with pytest.raises(RecoveryError):
        _synthetic(engine.url.set(database=database, host=host))


def test_native_timeout_and_output_do_not_escape(recovery, monkeypatch):
    from app.services import backup_restore

    engine, temp, *_ = recovery
    marker = "private-jwt-and-password-" + uuid4().hex

    def fail(*args, **kwargs):
        raise subprocess.TimeoutExpired([marker], 1, output=marker, stderr=marker)

    monkeypatch.setattr(subprocess, "run", fail)
    with pytest.raises(RecoveryError) as error:
        backup_restore.dump_synthetic(engine, temp / "failed.dump")
    assert marker not in str(error.value) + repr(error.value)
    assert error.value.__suppress_context__


def test_restore_refuses_missing_authoritative_owner_and_nonempty_root(recovery):
    engine, temp, *_ = recovery
    archive = temp / "owner.dump"
    dump_synthetic(engine, archive)
    root = temp / "restore-artifacts"
    root.mkdir()
    try:
        with restore_synthetic(engine, archive, root) as state:
            with Session(state._target) as db, db.begin():
                from app.db.repositories.records import create_user

                create_user(db)
            with pytest.raises(RecoveryError):
                state.reconcile()
            assert not state.released
        (root / "unexpected.bin").write_bytes(b"synthetic")
        with pytest.raises(RecoveryError), restore_synthetic(engine, archive, root):
            pytest.fail("nonempty restore root accepted")
    finally:
        archive.unlink(missing_ok=True)


def test_person_delete_restore_preserves_other_person_and_invalidates_old_challenge(recovery):
    from app.db.repositories import records

    engine, temp, a, b, store, client = recovery
    target = store.list_records(a[0])[0]
    with Session(engine) as db, db.begin():
        person = records.create_person(db, a[0], "Synthetic other person")
        rel = records.create_relationship(db, a[0], person.id, "dating", "active")
        person_id, rel_id = person.id, rel.id
    _save(store, a[0], person_id, rel_id, "Synthetic other person retained")
    other = next(r for r in store.list_records(a[0]) if r.person_id == person_id)
    old_challenge = client.post(
        "/api/v1/memory/deletions/all/prepare",
        headers=headers(a[0]),
        json={"revoke_consent_after_delete": False},
    ).json()
    archive = temp / "person.dump"
    dump_synthetic(engine, archive)
    _, path, body = delete_via_http(client, a[0], target, "delete_person")
    root = temp / "restored-files"
    root.mkdir()
    try:
        with restore_synthetic(engine, archive, root) as state:
            restored = state.reconcile()
            target_store = SQLAlchemyMemoryStore(lambda: Session(restored))
            assert target_store.get_record(a[0], target.id) is None
            assert target_store.get_record(a[0], other.id) is not None
            assert len(target_store.list_records(b[0])) == 1
            with TestClient(
                create_app(settings(restored, chat_import_artifact_root=root))
            ) as target_client:
                replay = target_client.post(path, headers=headers(a[0]), json=body)
                assert replay.status_code == 200 and replay.json()["replayed"]
                stale = target_client.post(
                    "/api/v1/memory/deletions/" + old_challenge["confirmation_id"] + "/execute",
                    headers=headers(a[0]),
                    json={"operation_key": uuid4().hex},
                )
                assert stale.status_code == 409
                conflicting = target_client.post(
                    "/api/v1/memory/undo",
                    headers=headers(a[0]),
                    json={
                        "expected_operation_id": str(uuid4()),
                        "operation_key": body["operation_key"],
                    },
                )
                assert conflicting.status_code == 409
                assert target_store.get_record(a[0], other.id) is not None
    finally:
        archive.unlink(missing_ok=True)


def test_retention_after_backup_does_not_reappear_after_restore(recovery):
    from datetime import UTC, datetime, timedelta

    from app.services.memory_retention import MemoryRetentionService

    engine, temp, a, b, store, _ = recovery
    record = store.list_records(a[0])[0]
    archive = temp / "retention.dump"
    dump_synthetic(engine, archive)
    with Session(engine) as db, db.begin():
        db.get(MemoryRecordRow, record.id).expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert (
        MemoryRetentionService(lambda: Session(engine)).run(dry_run=False, max_batches=100).status
        == "ok"
    )
    root = temp / "restored-files"
    root.mkdir()
    try:
        with restore_synthetic(engine, archive, root) as state:
            target = state.reconcile()
            target_store = SQLAlchemyMemoryStore(lambda: Session(target))
            assert target_store.get_record(a[0], record.id) is None
            assert len(target_store.list_records(b[0])) == 1
            assert asyncio.run(run_agent(target, *a, target_store, save=False))[1] == 0
    finally:
        archive.unlink(missing_ok=True)


@pytest.mark.parametrize("when", ["before_backup", "after_backup"])
def test_restore_cannot_release_when_acknowledged_agent_key_is_missing(recovery, when):
    from test_agent_service import queue_safety, service_with_mock

    engine, temp, a, _, _, _ = recovery
    archive = temp / "agent-keys.dump"
    service, provider, _ = service_with_mock(engine)
    queue_safety(provider)
    key = uuid4().hex
    if when == "after_backup":
        dump_synthetic(engine, archive)
    completed = asyncio.run(
        service.execute(
            actor=actor_from_verified_identity(a[0]),
            conversation_id=a[3],
            message="Synthetic controlled safety fixture",
            operation_key=key,
        )
    )
    if when == "before_backup":
        dump_synthetic(engine, archive)
    root = temp / "restored-files"
    root.mkdir()
    try:
        with restore_synthetic(engine, archive, root) as state:
            if when == "after_backup":
                with pytest.raises(RecoveryError):
                    state.reconcile()
                assert not state.released
            else:
                restored = state.reconcile()
                replay_service, _, runtime = service_with_mock(restored)
                replay = asyncio.run(
                    replay_service.execute(
                        actor=actor_from_verified_identity(a[0]),
                        conversation_id=a[3],
                        message="Synthetic controlled safety fixture",
                        operation_key=key,
                    )
                )
                assert replay.run_id == completed.run_id and not runtime.requests
    finally:
        archive.unlink(missing_ok=True)
