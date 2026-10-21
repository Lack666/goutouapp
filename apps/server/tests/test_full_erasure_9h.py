"""Signed FastAPI/PostgreSQL full-scope erasure; only disposable anonymous data."""

import json
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session
from test_agent_rest import headers
from test_erasure import erasure_api as legacy_erasure_api  # noqa: F401
from test_import_api import bind, transcript, upload
from test_memory_control import _save
from test_resource_admission import api
from test_resource_admission import worker_pair as erasure_workers  # noqa: F401

from app.chat_import.artifacts import ArtifactStoreError, LocalFilesystemImportArtifactStore
from app.db.models import (
    AgentRun,
    ChatImportArtifact,
    ChatImportJob,
    ChatImportSpeaker,
    Conversation,
    LifecycleConfirmation,
    LifecycleReceipt,
    MemoryRecordRow,
    Message,
    Person,
    Relationship,
    RelationshipMessage,
    User,
)
from app.db.repositories import records
from app.db.repositories.memory import SQLAlchemyMemoryStore
from app.schemas.lifecycle import LifecycleExecute, LifecycleTarget
from app.services.agent_service import actor_from_verified_identity
from app.services.agent_writer import AgentWriterRegistry
from app.services.lifecycle_erasure import LifecycleErasure
from app.services.memory_retention import MemoryRetentionService

BASE = "/api/v1/lifecycle-erasures"


@pytest.fixture
def full_erasure_api(legacy_erasure_api):  # noqa: F811
    try:
        yield legacy_erasure_api
    finally:
        engine, _, a, b, *_ = legacy_erasure_api
        with Session(engine) as db, db.begin():
            db.execute(
                delete(LifecycleConfirmation).where(
                    LifecycleConfirmation.owner_user_id.in_((a[0], b[0]))
                )
            )


def preparation(fixture, domain):
    _, client, a, *_ = fixture
    body = {"domain": domain, "target_id": str(a[1] if domain == "person" else a[2])}
    response = client.post(BASE + "/prepare", headers=headers(a[0]), json=body)
    assert response.status_code == 200, response.text
    challenge = response.json()
    assert challenge["counts"]["messages"] == 2
    assert challenge["counts"]["memory_records"] == 1
    assert challenge["counts"]["relationship_messages"] == 4
    assert challenge["memory_policy"] == "delete_exact_structured_scope"
    return {**body, "confirmation_id": challenge["confirmation_id"], "operation_key": uuid4().hex}


def execution(fixture, body, owner=None):
    _, client, a, *_ = fixture
    return client.post(BASE + "/execute", headers=headers(owner or a[0]), json=body)


@pytest.mark.parametrize("domain", ["person", "relationship"])
def test_full_primary_scope_receipt_replay_old_uuid_agent_job_cursor(full_erasure_api, domain):
    engine, client, a, b, job, _, config = full_erasure_api
    with Session(engine) as db, db.begin():
        person = records.create_person(db, a[0], "Synthetic survivor")
        relationship = records.create_relationship(db, a[0], person.id, "unknown", "unknown")
        survivor = relationship.id
    body = preparation(full_erasure_api, domain)
    response = execution(full_erasure_api, body)
    assert response.status_code == 200, response.text
    receipt = response.json()
    assert execution(full_erasure_api, body).json() == receipt
    assert (
        client.get(BASE + "/receipts/" + receipt["receipt_id"], headers=headers(a[0])).json()
        == receipt
    )
    assert execution(full_erasure_api, {**body, "target_id": str(uuid4())}).status_code == 409
    with Session(engine) as db:
        assert db.get(Relationship, a[2]).deleted_at
        assert db.get(Relationship, a[2]).relationship_type == "erased"
        assert bool(db.get(Person, a[1]).deleted_at) == (domain == "person")
        if domain == "person":
            assert db.get(Person, a[1]).display_name == ""
        assert db.get(Conversation, a[3]).deleted_at
        for model, predicate in (
            (Message, Message.conversation_id == a[3]),
            (RelationshipMessage, RelationshipMessage.relationship_id == a[2]),
            (MemoryRecordRow, MemoryRecordRow.relationship_id == a[2]),
            (ChatImportSpeaker, ChatImportSpeaker.job_id == job["id"]),
        ):
            assert db.scalar(select(func.count()).select_from(model).where(predicate)) == 0
        assert records.get_relationship(db, a[0], survivor) is not None
        assert records.get_conversation(db, b[0], b[3]) is not None
        assert (
            db.get(
                AgentRun, db.scalar(select(AgentRun.id).where(AgentRun.conversation_id == a[3]))
            ).operation_key
            == "synthetic-original-key"
        )
    assert (
        client.get(f"/api/v1/relationships/{a[2]}/messages", headers=headers(a[0])).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/conversations/{a[3]}/agent-runs",
            headers=headers(a[0]),
            json={"message": "Synthetic replay", "operation_key": "synthetic-original-key"},
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/conversations/{a[3]}/agent-runs/stream",
            headers=headers(a[0]),
            json={"message": "Synthetic replay", "operation_key": "synthetic-original-key"},
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/chat-imports/{job['id']}/finalize",
            headers=headers(a[0]),
            json={"expected_revision": job["binding_revision"]},
        ).status_code
        == 409
    )
    endpoint = "/persons" if domain == "person" else "/relationships"
    payload = {
        "id": body["target_id"],
        **(
            {"display_name": "New synthetic label"}
            if domain == "person"
            else {"person_id": str(a[1]), "relationship_type": "unknown", "status": "unknown"}
        ),
    }
    assert client.post("/api/v1" + endpoint, headers=headers(a[0]), json=payload).status_code == 409


