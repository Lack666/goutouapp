"""Real signed HTTP/PostgreSQL guarded erasure using anonymous synthetic data."""

import json
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from test_agent_rest import headers, settings
from test_import_api import bind, finalize, scope, transcript, upload
from test_memory_control import _save
from test_resource_admission import api
from test_resource_admission import worker_pair as erasure_workers  # noqa: F401

from app.db.models import (
    AgentRun,
    ChatImportJob,
    Conversation,
    ErasureConfirmation,
    ErasureReceipt,
    MemoryRecordRow,
    Message,
    Person,
    Relationship,
    RelationshipMessage,
)
from app.db.repositories import records
from app.db.repositories.memory import SQLAlchemyMemoryStore
from app.main import create_app
from app.services.agent_service import actor_from_verified_identity
from app.services.backup_restore import RecoveryError, dump_synthetic, restore_synthetic
from app.services.erasure import ErasureError, ErasureService
from app.services.memory_retention import MemoryRetentionService

BASE = "/api/v1/erasures"


@pytest.fixture(name="database_engine")
def isolated_recovery_engine(recovery_database_engine):
    return recovery_database_engine


@pytest.fixture
def erasure_api(database_engine, tmp_path):
    a, b = scope(database_engine), scope(database_engine)
    config = settings(database_engine, chat_import_artifact_root=tmp_path / "artifacts")
    store = SQLAlchemyMemoryStore(lambda: Session(database_engine))
    _save(store, a[0], a[1], a[2], "Synthetic independent memory")
    with TestClient(create_app(config)) as client:
        job = bind(client, a[0], upload(client, a[0], content=transcript(4)).json(), a[1], a[2])
        result = finalize(client, a[0], job)
        assert result.status_code == 200
        with Session(database_engine) as db, db.begin():
            msg = records.create_message(db, a[0], a[3], "user", "Synthetic agent input")
            answer = records.create_message(db, a[0], a[3], "assistant", "Synthetic agent answer")
            db.add(
                AgentRun(
                    user_id=a[0],
                    conversation_id=a[3],
                    status="completed",
                    operation_key="synthetic-original-key",
                    request_fingerprint="a" * 64,
                    user_message_id=msg.id,
                    assistant_message_id=answer.id,
                    memory_status="not_requested",
                    result_warnings=[],
                )
            )
        try:
            yield database_engine, client, a, b, job, tmp_path, config
        finally:
            # The repository uses a session-scoped disposable DB. Do not leak
            # deliberately expired 9E challenges into prior Memory-only grace
            # boundary tests. Keep all durable receipts/tombstones intact.
            with Session(database_engine) as db, db.begin():
                db.execute(
                    delete(ErasureConfirmation).where(
                        ErasureConfirmation.owner_user_id.in_((a[0], b[0]))
                    )
                )


def target(fixture, domain):
    _, _, a, _, job, _, _ = fixture
    return {
        "domain": domain,
        "target_id": job["id"] if domain == "dataset" else str(a[3]),
        "relationship_id": str(a[2]),
    }


def prepare(fixture, domain):
    _, client, a, *_ = fixture
    body = target(fixture, domain)
    result = client.post(BASE + "/prepare", headers=headers(a[0]), json=body)
    assert result.status_code == 200, result.text
    challenge = result.json()
    assert challenge["memory_affected"] is False
    return {**body, "confirmation_id": challenge["confirmation_id"], "operation_key": uuid4().hex}


def execute(fixture, body, owner=None):
    _, client, a, *_ = fixture
    return client.post(BASE + "/execute", headers=headers(owner or a[0]), json=body)


