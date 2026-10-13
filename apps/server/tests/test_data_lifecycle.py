"""9D signed-owner lifecycle, periodic execution, physical retry and OS competition."""

import multiprocessing
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Event
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_agent_rest import headers, settings
from test_import_api import bind, finalize, scope, upload
from test_memory_control import _save

from app.chat_import.artifacts import ArtifactStoreError, LocalFilesystemImportArtifactStore
from app.core.config import Settings
from app.db.models import ChatImportArtifact, ChatImportJob, MemoryRecordRow, RelationshipMessage
from app.db.repositories.memory import SQLAlchemyMemoryStore
from app.db.session import Database
from app.main import create_app
from app.services.import_workflow import ImportWorkflowService
from app.services.maintenance import MaintenanceLoop, MaintenanceService
from app.services.resource_admission import AdmissionRejected, ResourceAdmission


@pytest.fixture
def lifecycle(database_engine, tmp_path):
    root = tmp_path / "sources"
    config = settings(
        database_engine,
        chat_import_artifact_root=root,
        max_chat_import_bytes=4096,
        admission_min_free_bytes=0,
    )
    app = create_app(config)
    database = Database(config)
    admission = ResourceAdmission(database, config)
    maintenance = MaintenanceService(admission, app.state.import_workflow)
    with TestClient(app) as client:
        yield app, client, root, database_engine, maintenance, config
    database.dispose()


def artifact(engine, job):
    with Session(engine) as db:
        return db.get(ChatImportArtifact, UUID(job["artifact_id"])).storage_key


def expire(engine, job):
    with Session(engine) as db, db.begin():
        db.get(ChatImportArtifact, UUID(job["artifact_id"])).expires_at = datetime.now(
            UTC
        ) - timedelta(seconds=1)


def test_periodic_loop_retries_failure_and_drains_expired_memory(lifecycle, monkeypatch, capsys):
    app, client, root, engine, maintenance, _ = lifecycle
    owner, person, rel, _ = scope(engine)
    job = upload(client, owner).json()
    expire(engine, job)
    store = SQLAlchemyMemoryStore(lambda: Session(engine))
    _save(store, owner, person, rel, "Synthetic lifecycle preference")
    memory = store.list_records(owner)[0]
    with Session(engine) as db, db.begin():
        db.get(MemoryRecordRow, memory.id).expires_at = datetime.now(UTC) - timedelta(seconds=1)
    original = app.state.import_workflow._store.delete
    attempts = []
    marker = "private-body-and-token-" + uuid4().hex

    def fail_once(key):
        attempts.append(key)
        if len(attempts) == 1:
            raise OSError(marker)
        original(key)

    monkeypatch.setattr(app.state.import_workflow._store, "delete", fail_once)
    reports = []
    loop = MaintenanceLoop(maintenance, interval_seconds=0.03)
    loop.run(Event(), iterations=3, report=reports.append)
    assert loop.executions == 3 and loop.failures == 1
    assert reports[0].status == "failed" and reports[0].cleanup_failures == 1
    assert reports[1].status == reports[2].status == "ok"
    assert reports[0].memory.counts.memory_records >= 1
    assert store.get_record(owner, memory.id) is None
    assert list(root.iterdir()) == []
    assert reports[-1].occupancy["charged_storage_bytes"] == 0
    assert marker not in capsys.readouterr().err + "".join(r.model_dump_json() for r in reports)
    with Session(engine) as db:
        assert db.get(ChatImportJob, UUID(job["id"])).status == "cancelled"


@pytest.mark.parametrize(
    "state,physical", [("active", True), ("deleted", True), ("expired", True), ("active", False)]
)
def test_metadata_physical_mismatches_reconcile_and_restore_quota(lifecycle, state, physical):
    app, client, root, engine, maintenance, _ = lifecycle
    owner, *_ = scope(engine)
    job = upload(client, owner).json()
    key = artifact(engine, job)
    with Session(engine) as db, db.begin():
        row = db.get(ChatImportArtifact, UUID(job["artifact_id"]))
        row.state = state
        row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    if not physical:
        app.state.import_workflow._store.delete(key)
    before = maintenance.admission.snapshot()["charged_storage_bytes"]
    assert (before > 0) == physical
    result = maintenance.run()
    assert result.status == "ok" and result.occupancy["charged_storage_bytes"] == 0
    assert not (root / (key + ".bin")).exists()
    assert maintenance.run().artifact_removed == 0
    assert upload(client, owner).status_code == 201


