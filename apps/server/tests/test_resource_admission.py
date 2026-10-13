"""9C: signed real TCP, shared PostgreSQL, isolated files and spawned workers."""

import errno
import multiprocessing
import socket
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import monotonic, sleep
from uuid import uuid4

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient
from sqlalchemy import text
from test_agent_rest import headers, settings
from test_import_api import bind, finalize, scope, transcript, upload

from app.core.config import Settings
from app.db.models import UploadReservation
from app.db.session import Database
from app.main import create_app
from app.services.resource_admission import AdmissionRejected, ResourceAdmission


def controlled_rate_clock(original_scalar, read_clock):
    def scalar(self, statement, *args, **kwargs):
        result = original_scalar(self, statement, *args, **kwargs)
        if str(statement) == "SELECT extract(epoch FROM clock_timestamp())":
            return read_clock()
        return result

    return scalar


def serve(config, port, fault=None, event=None, marker=None, rate_epoch=None):
    if rate_epoch is not None:
        from sqlalchemy.orm import Session

        # Spawned workers use the same controlled minute; SQL/transactions,
        # sockets, signatures, counters and storage remain real.
        Session.scalar = controlled_rate_clock(Session.scalar, lambda: rate_epoch)
    app = create_app(Settings(**config))
    if fault == "artifact":
        original = app.state.import_workflow.register_uploaded

        def paused(*args, **kwargs):
            event.set()
            sleep(30)  # Parent terminates this owned worker at the crash window.
            return original(*args, **kwargs)

        app.state.import_workflow.register_uploaded = paused
    if fault in {"partial", "disk"}:
        from app.chat_import.artifacts import _LocalWriter

        original_write = _LocalWriter.write

        def injected(self, chunk):
            if fault == "disk":
                raise OSError(errno.ENOSPC, marker)
            original_write(self, chunk)
            self._file.flush()
            event.set()
            sleep(30)  # Parent terminates this owned worker at the crash window.

        _LocalWriter.write = injected
    if fault == "spooling":
        import starlette.formparsers as forms

        spool_root = Path(config["chat_import_artifact_root"]).parent / f".spools-{port}"
        spool_root.mkdir()
        original_spool = forms.SpooledTemporaryFile

        def observed_spool(*args, **kwargs):
            file = original_spool(*args, dir=spool_root, **kwargs)
            original_rollover = file.rollover

            def rollover():
                original_rollover()
                event.set()

            file.rollover = rollover
            return file

        forms.SpooledTemporaryFile = observed_spool
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        access_log=False,
        log_level="error",
        timeout_graceful_shutdown=1,
    )


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def worker_pair(database_engine, tmp_path):
    processes = []
    databases = []

    def start(**options):
        fault = options.pop("fault", None)
        marker = options.pop("marker", None)
        rate_epoch = options.pop("rate_epoch", None)
        event = multiprocessing.get_context("spawn").Event()
        limits = dict(
            max_chat_import_bytes=4096,
            admission_uploads_global=2,
            admission_uploads_owner=1,
            admission_min_free_bytes=0,
            admission_body_idle_seconds=3,
            admission_body_total_seconds=8,
        )
        limits.update(options)
        config = settings(
            database_engine, chat_import_artifact_root=tmp_path / uuid4().hex, **limits
        )
        # Create the root in the parent so operator reconciliation is independent
        # of worker startup. Credentials travel through spawn pipes, not argv.
        config.chat_import_artifact_root.mkdir()
        database = Database(config)
        databases.append(database)
        admission = ResourceAdmission(database, config)
        ports = []
        for index in range(2):
            port = free_port()
            proc = multiprocessing.get_context("spawn").Process(
                target=serve,
                args=(
                    config.model_dump(),
                    port,
                    fault if index == 0 else None,
                    event,
                    marker,
                    rate_epoch,
                ),
            )
            proc.start()
            proc._phase9c_event = event
            processes.append(proc)
            ports.append(port)
            deadline = monotonic() + 15
            while monotonic() < deadline:
                try:
                    if (
                        httpx.get(
                            f"http://127.0.0.1:{port}/health", timeout=0.3, trust_env=False
                        ).status_code
                        == 200
                    ):
                        break
                except httpx.HTTPError:
                    sleep(0.05)
            else:
                pytest.fail("Synthetic HTTP worker did not start")
        return config, admission, ports, processes[-2:]

    yield start
    for proc in processes:
        if proc.is_alive():
            proc.terminate()
        proc.join(timeout=5)
        assert not proc.is_alive(), "Owned test worker did not terminate"
    for database in databases:
        database.dispose()


