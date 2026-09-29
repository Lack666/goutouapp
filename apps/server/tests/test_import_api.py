"""Phase 5D authenticated one-upload import and lifecycle acceptance."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Thread
from time import monotonic, sleep
from uuid import UUID

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import sessionmaker
from starlette.datastructures import UploadFile
from test_agent_rest import headers, settings
from test_agent_service import queue_safety, service_with_mock

from app.chat_import import ChatImportSource, ImportOptions, WeChatMarkdownParser
from app.chat_import.artifacts import (
    CHUNK_BYTES,
    ArtifactStoreError,
    LocalFilesystemImportArtifactStore,
)
from app.core.config import Settings
from app.db.models import ChatImportArtifact, ChatImportJob, MemoryRecordRow, RelationshipMessage
from app.db.repositories import records
from app.main import create_app
from app.services.agent_service import actor_from_verified_identity
from app.services.import_jobs import ImportJobError, ImportJobErrorCode, ImportJobService


def transcript(count: int = 2) -> bytes:
    start = datetime(2023, 11, 9, 7, 51, 23)
    return "".join(
        f"## {(start + timedelta(seconds=i)).strftime('%Y-%m-%d %H:%M:%S')} "
        f"{'我' if i % 2 == 0 else 'A'}\n\nsynthetic {i}\n"
        for i in range(count)
    ).encode()


def scope(engine):
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db, db.begin():
        user = records.create_user(db)
        person = records.create_person(db, user.id, "A")
        relationship = records.create_relationship(db, user.id, person.id, "dating", "active")
        conversation = records.create_conversation(db, user.id, relationship.id)
        return user.id, person.id, relationship.id, conversation.id


@pytest.fixture
def setup_api(database_engine, tmp_path):
    app = create_app(settings(database_engine, chat_import_artifact_root=tmp_path / "artifacts"))
    with TestClient(app) as client:
        yield app, client, tmp_path / "artifacts"


def upload(client, user, *, content=None, filename="chat.md", source_timezone="Asia/Shanghai"):
    return client.post(
        "/api/v1/chat-imports",
        headers=headers(user),
        data={"source_timezone": source_timezone},
        files={
            "file": (
                filename,
                transcript() if content is None else content,
                "application/octet-stream",
            )
        },
    )


def bind(client, user, job, person, relationship):
    path = f"/api/v1/chat-imports/{job['id']}"
    revision = job["binding_revision"]
    for label, kind, person_id in (("我", "self", None), ("A", "person", person)):
        result = client.put(
            path + "/speakers",
            headers=headers(user),
            json={
                "raw_speaker_label": label,
                "binding_kind": kind,
                "person_id": str(person_id) if person_id else None,
                "expected_revision": revision,
            },
        )
        assert result.status_code == 200, result.text
        revision = result.json()["binding_revision"]
    result = client.put(
        path + "/relationship",
        headers=headers(user),
        json={"relationship_id": str(relationship), "expected_revision": revision},
    )
    assert result.status_code == 200, result.text
    ready = client.post(path + "/ready", headers=headers(user))
    assert ready.status_code == 200, ready.text
    return ready.json()


def finalize(client, user, job):
    return client.post(
        f"/api/v1/chat-imports/{job['id']}/finalize",
        headers=headers(user),
        json={"expected_revision": job["binding_revision"]},
    )


def test_artifact_store_immutable_traversal_and_orphan_cleanup(tmp_path):
    store = LocalFilesystemImportArtifactStore(tmp_path)
    writer = store.begin()
    writer.write(b"synthetic")
    artifact = writer.finish()
    assert store.exists(artifact.key)
    assert store.stat(artifact.key).st_size == 9
    with store.open(artifact.key) as stream:
        assert stream.read() == b"synthetic"
    with pytest.raises(ArtifactStoreError):
        writer.write(b"changed")
    for key in ("../secret", "C:\\secret", "0" * 31 + "/"):
        with pytest.raises(ArtifactStoreError):
            store.open(key)
    old = datetime.now(UTC) + timedelta(seconds=1)
    assert store.cleanup_expired(set(), old) == 1
    assert not store.exists(artifact.key)
    interrupted = store.begin()
    interrupted.write(b"partial")
    interrupted.abort()
    assert list(tmp_path.iterdir()) == []
    orphan = tmp_path / ("a" * 32 + ".part")
    orphan.write_bytes(b"crash fragment")
    assert store.cleanup_expired(set(), old) == 1
    assert not orphan.exists()


def test_artifact_cannot_be_bound_to_another_owner(setup_api, database_engine):
    _app, client, _root = setup_api
    owner, _, _, _ = scope(database_engine)
    outsider, _, _, _ = scope(database_engine)
    uploaded = upload(client, owner)
    assert uploaded.status_code == 201
    artifact_id = UUID(uploaded.json()["artifact_id"])
    parsed = WeChatMarkdownParser().parse(
        ChatImportSource([transcript()]),
        ImportOptions(source_timezone="Asia/Shanghai", include_messages=False),
    )
    with sessionmaker(bind=database_engine)() as db, db.begin():
        with pytest.raises(ImportJobError) as caught:
            ImportJobService(db).create(
                actor_from_verified_identity(outsider), parsed, artifact_id=artifact_id
            )
        assert caught.value.code == ImportJobErrorCode.INVALID_PARSE_RESULT


def test_oversized_multipart_rejected_before_form_spooling(tmp_path, monkeypatch):
    app = create_app(
        Settings(
            max_chat_import_bytes=100,
            chat_import_artifact_root=tmp_path / "early-limit",
            _env_file=None,
        )
    )
    reads = []
    original = UploadFile.read

    async def measured(self, size=-1):
        reads.append(size)
        return await original(self, size)

    monkeypatch.setattr(UploadFile, "read", measured)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat-imports",
            data={"source_timezone": "Asia/Shanghai"},
            files={"file": ("large.md", b"x" * (2 * 1024 * 1024))},
        )
    assert response.status_code == 413, response.text
    assert response.json()["error"]["code"] == "upload_too_large"
    assert reads == [] and list((tmp_path / "early-limit").iterdir()) == []


def test_chunked_multipart_body_limit(tmp_path):
    root = tmp_path / "chunked-limit"
    app = create_app(
        Settings(max_chat_import_bytes=100, chat_import_artifact_root=root, _env_file=None)
    )

    def body():
        yield (
            b"--limit-boundary\r\nContent-Disposition: form-data; "
            b'name="file"; filename="large.md"\r\nContent-Type: text/plain\r\n\r\n'
        )
        for _ in range(20):
            yield b"x" * 65536
        yield b"\r\n--limit-boundary--\r\n"

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat-imports",
            content=body(),
            headers={"Content-Type": "multipart/form-data; boundary=limit-boundary"},
        )
    assert response.status_code == 413, response.text
    assert response.json()["error"]["code"] == "upload_too_large"
    assert list(root.iterdir()) == []


def test_full_http_workflow_replay_duplicate_pagination_and_agent_isolation(
    setup_api, database_engine
):
    app, client, root = setup_api
    user, person, relationship, conversation = scope(database_engine)
    other, _, _, _ = scope(database_engine)
    invalid = client.post(
        "/api/v1/chat-imports",
        headers={"Authorization": "Bearer bad"},
        data={"source_timezone": "Asia/Shanghai"},
        files={"file": ("x", transcript())},
    )
    assert invalid.status_code == 401 and list(root.iterdir()) == []
    response = upload(client, user, filename="../../secret.txt")
    assert response.status_code == 201, response.text
    job = response.json()
    assert job["status"] == "awaiting_binding" and job["message_count"] == 2
    assert {speaker["raw_speaker_label"] for speaker in job["speakers"]} == {"我", "A"}
    assert len(list(root.glob("*.bin"))) == 1
    assert not (root.parent / "secret.txt").exists()
    assert (
        client.post(f"/api/v1/chat-imports/{job['id']}/ready", headers=headers(user)).status_code
        == 409
    )
    for suffix in ("", "/ready", "/cancel"):
        method = client.get if not suffix else client.post
        response = method(f"/api/v1/chat-imports/{job['id']}{suffix}", headers=headers(other))
        assert response.status_code == 404
    assert (
        client.post(
            f"/api/v1/chat-imports/{job['id']}/finalize",
            headers=headers(other),
            json={"expected_revision": 0},
        ).status_code
        == 404
    )
    ready = bind(client, user, job, person, relationship)
    assert ready["status"] == "ready" and ready["readiness_issues"] == []
    result = finalize(client, user, ready)
    assert result.status_code == 200, result.text
    assert result.json()["new_message_count"] == 2
    assert list(root.glob("*.bin")) == []
    imported = client.get(f"/api/v1/chat-imports/{job['id']}", headers=headers(user)).json()
    assert imported["artifact_state"] == "deleted" and imported["imported_message_count"] == 2
    assert imported["receipt"]["imported_message_count"] == 2
    replay = finalize(client, user, ready)
    assert replay.status_code == 200 and replay.json()["new_message_count"] == 0
    assert replay.json()["imported_at"] == result.json()["imported_at"]
    page1 = client.get(
        f"/api/v1/relationships/{relationship}/messages", headers=headers(user), params={"limit": 1}
    )
    assert page1.status_code == 200, page1.text
    assert len(page1.json()["items"]) == 1 and page1.json()["next_cursor"]
    page2 = client.get(
        f"/api/v1/relationships/{relationship}/messages",
        headers=headers(user),
        params={"limit": 1, "cursor": page1.json()["next_cursor"]},
    )
    assert page2.status_code == 200 and len(page2.json()["items"]) == 1
    assert page2.json()["next_cursor"] is None
    assert (
        client.get(
            f"/api/v1/relationships/{relationship}/messages", headers=headers(other)
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/relationships/{relationship}/messages",
            headers=headers(user),
            params={"limit": 201},
        ).status_code
        == 422
    )
    second = upload(client, user).json()
    duplicate = finalize(client, user, bind(client, user, second, person, relationship))
    assert duplicate.status_code == 200 and duplicate.json()["new_message_count"] == 0
    assert duplicate.json()["dataset_job_id"] == job["id"]
    assert app.state.agent_service is None  # No Agent/LLM was composed by import.
    service, provider, spy = service_with_mock(database_engine)
    queue_safety(provider)
    app.state.agent_service = service
    agent = client.post(
        f"/api/v1/conversations/{conversation}/agent-runs",
        headers=headers(user),
        json={"message": "有人正在伤害我"},
    )
    assert agent.status_code == 200, agent.text
    assert spy.requests[0].recent_messages == []
    with sessionmaker(bind=database_engine)() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(RelationshipMessage)
                .where(RelationshipMessage.relationship_id == relationship)
            )
            == 2
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(MemoryRecordRow)
                .where(MemoryRecordRow.owner_user_id == user)
            )
            == 0
        )


def test_rejections_cleanup_tamper_cancel_expire_and_failure_retention(setup_api, database_engine):
    app, client, root = setup_api
    user, person, relationship, _ = scope(database_engine)
    assert upload(client, user, content=b"\xff").json()["error"]["code"] == "parse_failed"
    assert list(root.glob("*.bin")) == []
    app.state.settings.max_chat_import_bytes = 100
    oversized = upload(client, user, content=transcript(10))
    assert oversized.status_code == 413 and oversized.json()["error"]["code"] == "upload_too_large"
    assert list(root.glob("*.part")) == []
    app.state.settings.max_chat_import_bytes = 100 * 1024 * 1024
    cancel_job = upload(client, user).json()
    assert (
        client.post(
            f"/api/v1/chat-imports/{cancel_job['id']}/cancel", headers=headers(user)
        ).status_code
        == 200
    )
    assert list(root.glob("*.bin")) == []
    tamper = bind(client, user, upload(client, user).json(), person, relationship)
    artifact_path = next(root.glob("*.bin"))
    artifact_path.write_bytes(transcript().replace(b"synthetic 0", b"changed 0"))
    mismatch = finalize(client, user, tamper)
    assert mismatch.status_code == 409 and mismatch.json()["error"]["code"] == "transcript_mismatch"
    assert artifact_path.exists()
    # Restore the source; a database failure must retain it and roll back all formal rows.
    artifact_path.write_bytes(transcript())
    with database_engine.begin() as connection:
        connection.execute(
            text(
                "CREATE FUNCTION phase5d_reject() RETURNS trigger LANGUAGE plpgsql AS $$ "
                "BEGIN RAISE EXCEPTION 'synthetic failure'; END $$"
            )
        )
        connection.execute(
            text(
                "CREATE TRIGGER phase5d_reject BEFORE INSERT ON relationship_messages "
                "FOR EACH ROW EXECUTE FUNCTION phase5d_reject()"
            )
        )
    try:
        failed = finalize(client, user, tamper)
        assert failed.status_code == 503 and artifact_path.exists()
        with sessionmaker(bind=database_engine)() as db:
            assert db.get(ChatImportJob, tamper["id"]).status == "ready"
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(RelationshipMessage)
                    .where(RelationshipMessage.import_job_id == tamper["id"])
                )
                == 0
            )
    finally:
        with database_engine.begin() as connection:
            connection.execute(text("DROP TRIGGER phase5d_reject ON relationship_messages"))
            connection.execute(text("DROP FUNCTION phase5d_reject()"))
    assert finalize(client, user, tamper).status_code == 200
    expiring = upload(client, user).json()
    with sessionmaker(bind=database_engine)() as db, db.begin():
        row = db.get(ChatImportArtifact, expiring["artifact_id"])
        row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    removed, _ = app.state.import_workflow.cleanup_expired()
    assert removed == 1
    assert (
        client.get(f"/api/v1/chat-imports/{expiring['id']}", headers=headers(user)).json()["status"]
        == "cancelled"
    )


def test_chunked_reads_interrupted_upload_and_cross_owner_binding(
    setup_api, database_engine, monkeypatch
):
    app, client, root = setup_api
    user, _, _, _ = scope(database_engine)
    outsider, _, _, _ = scope(database_engine)
    original = UploadFile.read
    read_sizes = []

    async def measured(self, size=-1):
        read_sizes.append(size)
        return await original(self, size)

    monkeypatch.setattr(UploadFile, "read", measured)
    created = upload(client, user, content=transcript(1000))
    assert created.status_code == 201, created.text
    assert read_sizes and all(size == CHUNK_BYTES for size in read_sizes)
    job = created.json()
    denied = client.put(
        f"/api/v1/chat-imports/{job['id']}/speakers",
        headers=headers(outsider),
        json={"raw_speaker_label": "我", "binding_kind": "self", "expected_revision": 0},
    )
    assert denied.status_code == 404
    client.post(f"/api/v1/chat-imports/{job['id']}/cancel", headers=headers(user))
    calls = 0

    async def interrupted(self, size=-1):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ConnectionError("synthetic client disconnect")
        return await original(self, size)

    monkeypatch.setattr(UploadFile, "read", interrupted)
    with TestClient(app, raise_server_exceptions=False) as fault_client:
        response = upload(fault_client, user, content=transcript(1000))
    assert response.status_code == 500
    assert list(root.iterdir()) == []


def test_concurrent_http_finalize_one_receipt(setup_api, database_engine):
    _app, client, _root = setup_api
    user, person, relationship, _ = scope(database_engine)
    ready = bind(
        client, user, upload(client, user, content=transcript(1000)).json(), person, relationship
    )
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: finalize(client, user, ready), range(2)))
    assert all(result.status_code == 200 for result in results), [r.text for r in results]
    assert sorted(result.json()["new_message_count"] for result in results) == [0, 1000]
    with sessionmaker(bind=database_engine)() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(RelationshipMessage)
                .where(RelationshipMessage.relationship_id == relationship)
            )
            == 1000
        )


def test_success_cleanup_fault_recovered_without_reimport(setup_api, database_engine, monkeypatch):
    app, client, root = setup_api
    user, person, relationship, _ = scope(database_engine)
    ready = bind(client, user, upload(client, user).json(), person, relationship)
    store = app.state.import_artifact_store
    original_delete = store.delete

    def failed_delete(_key):
        raise OSError("synthetic storage failure")

    monkeypatch.setattr(store, "delete", failed_delete)
    receipt = finalize(client, user, ready)
    assert receipt.status_code == 200 and receipt.json()["new_message_count"] == 2
    assert len(list(root.glob("*.bin"))) == 1
    assert finalize(client, user, ready).json()["new_message_count"] == 0
    monkeypatch.setattr(store, "delete", original_delete)
    assert app.state.import_workflow.cleanup_expired()[0] >= 1
    assert list(root.glob("*.bin")) == []
    with sessionmaker(bind=database_engine)() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(RelationshipMessage)
                .where(RelationshipMessage.relationship_id == relationship)
            )
            == 2
        )


def test_real_socket_ten_thousand_http_import(database_engine, tmp_path):
    user, person, relationship, _ = scope(database_engine)
    app = create_app(
        settings(database_engine, chat_import_artifact_root=tmp_path / "network-artifacts")
    )
    import socket

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = Thread(target=server.run, daemon=True)
    thread.start()
    deadline = monotonic() + 10
    while not server.started and monotonic() < deadline:
        sleep(0.02)
    assert server.started
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=120) as client:
            response = upload(client, user, content=transcript(10_000))
            assert response.status_code == 201, response.text
            ready = bind(client, user, response.json(), person, relationship)
            receipt = finalize(client, user, ready)
            assert receipt.status_code == 200, receipt.text
            assert receipt.json()["new_message_count"] == 10_000
            assert client.get(
                f"/api/v1/relationships/{relationship}/messages",
                headers=headers(user),
                params={"limit": 200},
            ).json()["next_cursor"]
            assert list((tmp_path / "network-artifacts").glob("*.bin")) == []
    finally:
        server.should_exit = True
        thread.join(timeout=10)
    assert not thread.is_alive()