def test_unlink_then_crash_before_metadata_update_is_retryable(lifecycle, monkeypatch):
    app, client, _, engine, maintenance, _ = lifecycle
    owner, *_ = scope(engine)
    job = upload(client, owner).json()
    expire(engine, job)
    original = app.state.import_workflow._store.delete

    def lost_update(key):
        original(key)
        raise OSError("synthetic crash after unlink")

    monkeypatch.setattr(app.state.import_workflow._store, "delete", lost_update)
    result = maintenance.run()
    assert result.status == "failed" and result.occupancy["charged_storage_bytes"] == 0
    with Session(engine) as db:
        assert db.get(ChatImportArtifact, UUID(job["artifact_id"])).state == "active"
    monkeypatch.setattr(app.state.import_workflow._store, "delete", original)
    assert maintenance.run().status == "ok"
    with Session(engine) as db:
        assert db.get(ChatImportArtifact, UUID(job["artifact_id"])).state in {"deleted", "expired"}


def test_slow_cleanup_keeps_physical_budget_until_unlink(lifecycle, monkeypatch):
    app, client, _, engine, maintenance, _ = lifecycle
    owner, *_ = scope(engine)
    job = upload(client, owner).json()
    expire(engine, job)
    original = app.state.import_workflow._store.delete
    entered, release = Event(), Event()

    def held(key):
        entered.set()
        assert release.wait(5)
        original(key)

    monkeypatch.setattr(app.state.import_workflow._store, "delete", held)
    with ThreadPoolExecutor() as pool:
        task = pool.submit(maintenance.run)
        try:
            assert entered.wait(5)
            assert maintenance.admission.snapshot()["charged_storage_bytes"] > 0
            competitor = MaintenanceService(maintenance.admission, app.state.import_workflow)
            assert competitor.run().status == "skipped"
        finally:
            release.set()
        assert task.result().status == "ok"
    assert maintenance.admission.snapshot()["charged_storage_bytes"] == 0


def test_live_upload_and_unknown_owner_orphan_sweep(lifecycle):
    app, client, root, engine, maintenance, _ = lifecycle
    owner, *_ = scope(engine)
    lease = maintenance.admission.acquire(owner, "upload")
    part = root / (lease.artifact_key + ".part")
    part.write_bytes(b"synthetic live fragment")
    unknown = root / (uuid4().hex + ".bin")
    unknown.write_bytes(b"synthetic unknown owner")
    old = (datetime.now(UTC) - timedelta(hours=2)).timestamp()
    os.utime(part, (old, old))
    os.utime(unknown, (old, old))
    try:
        assert maintenance.run().status == "ok"
        assert part.exists() and not unknown.exists()
        assert maintenance.admission.snapshot()["active_uploads"] == 1
    finally:
        maintenance.admission.release(lease)
    assert maintenance.run().status == "ok"
    assert not part.exists()
    assert upload(client, owner).status_code == 201


def test_fresh_unattributed_file_fails_closed_until_actual_cleanup(lifecycle):
    _, client, root, engine, maintenance, _ = lifecycle
    owner, *_ = scope(engine)
    path = root / (uuid4().hex + ".bin")
    path.write_bytes(b"synthetic orphan")
    assert maintenance.run().occupancy["unattributed_storage_bytes"] > 0
    with pytest.raises(AdmissionRejected):
        maintenance.admission.acquire(owner, "upload")
    old = (datetime.now(UTC) - timedelta(hours=2)).timestamp()
    os.utime(path, (old, old))
    assert maintenance.run().occupancy["unattributed_storage_bytes"] == 0
    assert upload(client, owner).status_code == 201