def slow_socket(port, owner):
    sock = socket.create_connection(("127.0.0.1", port), timeout=5)
    # Send a valid signed credential privately, with an unfinished multipart.
    token = headers(owner)["Authorization"]
    sock.sendall(
        (
            f"POST /api/v1/chat-imports HTTP/1.1\r\nHost: localhost\r\nAuthorization: {token}\r\n"
            "Content-Type: multipart/form-data; boundary=slow\r\nContent-Length: 2048\r\n"
            "Connection: close\r\n\r\n--slow\r\n"
        ).encode()
    )
    return sock


def wait_active(admission, count):
    deadline = monotonic() + 4
    while monotonic() < deadline:
        if admission.snapshot()["active_uploads"] == count:
            return
        sleep(0.03)
    pytest.fail("Admission did not reach expected aggregate occupancy")


def api(port):
    return httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=5, trust_env=False)


def test_real_two_workers_owner_global_limits_disconnect_and_recovery(worker_pair, database_engine):
    config, admission, ports, _ = worker_pair()
    a, *_ = scope(database_engine)
    b, *_ = scope(database_engine)
    c, *_ = scope(database_engine)
    first = slow_socket(ports[0], a)
    second = None
    try:
        wait_active(admission, 1)
        with api(ports[1]) as client:
            rejected = upload(client, a)
            assert rejected.status_code == 503 and rejected.headers["retry-after"] == "1"
            assert (
                str(a) not in rejected.text
                and str(config.chat_import_artifact_root) not in rejected.text
            )
        second = slow_socket(ports[1], b)
        wait_active(admission, 2)
        with api(ports[0]) as client:
            assert upload(client, c).status_code == 503
        assert (
            admission.snapshot()["reserved_storage_bytes"] == 2 * admission.upload_reservation_bytes
        )
    finally:
        first.close()
        if second:
            second.close()
    wait_active(admission, 0)
    with api(ports[1]) as client:
        result = upload(client, a)
        assert result.status_code == 201
        assert (
            client.post(
                f"/api/v1/chat-imports/{result.json()['id']}/cancel", headers=headers(a)
            ).status_code
            == 200
        )
    assert admission.snapshot()["charged_storage_bytes"] == 0


@pytest.mark.parametrize("mode", ["idle", "total"])
def test_real_body_idle_and_total_deadline(worker_pair, database_engine, mode):
    config, admission, ports, _ = worker_pair(
        **(
            {"admission_body_idle_seconds": 0.25}
            if mode == "idle"
            else {"admission_body_total_seconds": 0.5}
        )
    )
    owner, *_ = scope(database_engine)
    sock = slow_socket(ports[0], owner)
    started = monotonic()
    try:
        if mode == "total":
            for _ in range(4):
                sleep(0.09)
                try:
                    sock.sendall(b"x")
                except OSError:
                    break
        response = sock.recv(4096)
        assert b"408 Request Timeout" in response
        assert monotonic() - started < 2
    finally:
        sock.close()
    wait_active(admission, 0)
    assert list(config.chat_import_artifact_root.iterdir()) == []
    with api(ports[1]) as client:
        assert upload(client, owner).status_code == 201


