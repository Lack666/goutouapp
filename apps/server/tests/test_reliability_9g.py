"""Bounded PostgreSQL lock diagnosis, file publication and unresolved-run audits."""

import json
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import monotonic
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select, text
from sqlalchemy.orm import Session
from test_agent_rest import headers, settings
from test_erasure import erasure_api as audit_erasure  # noqa: F401
from test_erasure import target
from test_import_api import scope, upload
from test_resource_admission import api
from test_resource_admission import worker_pair as audit_workers  # noqa: F401

from app.db.models import (
    AgentRun,
    Conversation,
    MemoryRecordRow,
    Message,
    Person,
    UploadReservation,
)
from app.db.session import Database
from app.main import create_app
from app.services.agent_service import request_fingerprint
from app.services.resource_admission import AdmissionRejected, ResourceAdmission


@pytest.mark.parametrize("window", ["partial", "linked", "promoted", "vanished"])
def test_real_file_publication_is_fully_charged(database_engine, tmp_path, window):
    owner, *_ = scope(database_engine)
    config = settings(
        database_engine,
        max_chat_import_bytes=4096,
        chat_import_artifact_root=tmp_path / "artifacts",
        admission_min_free_bytes=0,
    )
    config.chat_import_artifact_root.mkdir()
    database = Database(config)
    admission = ResourceAdmission(database, config)
    lease = admission.acquire(owner)
    partial = admission.root / f"{lease.artifact_key}.part"
    final = partial.with_suffix(".bin")
    partial.write_bytes(b"synthetic")
    original = Path.lstat

    def promote(candidate, *args, **kwargs):
        if candidate == partial:
            os.link(partial, final)
            partial.unlink()
        return original(candidate, *args, **kwargs)

    try:
        if window in {"linked", "promoted"}:
            os.link(partial, final)
            if window == "promoted":
                partial.unlink()
        with patch.object(Path, "lstat", promote if window == "vanished" else original):
            snapshot = admission.snapshot()
        assert snapshot["active_uploads"] == 1
        assert snapshot["charged_storage_bytes"] == admission.upload_reservation_bytes
        assert snapshot["unattributed_storage_bytes"] == 0
        admission.release(lease)
        # Linked publication may charge both aliases conservatively after release.
        assert admission.snapshot()["charged_storage_bytes"] >= 8192
        partial.unlink(missing_ok=True)
        final.unlink(missing_ok=True)
        assert admission.snapshot()["charged_storage_bytes"] == 0
    finally:
        admission.release(lease)
        database.dispose()


@pytest.mark.parametrize("foreign", [False, True])
def test_unrelated_live_reservation_cannot_admit_unknown_disappearing_file(
    database_engine, tmp_path, foreign
):
    a, *_ = scope(database_engine)
    b, *_ = scope(database_engine)
    config = settings(
        database_engine, chat_import_artifact_root=tmp_path / "root", admission_min_free_bytes=0
    )
    config.chat_import_artifact_root.mkdir()
    database = Database(config)
    admission = ResourceAdmission(database, config)
    lease = admission.acquire(b if foreign else a)
    unknown = admission.root / (uuid4().hex + ".part")
    unknown.write_bytes(b"synthetic")
    original = Path.lstat

    def disappear(candidate, *args, **kwargs):
        if candidate == unknown:
            unknown.unlink()
        return original(candidate, *args, **kwargs)

    try:
        with patch.object(Path, "lstat", disappear), database.session() as db, db.begin():
            with pytest.raises(AdmissionRejected):
                admission._inventory(db)
        assert admission.snapshot()["reserved_storage_bytes"] == admission.upload_reservation_bytes
    finally:
        admission.release(lease)
        database.dispose()