@pytest.mark.parametrize("domain", ["dataset", "conversation"])
def test_exact_primary_deletion_replay_restart_and_domain_independence(erasure_api, domain):
    engine, client, a, b, job, _, config = erasure_api
    body = prepare(erasure_api, domain)
    receipt = execute(erasure_api, body)
    assert receipt.status_code == 200, receipt.text
    result = receipt.json()
    assert result["message_count"] == (4 if domain == "dataset" else 2)
    assert result["run_count"] == (0 if domain == "dataset" else 1)
    assert result["memory_affected"] is False
    # A later independent conversation must survive the logical operation replay.
    with Session(engine) as db, db.begin():
        later = records.create_conversation(db, a[0], a[2])
        records.create_message(db, a[0], later.id, "user", "Synthetic later history")
        later_id = later.id
    with TestClient(create_app(config)) as restarted:
        replay = restarted.post(BASE + "/execute", headers=headers(a[0]), json=body)
        assert replay.json() == result
        lookup = restarted.get(BASE + "/receipts/" + result["receipt_id"], headers=headers(a[0]))
        assert lookup.json() == result
    with Session(engine) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(MemoryRecordRow)
                .where(MemoryRecordRow.owner_user_id == a[0])
            )
            == 1
        )
        assert records.get_person(db, a[0], a[1]) is not None
        assert records.get_relationship(db, a[0], a[2]) is not None
        assert records.get_conversation(db, b[0], b[3]) is not None
        assert len(records.list_messages(db, a[0], later_id)) == 1
        dataset = db.get(ChatImportJob, UUID(job["id"]))
        conversation = db.get(Conversation, a[3])
        assert (dataset.deleted_at is not None) == (domain == "dataset")
        assert (conversation.deleted_at is not None) == (domain == "conversation")
        assert db.scalar(
            select(func.count())
            .select_from(RelationshipMessage)
            .where(RelationshipMessage.import_job_id == dataset.id)
        ) == (0 if domain == "dataset" else 4)
        assert db.scalar(
            select(func.count()).select_from(Message).where(Message.conversation_id == a[3])
        ) == (0 if domain == "conversation" else 2)
        run = db.scalar(select(AgentRun).where(AgentRun.conversation_id == a[3]))
        assert run.operation_key == "synthetic-original-key"
        if domain == "conversation":
            assert run.user_message_id is None and run.assistant_message_id is None
            assert run.result_warnings is None
    if domain == "conversation":
        assert (
            client.get(f"/api/v1/conversations/{a[3]}/messages", headers=headers(a[0])).status_code
            == 404
        )
        listed = client.get("/api/v1/conversations", headers=headers(a[0])).json()["items"]
        assert str(a[3]) not in {row["id"] for row in listed}
        recreate = client.post(
            "/api/v1/conversations",
            headers=headers(a[0]),
            json={"id": str(a[3]), "relationship_id": str(a[2])},
        )
        assert recreate.status_code == 409
    else:
        assert finalize(client, a[0], job).json()["error"]["code"] == "dataset_deleted"


@pytest.mark.parametrize("domain", ["dataset", "conversation"])
def test_foreign_target_challenge_and_receipt_denied(erasure_api, domain):
    engine, client, a, b, *_ = erasure_api
    body = prepare(erasure_api, domain)
    assert (
        client.post(
            BASE + "/prepare", headers=headers(b[0]), json=target(erasure_api, domain)
        ).status_code
        == 404
    )
    assert execute(erasure_api, body, b[0]).status_code == 404
    # Both API scope checks and real composite FKs enforce Relationship ownership.
    model = ChatImportJob if domain == "dataset" else Conversation
    column = "bound_relationship_id" if domain == "dataset" else "relationship_id"
    with pytest.raises(IntegrityError), Session(engine) as db, db.begin():
        setattr(db.get(model, UUID(body["target_id"])), column, b[2])
    inconsistent = {**target(erasure_api, domain), "relationship_id": str(b[2])}
    assert (
        client.post(BASE + "/prepare", headers=headers(a[0]), json=inconsistent).status_code == 404
    )
    receipt = execute(erasure_api, body).json()
    assert (
        client.get(BASE + "/receipts/" + receipt["receipt_id"], headers=headers(b[0])).status_code
        == 404
    )
    assert client.post(BASE + "/execute", json=body).status_code == 401


@pytest.mark.parametrize("domain", ["dataset", "conversation"])
@pytest.mark.parametrize("change", ["target_id", "relationship_id", "domain"])
def test_challenge_exact_target_and_same_key_changed_payload(erasure_api, domain, change):
    body = prepare(erasure_api, domain)
    altered = dict(body)
    altered[change] = (
        ("conversation" if domain == "dataset" else "dataset")
        if change == "domain"
        else str(uuid4())
    )
    assert execute(erasure_api, altered).json()["error"]["code"] == "confirmation_mismatch"
    assert execute(erasure_api, body).status_code == 200
    assert execute(erasure_api, altered).json()["error"]["code"] == "idempotency_conflict"