def test_real_worker_kill_recovers_without_expiring_a_live_owner(worker_pair, database_engine):
    _, admission, ports, processes = worker_pair()
    owner, *_ = scope(database_engine)
    sock = slow_socket(ports[0], owner)
    try:
        wait_active(admission, 1)
        processes[0].terminate()
        processes[0].join(timeout=5)
        assert not processes[0].is_alive()
        wait_active(admission, 0)
        with api(ports[1]) as client:
            assert upload(client, owner).status_code == 201
    finally:
        sock.close()


def test_real_shared_rate_windows_and_owner_isolation(worker_pair, database_engine):
    _, admission, ports, _ = worker_pair(
        admission_owner_uploads_per_minute=1, rate_epoch=1900000000.0
    )
    a, *_ = scope(database_engine)
    b, *_ = scope(database_engine)
    with api(ports[0]) as first, api(ports[1]) as second:
        assert upload(first, a).status_code == 201
        refused = upload(second, a)
        assert refused.status_code == 429 and int(refused.headers["retry-after"]) >= 1
        assert upload(second, b).status_code == 201
    assert admission.snapshot()["active_uploads"] == 0


@pytest.fixture
def quota_api(database_engine, tmp_path):
    def make(**overrides):
        config = settings(
            database_engine,
            chat_import_artifact_root=tmp_path / uuid4().hex,
            max_chat_import_bytes=4096,
            admission_min_free_bytes=0,
            **overrides,
        )
        app = create_app(config)
        return app, TestClient(app, raise_server_exceptions=False)

    return make


@pytest.mark.parametrize("budget", ["owner", "global"])
def test_storage_includes_retained_sources_and_releases_on_cancel(
    quota_api, database_engine, budget
):
    reserve = 2 * 4096 + 1024**2 + 16384
    app, client = quota_api(**{f"admission_storage_{budget}_bytes": reserve + 4096})
    a, *_ = scope(database_engine)
    b, *_ = scope(database_engine)
    result = upload(client, a)
    assert result.status_code == 201
    assert upload(client, a if budget == "owner" else b).status_code == 503
    if budget == "owner":
        assert upload(client, b).status_code == 201
    assert (
        client.post(
            f"/api/v1/chat-imports/{result.json()['id']}/cancel", headers=headers(a)
        ).status_code
        == 200
    )
    assert upload(client, a).status_code == 201
    assert app.state.resource_admission.snapshot()["active_uploads"] == 0


def test_pending_job_limit_and_form_inventory_before_disk(quota_api, database_engine):
    app, client = quota_api(admission_pending_owner=1)
    owner, *_ = scope(database_engine)
    created = upload(client, owner)
    assert created.status_code == 201
    assert upload(client, owner).status_code == 503
    assert (
        client.post(
            f"/api/v1/chat-imports/{created.json()['id']}/cancel", headers=headers(owner)
        ).status_code
        == 200
    )
    response = client.post(
        "/api/v1/chat-imports",
        headers=headers(owner),
        data={"source_timezone": "Asia/Shanghai"},
        files=[("file", ("a", transcript())), ("file", ("b", transcript()))],
    )
    assert response.status_code == 400
    assert app.state.resource_admission.snapshot()["active_uploads"] == 0
    assert list(app.state.import_artifact_store._root.iterdir()) == []


def test_atomic_concurrent_reservations_and_live_database_loss(quota_api, database_engine):
    app, _ = quota_api(admission_uploads_global=1, admission_uploads_owner=1)
    admission = app.state.resource_admission
    owners = [scope(database_engine)[0] for _ in range(6)]

    def acquire(owner):
        try:
            return admission.acquire(owner)
        except AdmissionRejected:
            return None

    with ThreadPoolExecutor(max_workers=6) as executor:
        leases = list(executor.map(acquire, owners))
    held = [lease for lease in leases if lease]
    assert len(held) == 1
    lease = held[0]
    # A DB backend terminated while its process/fence is live cannot grant a
    # second reservation. This specifically prevents unsafe lease reclamation.
    pid = lease.connection.scalar(text("SELECT pg_backend_pid()"))
    lease.connection.commit()
    with database_engine.begin() as db:
        db.execute(text("SELECT pg_terminate_backend(:pid)"), {"pid": pid})
    with pytest.raises(AdmissionRejected):
        admission.acquire(owners[-1])
    admission.release(lease)
    recovered = admission.acquire(owners[-1])
    admission.release(recovered)
    assert admission.snapshot()["active_uploads"] == 0