def test_missing_active_file_retains_owner_charge_until_fence_release(database_engine, tmp_path):
    a, *_ = scope(database_engine)
    b, *_ = scope(database_engine)
    config = settings(
        database_engine,
        max_chat_import_bytes=4096,
        chat_import_artifact_root=tmp_path / "root",
        admission_min_free_bytes=0,
        admission_storage_owner_bytes=2 * 4096 + 1024**2 + 16384,
    )
    config.chat_import_artifact_root.mkdir()
    database = Database(config)
    admission = ResourceAdmission(database, config)
    lease = admission.acquire(a)
    other = None
    try:
        path = admission.root / f"{lease.artifact_key}.part"
        path.write_bytes(b"synthetic")
        path.unlink()
        with pytest.raises(AdmissionRejected):
            admission.acquire(a)
        other = admission.acquire(b)
        assert admission.snapshot()["active_uploads"] == 2
        assert (
            admission.snapshot()["reserved_storage_bytes"] == 2 * admission.upload_reservation_bytes
        )
    finally:
        if other:
            admission.release(other)
        admission.release(lease)
        assert admission.snapshot()["charged_storage_bytes"] == 0
        with database.session() as db:
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(UploadReservation)
                    .where(UploadReservation.scope_key == admission.scope_key)
                )
                == 0
            )
        database.dispose()


@pytest.mark.parametrize("different_owner", [False, True])
def test_person_503_has_real_55p03_bound_and_no_business_commit(
    database_engine, tmp_path, different_owner
):
    owner, *_ = scope(database_engine)
    b, *_ = scope(database_engine)
    config = settings(database_engine, chat_import_artifact_root=tmp_path / "root")
    app = create_app(config)
    errors = []

    def diagnose(context):
        errors.append(getattr(context.original_exception, "sqlstate", None))

    event.listen(app.state.database.engine(), "handle_error", diagnose)
    body = {"id": str(uuid4()), "display_name": "Synthetic lock diagnosis"}
    with TestClient(app) as client:
        with database_engine.connect() as holder, holder.begin():
            holder.execute(
                text("SELECT pg_advisory_xact_lock(:key)"),
                {"key": app.state.resource_admission.guard_key},
            )
            started = monotonic()
            response = client.post(
                "/api/v1/persons", headers=headers(b if different_owner else owner), json=body
            )
            elapsed = monotonic() - started
        assert response.status_code == 503
        assert response.headers["retry-after"] == "1"
        assert response.json()["error"]["code"] == "artifact_unavailable"
        assert errors == ["55P03"] and 0.20 <= elapsed < 3
        with Session(database_engine) as db:
            assert db.get(Person, UUID(body["id"])) is None
        # Explicit user retry retains the original UUID. No automatic HTTP retry.
        retry = client.post(
            "/api/v1/persons", headers=headers(b if different_owner else owner), json=body
        )
        assert retry.status_code == 201
        replay = client.post(
            "/api/v1/persons", headers=headers(b if different_owner else owner), json=body
        )
        assert replay.status_code == 201 and replay.json() == retry.json()
    print(
        json.dumps(
            {
                "diagnostic": "held_global_guard",
                "sqlstate": errors[0],
                "different_owner": different_owner,
                "elapsed_ms": round(elapsed * 1000),
                "rejected_no_row": True,
                "explicit_same_uuid_retry": 201,
            }
        )
    )