def test_cleanup_cancel_finalize_and_concurrent_upload_keep_formal_datasets(lifecycle):
    app, client, _, engine, maintenance, _ = lifecycle
    owner, person, rel, _ = scope(engine)
    outsider, *_ = scope(engine)
    job = bind(client, owner, upload(client, owner).json(), person, rel)
    with ThreadPoolExecutor() as pool:
        tasks = [
            pool.submit(finalize, client, owner, job),
            pool.submit(maintenance.run),
            pool.submit(upload, client, outsider),
        ]
        final, result, other = [t.result() for t in tasks]
    assert final.status_code == 200 and result.status == "ok" and other.status_code == 201
    duplicate = bind(client, owner, upload(client, owner).json(), person, rel)
    assert finalize(client, owner, duplicate).status_code == 200
    cancelled = client.post(
        f"/api/v1/chat-imports/{duplicate['id']}/cancel", headers=headers(owner)
    )
    assert cancelled.status_code == 200
    with Session(engine) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(RelationshipMessage)
                .where(RelationshipMessage.owner_user_id == owner)
            )
            == 2
        )
    assert maintenance.run().status == "ok"


def hold_maintenance(config, ready):
    database = Database(Settings(**config))
    admission = ResourceAdmission(database, Settings(**config))
    maintenance = MaintenanceService(admission, None)
    with maintenance._fence():
        ready.set()
        Event().wait(30)  # Parent kills only this owned test process.


def test_multiple_processes_compete_and_killed_maintenance_releases_fence(lifecycle):
    _, _, _, _, maintenance, config = lifecycle
    ctx = multiprocessing.get_context("spawn")
    ready = ctx.Event()
    process = ctx.Process(target=hold_maintenance, args=(config.model_dump(), ready))
    process.start()
    try:
        assert ready.wait(10)
        assert maintenance.run().status == "skipped"
    finally:
        process.terminate()
        process.join(10)
    assert not process.is_alive()
    assert maintenance.run().status == "ok"


def test_response_lost_delete_original_key_and_signed_foreign_owner_denial(lifecycle):
    app, client, _, engine, _, _ = lifecycle
    owner, person, rel, _ = scope(engine)
    outsider, *_ = scope(engine)
    store = SQLAlchemyMemoryStore(lambda: Session(engine))
    _save(store, owner, person, rel, "Synthetic deletion target")
    record = store.list_records(owner)[0]
    base = "/api/v1/memory/deletions"
    prepared = client.post(
        base + "/all/prepare", headers=headers(owner), json={"revoke_consent_after_delete": False}
    )
    challenge = prepared.json()["confirmation_id"]
    key = uuid4().hex
    foreign = client.post(
        f"{base}/{challenge}/execute", headers=headers(outsider), json={"operation_key": key}
    )
    assert foreign.status_code == 409
    deleted = client.post(
        f"{base}/{challenge}/execute", headers=headers(owner), json={"operation_key": key}
    )
    assert deleted.status_code == 200  # Committed response discarded by simulated client.
    _save(store, owner, person, rel, "Synthetic later record")
    replay = client.post(
        f"{base}/{challenge}/execute", headers=headers(owner), json={"operation_key": key}
    )
    assert replay.status_code == 200 and replay.json()["replayed"]
    assert replay.json()["mutation_id"] == deleted.json()["mutation_id"]
    assert store.get_record(owner, record.id) is None and len(store.list_records(owner)) == 1
    receipt_path = "/api/v1/memory/mutations/" + deleted.json()["mutation_id"]
    assert client.get(receipt_path, headers=headers(owner)).status_code == 200
    assert client.get(receipt_path, headers=headers(outsider)).status_code == 404
    job = upload(client, owner).json()
    assert (
        client.post(
            f"/api/v1/chat-imports/{job['id']}/cancel", headers=headers(outsider)
        ).status_code
        == 404
    )
    assert (
        client.get(f"/api/v1/chat-imports/{job['id']}", headers=headers(outsider)).status_code
        == 404
    )