def test_unknown_orphan_fails_closed_and_crash_artifact_stays_charged(quota_api, database_engine):
    app, client = quota_api()
    owner, *_ = scope(database_engine)
    admission = app.state.resource_admission
    lease = admission.acquire(owner)
    path = app.state.import_artifact_store._root / f"{lease.artifact_key}.part"
    path.write_bytes(transcript())
    # Equivalent abandoned connection and OS handle, with a real residual file.
    lease.connection.invalidate()
    lease.connection.close()
    lease.fence.close()
    assert admission.snapshot()["active_uploads"] == 0
    assert admission.snapshot()["charged_storage_bytes"] >= len(transcript())
    with app.state.database.session() as db:
        row = db.get(UploadReservation, lease.id)
        assert row is not None and not row.active
    path.unlink()
    assert admission.snapshot()["charged_storage_bytes"] == 0
    unknown = app.state.import_artifact_store._root / f"{uuid4().hex}.bin"
    unknown.write_bytes(transcript())
    assert upload(client, owner).status_code == 503
    unknown.unlink()
    assert upload(client, owner).status_code == 201


@pytest.mark.parametrize("fault", ["begin", "write", "database", "parser"])
def test_failure_paths_no_false_job_and_recovered_capacity(
    quota_api, database_engine, monkeypatch, fault
):
    app, client = quota_api(admission_uploads_global=1)
    owner, *_ = scope(database_engine)
    marker = uuid4().hex
    original = Path.open
    with monkeypatch.context() as patch:
        if fault == "begin":

            def fail(path, *args, **kwargs):
                if path.suffix == ".part":
                    raise OSError(errno.ENOSPC, marker)
                return original(path, *args, **kwargs)

            patch.setattr(Path, "open", fail)
        elif fault == "write":
            from app.chat_import.artifacts import _LocalWriter

            def fail_write(*args):
                raise OSError(errno.ENOSPC, marker)

            patch.setattr(_LocalWriter, "write", fail_write)
        elif fault == "database":
            from sqlalchemy.exc import SQLAlchemyError

            from app.services.import_jobs import ImportJobService

            def fail_create(*args, **kwargs):
                raise SQLAlchemyError(marker)

            patch.setattr(ImportJobService, "create", fail_create)
        response = upload(client, owner, content=b"not markdown" if fault == "parser" else None)
        assert response.status_code in {415, 503}
        assert marker not in response.text
    assert app.state.resource_admission.snapshot()["active_uploads"] == 0
    assert list(app.state.import_artifact_store._root.iterdir()) == []
    assert upload(client, owner).status_code == 201


def test_finalize_replay_cancel_race_and_accounting(quota_api, database_engine):
    app, client = quota_api()
    owner, person, relationship, _ = scope(database_engine)
    ready = bind(client, owner, upload(client, owner).json(), person, relationship)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(finalize, client, owner, ready)
        cancel = executor.submit(
            client.post, f"/api/v1/chat-imports/{ready['id']}/cancel", headers=headers(owner)
        )
        response, cancelled = first.result(), cancel.result()
    assert response.status_code in {200, 409} and cancelled.status_code in {200, 409}
    if response.status_code == 200:
        assert finalize(client, owner, ready).json() == response.json()
    assert app.state.resource_admission.snapshot()["active_processing"] == 0
    assert app.state.resource_admission.snapshot()["charged_storage_bytes"] == 0