@pytest.mark.parametrize("domain", ["dataset", "conversation"])
@pytest.mark.parametrize("fault", ["expired", "consumed", "missing", "changed"])
def test_expiry_consumption_missing_and_snapshot_change(erasure_api, domain, fault):
    engine, _, a, _, job, *_ = erasure_api
    body = prepare(erasure_api, domain)
    with Session(engine) as db, db.begin():
        challenge = db.get(ErasureConfirmation, UUID(body["confirmation_id"]))
        if fault == "expired":
            challenge.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        elif fault == "consumed":
            challenge.consumed_at = datetime.now(UTC)
        elif fault == "missing":
            body["confirmation_id"] = str(uuid4())
        elif domain == "conversation":
            records.create_message(db, a[0], a[3], "user", "Synthetic concurrent append")
        else:
            row = db.scalar(
                select(RelationshipMessage).where(
                    RelationshipMessage.import_job_id == UUID(job["id"])
                )
            )
            row.content = "Synthetic changed content"
    result = execute(erasure_api, body)
    assert result.status_code == (404 if fault == "missing" else 409)
    assert (
        result.json()["error"]["code"]
        == {
            "expired": "confirmation_expired",
            "consumed": "confirmation_consumed",
            "missing": "confirmation_not_found",
            "changed": "target_changed",
        }[fault]
    )
    with Session(engine) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(ErasureReceipt)
                .where(ErasureReceipt.owner_user_id == a[0])
            )
            == 0
        )


@pytest.mark.parametrize("domain", ["dataset", "conversation"])
def test_duplicate_parallel_execute_single_durable_receipt(erasure_api, domain):
    engine, _, a, *_ = erasure_api
    body = prepare(erasure_api, domain)

    def work(_):
        from app.schemas.erasure import ErasureExecute

        service = ErasureService(lambda: Session(engine))
        actor = actor_from_verified_identity(a[0])
        return service.execute(actor, ErasureExecute(**body)).model_dump(mode="json")

    with ThreadPoolExecutor(max_workers=4) as workers:
        results = list(workers.map(work, range(4)))
    assert all(row == results[0] for row in results)
    with Session(engine) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(ErasureReceipt)
                .where(ErasureReceipt.owner_user_id == a[0])
            )
            == 1
        )


@pytest.mark.parametrize(
    "status,memory_status", [("running", None), ("pending", None), ("completed", None)]
)
def test_running_and_unresolved_memory_work_blocks_deletion(erasure_api, status, memory_status):
    engine, client, a, *_ = erasure_api
    with Session(engine) as db, db.begin():
        run = db.scalar(select(AgentRun).where(AgentRun.conversation_id == a[3]))
        run.status, run.memory_status = status, memory_status
    result = client.post(
        BASE + "/prepare", headers=headers(a[0]), json=target(erasure_api, "conversation")
    )
    assert result.status_code == 409
    assert result.json()["error"]["code"] == "target_busy"


def test_import_duplicate_deleted_dataset_cannot_resurrect_other_scope_survives(erasure_api):
    engine, client, a, b, job, *_ = erasure_api
    duplicate = bind(client, a[0], upload(client, a[0], content=transcript(4)).json(), a[1], a[2])
    assert finalize(client, a[0], duplicate).json()["dataset_job_id"] == job["id"]
    body = prepare(erasure_api, "dataset")
    assert execute(erasure_api, body).status_code == 200
    assert finalize(client, a[0], duplicate).json()["error"]["code"] == "dataset_deleted"
    newer = bind(client, a[0], upload(client, a[0], content=transcript(4)).json(), a[1], a[2])
    assert finalize(client, a[0], newer).json()["error"]["code"] == "dataset_deleted"
    independent = bind(client, b[0], upload(client, b[0], content=transcript(4)).json(), b[1], b[2])
    assert finalize(client, b[0], independent).status_code == 200
    other_dataset = bind(
        client, a[0], upload(client, a[0], content=transcript(6)).json(), a[1], a[2]
    )
    assert finalize(client, a[0], other_dataset).status_code == 200
    assert execute(erasure_api, body).status_code == 200
    with Session(engine) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(RelationshipMessage)
                .where(RelationshipMessage.import_job_id == UUID(other_dataset["id"]))
            )
            == 6
        )