def test_bounded_cleanup_cursor_reaches_later_jobs(lifecycle):
    app, client, _, engine, _, _ = lifecycle
    owner, *_ = scope(engine)
    jobs = [upload(client, owner).json() for _ in range(3)]
    for job in jobs:
        expire(engine, job)
    cursor, scanned, removed = None, 0, 0
    for _ in range(100):
        result = app.state.import_workflow.cleanup_pass(
            batch_size=1, max_batches=1, start_after=cursor
        )
        cursor = result.next_cursor
        scanned += result.scanned
        removed += result.removed
        if cursor is None:
            break
    else:
        pytest.fail("bounded cursor never completed sweep")
    assert scanned >= 3 and removed >= 3


def test_periodic_database_failure_is_generic_and_retries(lifecycle, monkeypatch):
    _, _, _, _, maintenance, _ = lifecycle
    original = maintenance.admission.snapshot
    calls = []
    marker = "private-database-password-" + uuid4().hex

    def fail_once():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError(marker)
        return original()

    monkeypatch.setattr(maintenance.admission, "snapshot", fail_once)
    results = []
    loop = MaintenanceLoop(maintenance, interval_seconds=0.01)
    loop.run(Event(), iterations=2, report=results.append)
    assert loop.failures == 1 and results[-1].status == "ok"
    assert marker not in "".join(r.model_dump_json() for r in results)


@pytest.mark.parametrize("failure", [PermissionError, TimeoutError, ArtifactStoreError])
def test_cleanup_error_or_timeout_does_not_release_disk_budget(lifecycle, monkeypatch, failure):
    app, client, root, engine, maintenance, _ = lifecycle
    owner, *_ = scope(engine)
    job = upload(client, owner).json()
    key = artifact(engine, job)
    expire(engine, job)
    original = app.state.import_workflow._store.delete

    def fail(_key):
        raise failure("synthetic private cleanup error")

    monkeypatch.setattr(app.state.import_workflow._store, "delete", fail)
    first = maintenance.run()
    assert first.status == "failed" and first.cleanup_failures >= 1
    assert (root / (key + ".bin")).exists()
    assert first.occupancy["charged_storage_bytes"] > 0
    monkeypatch.setattr(app.state.import_workflow._store, "delete", original)
    second = maintenance.run()
    assert second.status == "ok" and second.occupancy["charged_storage_bytes"] == 0


def test_unreadable_maintenance_fence_is_failure_not_busy(lifecycle, monkeypatch):
    _, _, _, _, maintenance, _ = lifecycle

    def denied(*args, **kwargs):
        raise PermissionError("synthetic permission fault")

    monkeypatch.setattr(os, "open", denied)
    assert maintenance.run().status == "failed"


def crash_after_unlink(config, target_key):
    settings_value = Settings(**config)
    database = Database(settings_value)
    store = LocalFilesystemImportArtifactStore(settings_value.chat_import_artifact_root)
    original = store.delete

    def crashing(key):
        original(key)
        if key == target_key:
            os._exit(29)  # Actual owned process dies before metadata transaction commit.

    store.delete = crashing
    workflow = ImportWorkflowService(database.session, store, 72)
    MaintenanceService(ResourceAdmission(database, settings_value), workflow).run()


def test_actual_maintenance_process_crash_after_unlink_reconciles(lifecycle):
    _, client, root, engine, maintenance, config = lifecycle
    owner, *_ = scope(engine)
    job = upload(client, owner).json()
    key = artifact(engine, job)
    expire(engine, job)
    process = multiprocessing.get_context("spawn").Process(
        target=crash_after_unlink, args=(config.model_dump(), key)
    )
    process.start()
    try:
        process.join(15)
        assert process.exitcode == 29
    finally:
        if process.is_alive():
            process.terminate()
            process.join(10)
    assert not (root / (key + ".bin")).exists()
    with Session(engine) as db:
        assert db.get(ChatImportArtifact, UUID(job["artifact_id"])).state == "active"
    results = []
    loop = MaintenanceLoop(maintenance, interval_seconds=0.01)
    loop.run(Event(), iterations=2, report=results.append)
    assert loop.failures == 0 and results[-1].occupancy["charged_storage_bytes"] == 0
    assert upload(client, owner).status_code == 201