def test_changed_worker_policy_fails_closed(quota_api, database_engine):
    app, _ = quota_api()
    owner, *_ = scope(database_engine)
    lease = app.state.resource_admission.acquire(owner)
    changed = app.state.settings.model_copy(update={"admission_uploads_global": 50})
    second = ResourceAdmission(app.state.database, changed)
    with pytest.raises(AdmissionRejected):
        second.acquire(owner)
    app.state.resource_admission.release(lease)


@pytest.mark.parametrize("stage", ["partial", "artifact"])
def test_real_worker_crash_during_write_and_before_job_commit(worker_pair, database_engine, stage):
    config, admission, ports, processes = worker_pair(fault=stage)
    owner, *_ = scope(database_engine)

    def request():
        with api(ports[0]) as client:
            try:
                result = upload(client, owner)
            except httpx.HTTPError:
                return "disconnected"
        return result.status_code

    with ThreadPoolExecutor(max_workers=1) as executor:
        response = executor.submit(request)
        assert processes[0]._phase9c_event.wait(5)
        wait_active(admission, 1)
        processes[0].terminate()
        processes[0].join(timeout=5)
        outcome = response.result(timeout=5)
        assert outcome == "disconnected" or (isinstance(outcome, int) and outcome >= 400)
        assert not processes[0].is_alive() and processes[0].exitcode is not None
        print(f"Synthetic crash window {stage}: client outcome {outcome}")
    from sqlalchemy import func, select

    from app.db.models import ChatImportJob

    with admission.database.session() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(ChatImportJob)
                .where(ChatImportJob.owner_user_id == owner)
            )
            == 0
        )
    wait_active(admission, 0)
    assert admission.snapshot()["charged_storage_bytes"] >= len(transcript())
    from datetime import UTC, datetime, timedelta

    from app.chat_import.artifacts import LocalFilesystemImportArtifactStore
    from app.services.import_workflow import ImportWorkflowService

    workflow = ImportWorkflowService(
        admission.database.session,
        LocalFilesystemImportArtifactStore(config.chat_import_artifact_root),
        72,
    )
    workflow.cleanup_expired(now=datetime.now(UTC) + timedelta(hours=2))
    assert admission.snapshot()["charged_storage_bytes"] == 0
    with api(ports[1]) as client:
        assert upload(client, owner).status_code == 201


def test_real_http_storage_budget_rate_global_disk_failure_and_restored_capacity(
    worker_pair, database_engine
):
    reserve = 2 * 4096 + 1024**2 + 16384
    marker = uuid4().hex
    _, admission, ports, _ = worker_pair(
        fault="disk",
        marker=marker,
        admission_storage_global_bytes=reserve + 4096,
        admission_uploads_per_minute=3,
        rate_epoch=1900000000.0,
    )
    owner, *_ = scope(database_engine)
    with api(ports[0]) as failing, api(ports[1]) as healthy:
        response = upload(failing, owner)
        assert response.status_code == 503 and marker not in response.text
        assert admission.snapshot()["charged_storage_bytes"] == 0
        created = upload(healthy, owner)
        assert created.status_code == 201
        assert upload(healthy, scope(database_engine)[0]).status_code == 503
        rejected = upload(failing, scope(database_engine)[0])
        assert rejected.status_code == 429 and int(rejected.headers["retry-after"]) > 0
        # Upload-specific rate exhaustion cannot obstruct inspection/cancel or
        # guarded Memory/Agent history through the general request budget.
        assert healthy.get("/api/v1/memory/control", headers=headers(owner)).status_code == 200
        assert (
            healthy.get(
                f"/api/v1/chat-imports/{created.json()['id']}", headers=headers(owner)
            ).status_code
            == 200
        )
        assert (
            healthy.post(
                f"/api/v1/chat-imports/{created.json()['id']}/cancel", headers=headers(owner)
            ).status_code
            == 200
        )
    assert admission.snapshot()["active_uploads"] == 0