def test_dataset_cursor_refresh_and_agent_key_replay(erasure_api):
    _, client, a, _, job, *_ = erasure_api
    path = f"/api/v1/relationships/{a[2]}/messages"
    page = client.get(path, headers=headers(a[0]), params={"limit": 1})
    assert page.status_code == 200
    cursor = page.json()["next_cursor"]
    assert cursor
    assert execute(erasure_api, prepare(erasure_api, "dataset")).status_code == 200
    assert client.get(path, headers=headers(a[0]), params={"cursor": cursor}).json()["items"] == []
    assert client.get(path, headers=headers(a[0])).json()["items"] == []
    assert execute(erasure_api, prepare(erasure_api, "conversation")).status_code == 200
    for suffix in ("", "/stream"):
        result = client.post(
            f"/api/v1/conversations/{a[3]}/agent-runs{suffix}",
            headers=headers(a[0]),
            json={"message": "Synthetic old input", "operation_key": "synthetic-original-key"},
        )
        assert result.status_code == 404


@pytest.mark.parametrize("domain", ["dataset", "conversation"])
def test_receipt_failure_rolls_back_all_effects_and_redacts(erasure_api, domain):
    engine, _, a, *_ = erasure_api
    body = prepare(erasure_api, domain)
    with engine.begin() as c:
        c.execute(
            text(
                "CREATE FUNCTION erasure_fixture_fail() RETURNS trigger LANGUAGE plpgsql "
                "AS $$ BEGIN RAISE EXCEPTION 'synthetic-private-sentinel'; END $$"
            )
        )
        c.execute(
            text(
                "CREATE TRIGGER erasure_fixture_fail BEFORE INSERT ON erasure_receipts "
                "FOR EACH ROW EXECUTE FUNCTION erasure_fixture_fail()"
            )
        )
    try:
        response = execute(erasure_api, body)
        assert response.status_code == 503
        assert "synthetic-private-sentinel" not in response.text
        with Session(engine) as db:
            assert db.get(ErasureConfirmation, UUID(body["confirmation_id"])).consumed_at is None
            model = ChatImportJob if domain == "dataset" else Conversation
            assert db.get(model, UUID(body["target_id"])).deleted_at is None
    finally:
        with engine.begin() as c:
            c.execute(text("DROP TRIGGER erasure_fixture_fail ON erasure_receipts"))
            c.execute(text("DROP FUNCTION erasure_fixture_fail()"))
    assert execute(erasure_api, body).status_code == 200


@pytest.mark.parametrize("domain", ["dataset", "conversation"])
def test_real_old_backup_reconciles_exact_targets_receipt_and_memory(erasure_api, domain):
    engine, _, a, b, job, temp, config = erasure_api
    archive = temp / "erasure.dump"
    dump_synthetic(engine, archive)
    try:
        body = prepare(erasure_api, domain)
        receipt = execute(erasure_api, body).json()
        root = temp / "restore"
        root.mkdir()
        with restore_synthetic(engine, archive, root) as restore:
            assert restore.released is False
            restored = restore.reconcile()
            assert restore.released is True
            restore.reconcile()
            service = ErasureService(lambda: Session(restored))
            from app.schemas.erasure import ErasureExecute

            assert (
                service.execute(
                    actor_from_verified_identity(a[0]), ErasureExecute(**body)
                ).model_dump(mode="json")
                == receipt
            )
            with Session(restored) as db:
                model = ChatImportJob if domain == "dataset" else Conversation
                assert db.get(model, UUID(body["target_id"])).deleted_at is not None
                assert records.get_conversation(db, b[0], b[3]) is not None
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(MemoryRecordRow)
                        .where(MemoryRecordRow.owner_user_id == a[0])
                    )
                    == 1
                )
                if domain == "dataset":
                    assert (
                        db.scalar(
                            select(func.count())
                            .select_from(RelationshipMessage)
                            .where(RelationshipMessage.import_job_id == UUID(job["id"]))
                        )
                        == 0
                    )
                else:
                    assert (
                        db.scalar(
                            select(func.count())
                            .select_from(Message)
                            .where(Message.conversation_id == a[3])
                        )
                        == 0
                    )
    finally:
        archive.unlink(missing_ok=True)