@pytest.mark.parametrize("same_owner", [False, True])
def test_bounded_cold_two_worker_person_upload_pressure(audit_workers, database_engine, same_owner):  # noqa: F811
    config, admission, ports, _ = audit_workers(admission_owner_requests_per_minute=200)
    a, *_ = scope(database_engine)
    b, *_ = scope(database_engine)
    owners = [a, a if same_owner else b]
    bodies = [{"id": str(uuid4()), "display_name": "Synthetic bounded pressure"} for _ in range(16)]

    def create(index):
        with api(ports[index % 2]) as client:
            response = client.post(
                "/api/v1/persons", headers=headers(owners[index % 2]), json=bodies[index]
            )
            return index, response.status_code

    def import_and_cancel():
        with api(ports[0]) as client:
            response = upload(client, a)
            assert response.status_code in {201, 503}
            if response.status_code == 201:
                result = client.post(
                    f"/api/v1/chat-imports/{response.json()['id']}/cancel", headers=headers(a)
                )
                assert result.status_code == 200
            return response.status_code

    started = monotonic()
    with ThreadPoolExecutor(max_workers=5) as pool:
        uploaded = pool.submit(import_and_cancel)
        results = list(pool.map(create, range(16)))
        upload_status = uploaded.result(timeout=15)
    assert monotonic() - started < 20
    counts = Counter(status for _, status in results)
    assert set(counts) <= {201, 503} and counts[201] > 0
    with Session(database_engine) as db:
        for index, status in results:
            row = db.get(Person, UUID(bodies[index]["id"]))
            assert (row is not None) == (status == 201)
            if row:
                assert row.user_id == owners[index % 2]
    assert admission.snapshot()["active_uploads"] == 0
    assert admission.snapshot()["charged_storage_bytes"] == 0
    print(
        json.dumps(
            {
                "diagnostic": "cold_two_worker_pressure",
                "same_owner": same_owner,
                "person_status_counts": dict(counts),
                "upload_status": upload_status,
                "elapsed_ms": round((monotonic() - started) * 1000),
                "automatic_retries": 0,
            }
        )
    )


@pytest.mark.parametrize(
    "state", ["pending", "running", "completed_unresolved", "failed", "completed"]
)
def test_old_run_restart_replay_owner_and_erasure_contract(audit_erasure, state, monkeypatch):  # noqa: F811
    engine, client, a, b, _, _, config = audit_erasure
    busy = state in {"pending", "running", "completed_unresolved"}
    with Session(engine) as db, db.begin():
        run = db.scalar(select(AgentRun).where(AgentRun.conversation_id == a[3]))
        run_id = run.id
        run.status = "completed" if state.startswith("completed") else state
        run.memory_status = None if busy else "none"
        run.updated_at = datetime.now(UTC) - timedelta(days=30)
        run.request_fingerprint = request_fingerprint(
            a[0], a[3], "Synthetic old request", None, None
        )
        run.failure_code = "client_disconnected" if state == "failed" else None

    # No provider is allowed during replay/status checks, including a restarted App.
    def forbidden(_):
        raise AssertionError("A replay must not dispatch provider work")

    monkeypatch.setattr("app.api.dependencies.create_llm_provider", forbidden)
    # Replays need an assembled service; runtime itself must stay unused.
    from app.services.agent_service import AgentService

    class NoRuntime:
        async def run(self, request):
            raise AssertionError("No run allowed")

    app = create_app(config)
    app.state.agent_service = AgentService(app.state.database.session, NoRuntime())
    path = f"/api/v1/conversations/{a[3]}/agent-runs"
    body = {"message": "Synthetic old request", "operation_key": "synthetic-original-key"}
    with TestClient(app) as restarted:
        for suffix in ("", "/stream"):
            response = restarted.post(path + suffix, headers=headers(a[0]), json=body)
            assert response.status_code == (200 if state == "completed" else 409)
            foreign = restarted.post(path + suffix, headers=headers(b[0]), json=body)
            assert foreign.status_code == 404
        preparation = restarted.post(
            "/api/v1/erasures/prepare",
            headers=headers(a[0]),
            json=target(audit_erasure, "conversation"),
        )
        assert preparation.status_code == (409 if busy else 200)
        if busy:
            assert preparation.json()["error"]["code"] == "target_busy"
    with Session(engine) as db:
        assert db.get(Conversation, a[3]).deleted_at is None
        assert (
            db.scalar(
                select(func.count()).select_from(AgentRun).where(AgentRun.conversation_id == a[3])
            )
            == 1
        )
        assert db.get(AgentRun, run_id).operation_key == body["operation_key"]
        assert (
            db.scalar(
                select(func.count()).select_from(Message).where(Message.conversation_id == a[3])
            )
            == 2
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(MemoryRecordRow)
                .where(MemoryRecordRow.owner_user_id == a[0])
            )
            == 1
        )