def test_early_invalid_credential_does_not_receive_or_spool(quota_api):
    app, client = quota_api()
    received = []

    def content():
        received.append(True)
        yield b"private runtime input"

    result = client.post(
        "/api/v1/chat-imports",
        content=content(),
        headers={"Content-Type": "multipart/form-data; boundary=x"},
    )
    assert result.status_code == 401 and received == []
    assert list(app.state.import_artifact_store._root.iterdir()) == []


def test_generic_request_rate_is_shared_across_workers(worker_pair, database_engine):
    _, _, ports, _ = worker_pair(admission_requests_per_minute=1, rate_epoch=1900000000.0)
    owner, *_ = scope(database_engine)
    with api(ports[0]) as first, api(ports[1]) as second:
        assert first.get("/api/v1/persons", headers=headers(owner)).status_code == 200
        assert second.get("/api/v1/persons", headers=headers(owner)).status_code == 429
        assert second.get("/health").status_code == 200


def test_real_database_unavailability_is_safe_and_does_not_read_body(worker_pair, database_engine):
    from pydantic import SecretStr

    invalid = SecretStr(database_engine.url.set(port=9).render_as_string(hide_password=False))
    config, _, ports, _ = worker_pair(database_url=invalid)
    owner, *_ = scope(database_engine)
    with api(ports[0]) as client:
        result = upload(client, owner)
        assert result.status_code == 503
        assert str(config.chat_import_artifact_root) not in result.text
        assert result.json()["error"]["code"] == "artifact_unavailable"
    assert list(config.chat_import_artifact_root.iterdir()) == []


def test_live_fence_protects_old_partial_and_cleanup_fault_stays_charged(
    quota_api, database_engine, monkeypatch
):
    import os
    from datetime import UTC, datetime, timedelta

    from app.chat_import.artifacts import ArtifactStoreError

    app, client = quota_api()
    owner, *_ = scope(database_engine)
    admission = app.state.resource_admission
    lease = admission.acquire(owner)
    path = app.state.import_artifact_store._root / f"{lease.artifact_key}.part"
    path.write_bytes(transcript())
    old = (datetime.now(UTC) - timedelta(hours=2)).timestamp()
    os.utime(path, (old, old))
    app.state.import_workflow.cleanup_expired()
    assert path.exists() and admission.snapshot()["active_uploads"] == 1
    admission.release(lease)
    app.state.import_workflow.cleanup_expired()
    assert not path.exists() and admission.snapshot()["charged_storage_bytes"] == 0
    created = upload(client, owner).json()
    with monkeypatch.context() as patch:

        def fail_delete(*args):
            raise ArtifactStoreError

        patch.setattr(app.state.import_artifact_store, "delete", fail_delete)
        result = client.post(f"/api/v1/chat-imports/{created['id']}/cancel", headers=headers(owner))
        assert result.status_code == 200
        assert admission.snapshot()["charged_storage_bytes"] >= len(transcript())
    app.state.import_workflow.cleanup_expired()
    assert admission.snapshot()["charged_storage_bytes"] == 0


def test_speaker_inventory_rejected_without_partial_job_and_metrics_whitelist(
    quota_api, database_engine
):
    import json

    from app.chat_import import ChatImportSource, ImportOptions, WeChatMarkdownParser

    app, client = quota_api(max_chat_import_speakers=2)
    owner, *_ = scope(database_engine)
    content = b"".join(f"## 2023-11-09 07:51:23 synthetic-{i}\nbody\n".encode() for i in range(3))
    assert upload(client, owner, content=content).status_code == 422
    assert upload(client, owner).status_code == 201
    assert list(app.state.import_artifact_store._root.glob("*.part")) == []
    marker = uuid4().hex
    with pytest.raises(ValueError):
        app.state.resource_admission.record(marker)
    snapshot = app.state.resource_admission.snapshot()
    assert marker not in json.dumps(snapshot) and str(owner) not in json.dumps(snapshot)
    assert set(snapshot) == {
        "active_uploads",
        "active_processing",
        "charged_storage_bytes",
        "unattributed_storage_bytes",
        "reserved_storage_bytes",
        "worker_events",
    }
    assert (
        WeChatMarkdownParser()
        .parse(ChatImportSource([content]), ImportOptions(source_timezone="UTC"))
        .message_count
        == 3
    )