def test_person_relationship_account_gaps_are_explicit_no_public_erasure(erasure_api):
    engine, client, a, *_ = erasure_api
    # Multiple relationships and existing Memory/history keep formal references.
    with Session(engine) as db, db.begin():
        records.create_relationship(db, a[0], a[1], "unknown", "unknown")
    for path in (f"/api/v1/persons/{a[1]}", f"/api/v1/relationships/{a[2]}", "/api/v1/account"):
        assert client.delete(path, headers=headers(a[0])).status_code in {404, 405}
    with Session(engine) as db:
        assert db.get(Person, a[1]) is not None
        assert db.get(Relationship, a[2]) is not None
    # Unsupported domains cannot silently enlarge the new destructive protocol.
    for domain in ("person", "relationship", "account", "all", "message"):
        result = client.post(
            BASE + "/prepare",
            headers=headers(a[0]),
            json={"domain": domain, "target_id": str(a[1])},
        )
        assert result.status_code == 422


def test_client_confirm_boolean_and_expired_token_cannot_bypass(erasure_api):
    _, client, a, *_ = erasure_api
    body = prepare(erasure_api, "dataset")
    assert execute(erasure_api, {**body, "confirm": True}).status_code == 422
    assert (
        client.post(BASE + "/execute", headers=headers(a[0], exp=0), json=body).status_code == 401
    )


@pytest.mark.parametrize("domain", ["dataset", "conversation"])
def test_signed_two_process_http_commit_response_discard_and_replay(
    erasure_api,
    erasure_workers,  # noqa: F811 - imported pytest fixture
    domain,
):
    engine, _, a, b, *_ = erasure_api
    _, admission, ports, _ = erasure_workers()
    body = prepare(erasure_api, domain)

    # Send through a real socket but never read the committed HTTP response.
    # Observe only the authoritative receipt, close the connection, and recover
    # through a different worker. No caller-side success body is retained.
    encoded = json.dumps(body).encode()
    credential = next(iter(headers(a[0]).values()))
    request = (
        f"POST {BASE}/execute HTTP/1.1\r\nHost: 127.0.0.1\r\n"
        f"Authorization: {credential}\r\nContent-Type: application/json\r\n"
        f"Content-Length: {len(encoded)}\r\nConnection: close\r\n\r\n"
    ).encode() + encoded
    with socket.create_connection(("127.0.0.1", ports[0]), timeout=5) as connection:
        connection.sendall(request)
        del credential, request
        deadline = time.monotonic() + 10
        committed = False
        while time.monotonic() < deadline:
            with Session(engine) as db:
                committed = (
                    db.scalar(
                        select(ErasureReceipt.id).where(
                            ErasureReceipt.owner_user_id == a[0],
                            ErasureReceipt.operation_key == body["operation_key"],
                        )
                    )
                    is not None
                )
            if committed:
                break
            time.sleep(0.05)
    assert committed

    def work(index):
        with api(ports[index % 2]) as client:
            response = client.post(BASE + "/execute", headers=headers(a[0]), json=body)
            assert response.status_code == 200
            return response.json()

    with ThreadPoolExecutor(max_workers=4) as workers:
        results = list(workers.map(work, range(4)))
    # A different server process recovers the unread committed response.
    assert all(row == results[0] for row in results)
    with api(ports[1]) as client:
        assert client.post(BASE + "/execute", headers=headers(b[0]), json=body).status_code == 404
        assert (
            client.get(BASE + "/receipts/" + results[0]["receipt_id"], headers=headers(a[0])).json()
            == results[0]
        )
    with Session(engine) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(ErasureReceipt)
                .where(ErasureReceipt.owner_user_id == a[0])
            )
            == 1
        )
    assert admission.snapshot()["active_uploads"] == 0


def test_expired_erasure_challenge_cleanup_keeps_original_receipt(erasure_api):
    engine, _, a, *_ = erasure_api
    body = prepare(erasure_api, "dataset")
    receipt = execute(erasure_api, body).json()
    with Session(engine) as db, db.begin():
        row = db.get(ErasureConfirmation, UUID(body["confirmation_id"]))
        row.expires_at = datetime.now(UTC) - timedelta(days=2)
    cleanup = MemoryRetentionService(lambda: Session(engine)).run(dry_run=False, max_batches=2)
    assert cleanup.status == "ok" and cleanup.counts.confirmation_challenges >= 1
    with Session(engine) as db:
        assert db.get(ErasureConfirmation, UUID(body["confirmation_id"])) is None
        assert db.get(ErasureReceipt, UUID(receipt["receipt_id"])) is not None
    assert execute(erasure_api, body).json() == receipt