@pytest.mark.parametrize("domain", ["person", "relationship"])
def test_foreign_prepare_execute_receipt_and_widening_rejected(full_erasure_api, domain):
    _, client, a, b, *_ = full_erasure_api
    body = preparation(full_erasure_api, domain)
    assert (
        client.post(
            BASE + "/prepare",
            headers=headers(b[0]),
            json={"domain": domain, "target_id": body["target_id"]},
        ).status_code
        == 404
    )
    assert execution(full_erasure_api, body, b[0]).status_code == 404
    assert execution(full_erasure_api, {**body, "domain": "owner"}).status_code == 422
    response = execution(full_erasure_api, body)
    assert (
        client.get(
            BASE + "/receipts/" + response.json()["receipt_id"], headers=headers(b[0])
        ).status_code
        == 404
    )


@pytest.mark.parametrize("domain", ["person", "relationship"])
@pytest.mark.parametrize("change", ["expired", "message", "conversation", "relationship"])
def test_expired_or_new_dependency_snapshot_requires_new_confirmation(
    full_erasure_api, domain, change
):
    engine, client, a, *_ = full_erasure_api
    body = preparation(full_erasure_api, domain)
    with Session(engine) as db, db.begin():
        if change == "expired":
            db.get(LifecycleConfirmation, body["confirmation_id"]).expires_at = datetime.now(
                UTC
            ) - timedelta(seconds=1)
        elif change == "message":
            records.create_message(db, a[0], a[3], "user", "New synthetic occurrence")
        elif change == "conversation":
            records.create_conversation(db, a[0], a[2])
        else:
            records.create_relationship(db, a[0], a[1], "new", "new")
    response = execution(full_erasure_api, body)
    if change == "relationship" and domain == "relationship":
        assert response.status_code == 200  # unrelated relationship is outside the confirmed scope
    else:
        assert response.status_code == 409
    with Session(engine) as db:
        if response.status_code == 409:
            assert db.get(Relationship, a[2]).deleted_at is None


@pytest.mark.parametrize("domain", ["person", "relationship"])
def test_two_execute_workers_same_key_have_single_durable_receipt(full_erasure_api, domain):
    engine, _, a, _, _, _, config = full_erasure_api
    body = preparation(full_erasure_api, domain)
    service = LifecycleErasure(
        lambda: Session(engine),
        __import__(
            "app.chat_import.artifacts", fromlist=["LocalFilesystemImportArtifactStore"]
        ).LocalFilesystemImportArtifactStore(config.chat_import_artifact_root),
        AgentWriterRegistry(config.chat_import_artifact_root),
    )
    actor = actor_from_verified_identity(a[0])
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(
            executor.map(
                lambda _: service.execute(actor, LifecycleExecute(**body)).model_dump(mode="json"),
                range(4),
            )
        )
    assert all(row == results[0] for row in results)
    with Session(engine) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(LifecycleReceipt)
                .where(LifecycleReceipt.owner_user_id == a[0])
            )
            == 1
        )