def test_two_workers_simultaneously_compete_for_one_global_slot(worker_pair, database_engine):
    import select
    from threading import Barrier

    _, admission, ports, _ = worker_pair(admission_uploads_global=1)
    owners = [scope(database_engine)[0] for _ in range(2)]
    barrier = Barrier(2)

    def request(index):
        barrier.wait(timeout=5)
        return slow_socket(ports[index], owners[index])

    with ThreadPoolExecutor(max_workers=2) as executor:
        sockets = list(executor.map(request, range(2)))
    try:
        ready, _, _ = select.select(sockets, [], [], 1)
        assert len(ready) == 1
        assert b"503 Service Unavailable" in ready[0].recv(4096)
        wait_active(admission, 1)
        assert admission.snapshot()["reserved_storage_bytes"] == admission.upload_reservation_bytes
    finally:
        for sock in sockets:
            sock.close()
    wait_active(admission, 0)
    with api(ports[1]) as client:
        assert upload(client, owners[1]).status_code == 201


def test_owner_rejected_attempts_still_count_toward_global_rate(
    quota_api, database_engine, monkeypatch
):
    from sqlalchemy.orm import Session

    # Keep the invariant in one controlled minute. Real wall-clock rollover
    # legitimately accepts a second upload and is not a debit-rollback defect.
    # Execute the real PG clock query, but use a deterministic time in this test.
    clock = [1900000000.0]
    monkeypatch.setattr(Session, "scalar", controlled_rate_clock(Session.scalar, lambda: clock[0]))
    app, client = quota_api(admission_owner_uploads_per_minute=1, admission_requests_per_minute=3)
    owner, *_ = scope(database_engine)
    assert upload(client, owner).status_code == 201
    assert upload(client, owner).status_code == 429
    assert upload(client, owner).status_code == 429
    # A fourth protected request is refused by the global window despite the
    # previous two Owner rejections; no rollback may erase their attempts.
    assert (
        client.get("/api/v1/persons", headers=headers(scope(database_engine)[0])).status_code == 429
    )
    # The next minute resets the global/Owner counters exactly as documented.
    clock[0] += 60
    assert upload(client, owner).status_code == 201


def test_real_worker_death_closes_actual_rolled_multipart_spool(worker_pair, database_engine):
    config, admission, ports, processes = worker_pair(
        fault="spooling", max_chat_import_bytes=2 * 1024**2
    )
    owner, *_ = scope(database_engine)
    sock = socket.create_connection(("127.0.0.1", ports[0]), timeout=5)
    token = headers(owner)["Authorization"]
    request = (
        f"POST /api/v1/chat-imports HTTP/1.1\r\nHost: localhost\r\nAuthorization: {token}\r\n"
        "Content-Type: multipart/form-data; boundary=spool\r\nContent-Length: 2097152\r\n"
        "Connection: close\r\n\r\n--spool\r\nContent-Disposition: form-data; "
        'name="file"; filename="synthetic.md"\r\n\r\n'
    ).encode()
    try:
        sock.sendall(request + b"x" * (1100 * 1024))
        assert processes[0]._phase9c_event.wait(5)
        wait_active(admission, 1)
        processes[0].terminate()
        processes[0].join(timeout=5)
    finally:
        sock.close()
    wait_active(admission, 0)
    assert list((config.chat_import_artifact_root.parent / f".spools-{ports[0]}").iterdir()) == []
    assert admission.snapshot()["charged_storage_bytes"] == 0
    with api(ports[1]) as client:
        assert upload(client, owner).status_code == 201