@pytest.mark.parametrize("fault", ["missing_primary", "tampered_receipt", "missing_tombstone"])
def test_erasure_restore_without_complete_authority_fails_closed(erasure_api, fault):
    engine, _, a, _, _, temp, _ = erasure_api
    archive = temp / "failure.dump"
    if fault != "missing_tombstone":
        execute(erasure_api, prepare(erasure_api, "dataset"))
    dump_synthetic(engine, archive)
    try:
        root = temp / "restore-failed"
        root.mkdir()
        with restore_synthetic(engine, archive, root) as restore:
            if fault == "missing_primary":
                from sqlalchemy import create_engine

                restore._source = create_engine(
                    engine.url.set(database="missing_test_000000000000"),
                    hide_parameters=True,
                    connect_args={"connect_timeout": 1},
                )
            elif fault == "tampered_receipt":
                with Session(restore._target) as db, db.begin():
                    receipt = db.scalar(
                        select(ErasureReceipt).where(ErasureReceipt.owner_user_id == a[0])
                    )
                    receipt.message_count += 1
            else:
                with Session(engine) as db, db.begin():
                    newer = records.create_conversation(db, a[0], a[2])
                    newer.deleted_at = datetime.now(UTC)
            with pytest.raises(RecoveryError):
                restore.reconcile()
            assert restore.released is False
    finally:
        archive.unlink(missing_ok=True)


def test_restore_cannot_drop_post_backup_imported_dataset_fence(erasure_api):
    engine, client, a, _, _, temp, _ = erasure_api
    ready = bind(client, a[0], upload(client, a[0], content=transcript(6)).json(), a[1], a[2])
    archive = temp / "ready-before-import.dump"
    dump_synthetic(engine, archive)
    try:
        assert finalize(client, a[0], ready).status_code == 200
        body = {"domain": "dataset", "target_id": ready["id"], "relationship_id": str(a[2])}
        challenge = client.post(BASE + "/prepare", headers=headers(a[0]), json=body).json()
        assert (
            execute(
                erasure_api,
                {
                    **body,
                    "confirmation_id": challenge["confirmation_id"],
                    "operation_key": uuid4().hex,
                },
            ).status_code
            == 200
        )
        root = temp / "restored-before-import"
        root.mkdir()
        with restore_synthetic(engine, archive, root) as restore:
            # The backup had a ready Job, without the canonical imported unique
            # index fence. Merely copying deleted_at then cancelling the Job
            # would permit a new same-transcript Job to resurrect the dataset.
            with pytest.raises(RecoveryError):
                restore.reconcile()
            assert restore.released is False
    finally:
        archive.unlink(missing_ok=True)


def test_new_agent_run_and_erasure_lock_order_remain_live(erasure_api):
    from app.schemas.erasure import ErasureTarget

    engine, _, a, *_ = erasure_api
    service = ErasureService(lambda: Session(engine))
    with ThreadPoolExecutor(max_workers=1) as workers:
        with Session(engine) as agent, agent.begin():
            records.lock_conversation_run_slot(agent, a[3])
            future = workers.submit(
                service.prepare,
                actor_from_verified_identity(a[0]),
                ErasureTarget(**target(erasure_api, "conversation")),
            )
            deadline = time.monotonic() + 5
            waiting = False
            while time.monotonic() < deadline:
                with Session(engine) as probe:
                    waiting = bool(
                        probe.scalar(
                            text(
                                "SELECT count(*) FROM pg_locks WHERE locktype='advisory' "
                                "AND NOT granted AND database=(SELECT oid FROM pg_database "
                                "WHERE datname=current_database())"
                            )
                        )
                    )
                if waiting:
                    break
                time.sleep(0.02)
            assert waiting
            # Actual Run FK checks take KEY SHARE on User. Owner serialization
            # must allow that while erasure waits for this Conversation slot.
            agent.add(
                AgentRun(
                    user_id=a[0],
                    conversation_id=a[3],
                    status="pending",
                    operation_key="synthetic-new-run-race",
                    request_fingerprint="f" * 64,
                )
            )
            agent.flush()
        with pytest.raises(ErasureError) as error:
            future.result(timeout=5)
        assert error.value.code == "target_busy"