def test_owner_erasure_is_operator_only_terminal_identity_and_exact_metadata(full_erasure_api):
    engine, client, a, b, _, _, config = full_erasure_api
    from app.chat_import.artifacts import LocalFilesystemImportArtifactStore

    service = LifecycleErasure(
        lambda: Session(engine),
        LocalFilesystemImportArtifactStore(config.chat_import_artifact_root),
        AgentWriterRegistry(config.chat_import_artifact_root),
    )
    actor = actor_from_verified_identity(a[0])
    target = LifecycleTarget(domain="owner", target_id=a[0])
    assert (
        client.post(
            BASE + "/prepare", headers=headers(a[0]), json=target.model_dump(mode="json")
        ).status_code
        == 422
    )
    challenge = service.prepare(actor, target)
    body = LifecycleExecute(
        **target.model_dump(), confirmation_id=challenge.confirmation_id, operation_key=uuid4().hex
    )
    result = service.execute(actor, body)
    assert service.execute(actor, body) == result
    with Session(engine) as db:
        assert db.get(User, a[0]).deleted_at
        assert db.get(User, b[0]).deleted_at is None
        assert (
            db.scalar(
                select(func.count())
                .select_from(MemoryRecordRow)
                .where(MemoryRecordRow.owner_user_id == a[0])
            )
            == 0
        )
    for path in (
        "/persons",
        "/relationships",
        "/conversations",
        "/memory/control",
        BASE + "/receipts/" + str(result.receipt_id),
    ):
        assert client.get("/api/v1" + path, headers=headers(a[0])).status_code == 401
    assert (
        client.post(
            "/api/v1/persons",
            headers=headers(a[0]),
            json={"id": str(uuid4()), "display_name": "Cannot recreate"},
        ).status_code
        == 401
    )
    assert client.get("/api/v1/persons", headers=headers(b[0])).status_code == 200


@pytest.mark.parametrize("domain", ["person", "relationship"])
def test_two_real_http_workers_discard_committed_response_then_same_key_replay(
    full_erasure_api,
    erasure_workers,  # noqa: F811
    domain,
):
    engine, _, a, b, *_ = full_erasure_api
    _, _, ports, _ = erasure_workers()
    body = preparation(full_erasure_api, domain)
    payload = json.dumps(body).encode()
    credential = headers(a[0])["Authorization"]
    wire = (
        f"POST {BASE}/execute HTTP/1.1\r\nHost: 127.0.0.1\r\n"
        f"Authorization: {credential}\r\nContent-Type: application/json\r\n"
        f"Content-Length: {len(payload)}\r\nConnection: close\r\n\r\n"
    ).encode() + payload
    with socket.create_connection(("127.0.0.1", ports[0]), timeout=5) as connection:
        connection.sendall(wire)
        del credential, wire
        deadline = time.monotonic() + 10
        committed = False
        while time.monotonic() < deadline:
            with Session(engine) as db:
                committed = (
                    db.scalar(
                        select(LifecycleReceipt.id).where(
                            LifecycleReceipt.owner_user_id == a[0],
                            LifecycleReceipt.operation_key == body["operation_key"],
                        )
                    )
                    is not None
                )
            if committed:
                break
            time.sleep(0.05)
    assert committed

    def replay(index):
        with api(ports[index % 2]) as client:
            response = client.post(BASE + "/execute", headers=headers(a[0]), json=body)
            assert response.status_code == 200, response.text
            return response.json()

    with ThreadPoolExecutor(max_workers=4) as workers:
        receipts = list(workers.map(replay, range(4)))
    assert all(receipt == receipts[0] for receipt in receipts)
    with api(ports[1]) as client:
        assert (
            client.get(
                BASE + "/receipts/" + receipts[0]["receipt_id"], headers=headers(b[0])
            ).status_code
            == 404
        )


def test_person_multiple_relationship_memory_is_scope_not_text_mention(full_erasure_api):
    engine, _, a, *_ = full_erasure_api
    with Session(engine) as db, db.begin():
        second = records.create_relationship(db, a[0], a[1], "unknown", "unknown").id
        other_person = records.create_person(db, a[0], "Synthetic other person").id
        other_relationship = records.create_relationship(
            db, a[0], other_person, "unknown", "unknown"
        ).id
    store = SQLAlchemyMemoryStore(lambda: Session(engine))
    _save(store, a[0], a[1], second, "Synthetic second relationship fact")
    _save(store, a[0], other_person, other_relationship, "Synthetic text mentioning " + str(a[1]))
    client = full_erasure_api[1]
    target = {"domain": "person", "target_id": str(a[1])}
    challenge = client.post(BASE + "/prepare", headers=headers(a[0]), json=target).json()
    assert challenge["counts"]["memory_records"] == 2
    body = {**target, "confirmation_id": challenge["confirmation_id"], "operation_key": uuid4().hex}
    assert execution(full_erasure_api, body).status_code == 200
    with Session(engine) as db:
        assert not list(
            db.scalars(select(MemoryRecordRow.id).where(MemoryRecordRow.person_id == a[1]))
        )
        assert db.scalar(
            select(MemoryRecordRow.id).where(MemoryRecordRow.person_id == other_person)
        )


def test_person_shared_unbound_speaker_refuses_widening_and_preserves_everything(full_erasure_api):
    _, client, a, *_ = full_erasure_api
    job = upload(client, a[0]).json()
    response = client.put(
        f"/api/v1/chat-imports/{job['id']}/speakers",
        headers=headers(a[0]),
        json={
            "raw_speaker_label": "A",
            "binding_kind": "person",
            "person_id": str(a[1]),
            "expected_revision": job["binding_revision"],
        },
    )
    assert response.status_code == 200
    response = client.post(
        BASE + "/prepare", headers=headers(a[0]), json={"domain": "person", "target_id": str(a[1])}
    )
    assert response.status_code == 409 and response.json()["error"]["code"] == "shared_reference"
    assert client.get(f"/api/v1/persons/{a[1]}", headers=headers(a[0])).status_code == 200


@pytest.mark.parametrize("fault", ["unlink", "receipt_commit"])
def test_pending_raw_file_fault_never_certifies_deletion_and_exact_retry_cleans(
    full_erasure_api, monkeypatch, fault
):
    engine, client, a, _, _, _, config = full_erasure_api
    pending = bind(client, a[0], upload(client, a[0], content=transcript(2)).json(), a[1], a[2])
    with Session(engine) as db:
        artifact = db.get(ChatImportArtifact, db.get(ChatImportJob, pending["id"]).artifact_id)
        raw_key = artifact.storage_key
    store = LocalFilesystemImportArtifactStore(config.chat_import_artifact_root)
    assert store.exists(raw_key)
    body = preparation(full_erasure_api, "relationship")
    original = LocalFilesystemImportArtifactStore.delete
    if fault == "unlink":

        def fail(self, key):
            if key == raw_key:
                raise ArtifactStoreError("synthetic-private-file-sentinel")
            return original(self, key)

        monkeypatch.setattr(LocalFilesystemImportArtifactStore, "delete", fail)
    else:
        with engine.begin() as db:
            db.execute(
                text(
                    "CREATE FUNCTION lifecycle_fixture_fail() RETURNS trigger LANGUAGE plpgsql "
                    "AS $$ BEGIN RAISE EXCEPTION 'synthetic-private-sql-sentinel'; END $$"
                )
            )
            db.execute(
                text(
                    "CREATE TRIGGER lifecycle_fixture_fail BEFORE INSERT ON lifecycle_receipts "
                    "FOR EACH ROW EXECUTE FUNCTION lifecycle_fixture_fail()"
                )
            )
    try:
        response = execution(full_erasure_api, body)
        assert response.status_code == 503 and "sentinel" not in response.text
        with Session(engine) as db:
            assert db.get(Relationship, a[2]).deleted_at is None
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(LifecycleReceipt)
                    .where(LifecycleReceipt.owner_user_id == a[0])
                )
                == 0
            )
        assert store.exists(raw_key) == (fault == "unlink")
    finally:
        if fault == "unlink":
            monkeypatch.setattr(LocalFilesystemImportArtifactStore, "delete", original)
        else:
            with engine.begin() as db:
                db.execute(text("DROP TRIGGER lifecycle_fixture_fail ON lifecycle_receipts"))
                db.execute(text("DROP FUNCTION lifecycle_fixture_fail()"))
    assert execution(full_erasure_api, body).status_code == 200
    assert not store.exists(raw_key)
    with Session(engine) as db:
        assert db.get(ChatImportJob, pending["id"]).status == "cancelled"
        assert db.get(ChatImportJob, pending["id"]).deleted_at
    with Session(engine) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(LifecycleReceipt)
                .where(LifecycleReceipt.owner_user_id == a[0])
            )
            == 1
        )


def test_expired_lifecycle_challenge_cleanup_preserves_exact_receipt_replay(full_erasure_api):
    engine, _, a, *_ = full_erasure_api
    body = preparation(full_erasure_api, "relationship")
    receipt = execution(full_erasure_api, body).json()
    from uuid import UUID

    with Session(engine) as db, db.begin():
        db.get(LifecycleConfirmation, UUID(body["confirmation_id"])).expires_at = datetime.now(
            UTC
        ) - timedelta(days=2)
    result = MemoryRetentionService(lambda: Session(engine)).run(dry_run=False, max_batches=3)
    assert result.status == "ok" and result.counts.confirmation_challenges >= 1
    with Session(engine) as db:
        assert db.get(LifecycleConfirmation, UUID(body["confirmation_id"])) is None
        assert db.get(LifecycleReceipt, UUID(receipt["receipt_id"])) is not None
    assert execution(full_erasure_api, body).json() == receipt
