"""Phase 6 acceptance: signed HTTP + real LangGraph/AgentService + PostgreSQL.

Only the LLM provider is replaced. Authentication, composition, persistence,
control/mutation transports and SSE serialization are the production code paths.
"""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from memory_control_demo import create_scope
from memory_phase6_support import FACTS, Phase6Mock, agent_request
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import (
    AgentRun,
    ChatImportJob,
    Conversation,
    MemoryConfirmationRow,
    MemoryMutationRow,
    MemoryOperationRow,
    MemoryRecordRow,
    Message,
    Person,
    Relationship,
    RelationshipMessage,
)
from app.db.repositories import records
from app.main import create_app
from app.services.memory_retention import MemoryRetentionService

SECRET = "phase6d-synthetic-secret-with-more-than-32-bytes"


def headers(owner):
    return {
        "Authorization": "Bearer "
        + jwt.encode(
            {
                "sub": str(owner),
                "exp": datetime.now(UTC) + timedelta(minutes=10),
                "iss": "phase6d-test",
                "aud": "phase6d-api",
            },
            SECRET,
            algorithm="HS256",
        )
    }


class Flow:
    def __init__(self, engine, client, provider, scope):
        self.engine, self.client, self.provider = engine, client, provider
        self.owner, self.person, self.relationship, self.conversation = scope
        self.headers = headers(self.owner)

    def call(self, method, path, body=None, *, status=200, auth=None):
        response = self.client.request(
            method, "/api/v1" + path, headers=self.headers if auth is None else auth, json=body
        )
        assert response.status_code == status, response.text
        return response.json()

    def grant(self):
        return self.call("POST", "/memory/consent", {"enabled": True})

    def inspect(self):
        return self.call("GET", "/memories")["items"]

    def run(self, fact=None, *, stream=False, message=None, conversation=None):
        return agent_request(
            self.client,
            self.headers,
            conversation or self.conversation,
            fact=fact,
            stream=stream,
            message=message,
        )

    def save(self, index=0, **kwargs):
        status, _ = self.run(FACTS[index], **kwargs)
        assert status == "saved", status
        return next(item for item in self.inspect() if item["content"] == FACTS[index])

    def prepare(self, kind, body):
        if kind == "one":
            body = {
                "person_id": str(self.person),
                "relationship_id": str(self.relationship),
                **body,
            }
        return self.call("POST", f"/memory/deletions/{kind}/prepare", body)

    def execute(self, challenge, key=None, **kwargs):
        return self.call(
            "POST",
            f"/memory/deletions/{challenge['confirmation_id']}/execute",
            {"operation_key": key or uuid4().hex},
            **kwargs,
        )

    def expire(self, memory):
        with Session(self.engine) as db, db.begin():
            db.get(MemoryRecordRow, UUID(memory["id"])).expires_at = datetime.now(UTC) - timedelta(
                seconds=1
            )

    def cleanup(self, **kwargs):
        return MemoryRetentionService(lambda: Session(self.engine)).run(**kwargs)


@pytest.fixture
def flow(database_engine, monkeypatch, tmp_path):
    provider = Phase6Mock()
    monkeypatch.setattr("app.api.dependencies.create_llm_provider", lambda settings: provider)
    app = create_app(
        Settings(
            app_env="test",
            database_url=database_engine.url.render_as_string(hide_password=False),
            auth_jwt_secret=SECRET,
            auth_jwt_issuer="phase6d-test",
            auth_jwt_audience="phase6d-api",
            llm_provider="mock",
            chat_import_artifact_root=tmp_path / "artifacts",
            _env_file=None,
        )
    )
    assert not app.dependency_overrides
    with TestClient(app) as client:
        yield Flow(database_engine, client, provider, create_scope(database_engine))


def test_grant_save_inspect_same_durable_control(flow):
    initial = flow.call("GET", "/memory/control")
    assert not initial["consent_enabled"]
    assert flow.run(FACTS[0])[0] != "saved"
    assert flow.inspect() == []
    assert flow.grant()["effective_write_enabled"]
    item = flow.save()
    detail = flow.call("GET", f"/memories/{item['id']}")
    assert detail == item and detail["state"] == "active"
    assert detail["person_id"] == str(flow.person)
    assert detail["relationship_id"] == str(flow.relationship)
    assert detail["expires_at"] > detail["created_at"]
    with Session(flow.engine) as db:
        assert db.get(MemoryRecordRow, UUID(item["id"])) is not None
    flow.run()
    history = flow.provider.analysis_payloads[-1]["historical_memory"]
    assert len(history) == 1 and history[0]["historical"] is True
    assert flow.provider.analysis_payloads[-1]["user_evidence"]["facts"] == []


def test_pause_revoke_regrant_resume_keep_inspection_and_chat(flow):
    flow.grant()
    item = flow.save()
    for route, body in (("pause", None), ("consent", {"enabled": False})):
        control = flow.call("POST", f"/memory/{route}", body)
        assert not control["effective_read_enabled"] and not control["effective_write_enabled"]
        flow.run(FACTS[1])
        assert flow.provider.analysis_payloads[-1]["historical_memory"] == []
        assert flow.inspect() == [item]
    assert not flow.call("POST", "/memory/resume")["consent_enabled"]
    assert flow.grant()["paused"]
    assert flow.call("POST", "/memory/resume")["effective_write_enabled"]
    flow.run()
    assert len(flow.provider.analysis_payloads[-1]["historical_memory"]) == 1
    flow.save(1)
    with Session(flow.engine) as db:
        assert (
            len(
                db.scalars(
                    select(Message).where(Message.conversation_id == flow.conversation)
                ).all()
            )
            == 10
        )


@pytest.mark.parametrize("decision", ["pause", "revoke"])
@pytest.mark.parametrize("stream", [False, True])
def test_committed_control_change_blocks_inflight_candidate(flow, decision, stream):
    flow.grant()
    flow.provider.block_candidates = True
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(flow.run, FACTS[0], stream=stream)
        try:
            assert flow.provider.candidate_entered.wait(10)
            if decision == "pause":
                flow.call("POST", "/memory/pause")
            else:
                flow.call("POST", "/memory/consent", {"enabled": False})
        finally:
            flow.provider.candidate_release.set()
        assert pending.result(timeout=10)[0] == (
            "skipped_paused" if decision == "pause" else "skipped_no_consent"
        )
    assert flow.inspect() == []


def test_guarded_undo_receipt_replay_new_session_preserves_older_memory(flow):
    flow.grant()
    older, newer = flow.save(0), flow.save(1)
    preview = flow.call("GET", "/memory/undo/preview")
    assert preview["memory_id"] == newer["id"]
    body = {"expected_operation_id": preview["latest_operation_id"], "operation_key": "undo-B"}
    receipt = flow.call("POST", "/memory/undo", body)
    assert receipt["undone_memory_id"] == newer["id"]
    with Session(flow.engine) as db:
        assert db.get(MemoryMutationRow, UUID(receipt["mutation_id"])) is not None
    # New HTTP connection/session, with the same real JWT and persisted operation key.
    with TestClient(flow.client.app) as second:
        replay = second.post("/api/v1/memory/undo", headers=flow.headers, json=body).json()
    assert replay["replayed"] and replay["mutation_id"] == receipt["mutation_id"]
    assert flow.inspect() == [older]
    flow.run()
    assert [
        item["content"] for item in flow.provider.analysis_payloads[-1]["historical_memory"]
    ] == [FACTS[0]]
    flow.call("POST", "/memory/undo", {**body, "expected_operation_id": str(uuid4())}, status=409)


def test_two_undo_keys_cannot_fall_back_to_older_operation(flow):
    flow.grant()
    older, _ = flow.save(0), flow.save(1)
    operation = flow.call("GET", "/memory/undo/preview")["latest_operation_id"]

    def undo(key):
        return flow.client.post(
            "/api/v1/memory/undo",
            headers=flow.headers,
            json={"expected_operation_id": operation, "operation_key": key},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(undo, ["race-one", "race-two"]))
    assert sorted(response.status_code for response in responses) == [200, 409]
    assert flow.inspect() == [older]


@pytest.mark.parametrize("clean", [False, True])
def test_expired_latest_undo_never_removes_older_active_record(flow, clean):
    flow.grant()
    older, newer = flow.save(0), flow.save(1)
    operation = flow.call("GET", "/memory/undo/preview")["latest_operation_id"]
    flow.expire(newer)
    if clean:
        assert flow.cleanup(dry_run=False, max_batches=100).status == "ok"
    else:
        assert not flow.call("GET", "/memory/undo/preview")["available"]
    flow.call(
        "POST",
        "/memory/undo",
        {"expected_operation_id": operation, "operation_key": "expired-undo"},
        status=409,
    )
    assert flow.inspect() == [older]


def test_delete_one_prepare_execute_recall_and_receipt_replay(flow):
    flow.grant()
    older, target = flow.save(0), flow.save(1)
    challenge = flow.prepare(
        "one",
        {
            "memory_id": target["id"],
            "person_id": str(flow.person),
            "relationship_id": str(flow.relationship),
        },
    )
    assert challenge["expected_count"] == 1 and len(flow.inspect()) == 2
    receipt = flow.execute(challenge, "delete-one")
    assert receipt["affected_count"] == 1 and receipt["primary_store_only"]
    assert flow.execute(challenge, "delete-one")["replayed"]
    assert flow.inspect() == [older]
    flow.run()
    assert [
        item["content"] for item in flow.provider.analysis_payloads[-1]["historical_memory"]
    ] == [FACTS[0]]
    assert (
        flow.call("GET", f"/memory/mutations/{receipt['mutation_id']}")["mutation_id"]
        == receipt["mutation_id"]
    )


def test_delete_person_keeps_other_person_and_entities(flow):
    flow.grant()
    flow.save()
    with Session(flow.engine) as db, db.begin():
        other = records.create_person(db, flow.owner, "Synthetic B")
        relation = records.create_relationship(db, flow.owner, other.id, "dating", "active")
        conversation = records.create_conversation(db, flow.owner, relation.id)
        other_id, conversation_id = other.id, conversation.id
    remaining = flow.save(1, conversation=conversation_id)
    assert flow.provider.analysis_payloads[-1]["historical_memory"] == []
    flow.run(conversation=conversation_id)
    assert [
        item["content"] for item in flow.provider.analysis_payloads[-1]["historical_memory"]
    ] == [FACTS[1]]
    flow.run()
    assert [
        item["content"] for item in flow.provider.analysis_payloads[-1]["historical_memory"]
    ] == [FACTS[0]]
    challenge = flow.prepare("person", {"person_id": str(flow.person)})
    assert flow.execute(challenge)["affected_count"] == 1
    assert flow.inspect() == [remaining]
    with Session(flow.engine) as db:
        assert db.get(Person, flow.person) and db.get(Person, other_id)
        assert db.get(Relationship, flow.relationship)
        assert db.get(Conversation, flow.conversation)


@pytest.mark.parametrize("revoke", [False, True])
def test_delete_all_explicit_consent_choice_and_chats_survive(flow, revoke):
    flow.grant()
    flow.save(0)
    flow.save(1)
    challenge = flow.prepare("all", {"revoke_consent_after_delete": revoke})
    assert len(flow.inspect()) == 2
    assert flow.execute(challenge)["affected_count"] == 2
    assert flow.inspect() == []
    control = flow.call("GET", "/memory/control")
    assert control["consent_enabled"] is (not revoke)
    assert control["paused"] is revoke
    flow.run()
    assert flow.provider.analysis_payloads[-1]["historical_memory"] == []
    with Session(flow.engine) as db:
        assert db.get(Person, flow.person) and db.get(Relationship, flow.relationship)
        assert db.get(Conversation, flow.conversation)
        assert (
            len(
                db.scalars(
                    select(Message).where(Message.conversation_id == flow.conversation)
                ).all()
            )
            == 6
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(MemoryOperationRow)
                .where(MemoryOperationRow.owner_user_id == flow.owner)
            )
            == 0
        )


def test_delete_challenge_expiry_tampering_consumption_and_scope_growth(flow):
    flow.grant()
    memory = flow.save()
    flow.call(
        "POST", f"/memory/deletions/{uuid4()}/execute", {"operation_key": "missing"}, status=409
    )
    challenge = flow.prepare("all", {"revoke_consent_after_delete": False})
    # Clients cannot alter the stored action/target after prepare.
    flow.call(
        "POST",
        f"/memory/deletions/{challenge['confirmation_id']}/execute",
        {"operation_key": "tamper", "action": "delete_person", "target_id": str(flow.person)},
        status=422,
    )
    flow.save(1)
    flow.execute(challenge, status=409)
    assert len(flow.inspect()) == 2
    expired = flow.prepare("one", {"memory_id": memory["id"]})
    with Session(flow.engine) as db, db.begin():
        db.get(MemoryConfirmationRow, UUID(expired["confirmation_id"])).expires_at = datetime.now(
            UTC
        ) - timedelta(seconds=1)
    flow.execute(expired, status=409)
    valid = flow.prepare("one", {"memory_id": memory["id"]})
    flow.execute(valid, "consumed")
    flow.execute(valid, "second-key", status=409)
    assert len(flow.inspect()) == 1


def test_delete_receipt_survives_challenge_cleanup_and_payload_conflicts(flow):
    flow.grant()
    memory = flow.save()
    challenge = flow.prepare("one", {"memory_id": memory["id"]})
    receipt = flow.execute(challenge, "durable-delete")
    with Session(flow.engine) as db, db.begin():
        db.get(MemoryConfirmationRow, UUID(challenge["confirmation_id"])).expires_at = datetime.now(
            UTC
        ) - timedelta(days=2)
    result = flow.cleanup(dry_run=False, max_batches=100)
    assert result.status == "ok" and result.counts.mutation_receipts_removed == 0
    with Session(flow.engine) as db:
        assert db.get(MemoryConfirmationRow, UUID(challenge["confirmation_id"])) is None
    assert flow.execute(challenge, "durable-delete")["mutation_id"] == receipt["mutation_id"]
    flow.call(
        "POST",
        f"/memory/deletions/{uuid4()}/execute",
        {"operation_key": "durable-delete"},
        status=409,
    )


def test_expiry_excludes_recall_before_bounded_cleanup_and_keeps_controls(flow):
    flow.grant()
    active, expired = flow.save(0), flow.save(1)
    control = flow.call("GET", "/memory/control")
    flow.expire(expired)
    assert flow.call("GET", f"/memories/{expired['id']}")["state"] == "expired"
    assert flow.inspect() == [active]
    flow.run()
    assert [
        item["content"] for item in flow.provider.analysis_payloads[-1]["historical_memory"]
    ] == [FACTS[0]]
    before = flow.cleanup(dry_run=True)
    assert before.counts.memory_records >= 1 and before.batches_committed == 0
    with Session(flow.engine) as db:
        assert db.get(MemoryRecordRow, UUID(expired["id"])) is not None
    cleaned = flow.cleanup(dry_run=False, batch_size=1, max_batches=100)
    assert cleaned.status == "ok" and cleaned.counts.undo_operations >= 1
    assert flow.cleanup(dry_run=False).counts.memory_records == 0
    flow.call("GET", f"/memories/{expired['id']}", status=404)
    assert flow.call("GET", "/memory/control") == control


def test_expired_duplicate_resave_new_id_expiry_and_undo_active_duplicate_stays(flow):
    cases = [
        json.loads(line)
        for line in (Path(__file__).resolve().parents[3] / "evals/golden_cases.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    fixture = next(case for case in cases if case["id"] == "memory_retention_expired_01")[
        "retention_fixture"
    ]["resave_after_expiry"]
    assert fixture["content"] == FACTS[0] and fixture["expected_status"] == "saved"
    flow.grant()
    old = flow.save()
    old_operation = flow.call("GET", "/memory/undo/preview")["latest_operation_id"]
    assert flow.run(FACTS[0])[0] == "duplicate"
    flow.expire(old)
    new = flow.save()
    assert new["id"] != old["id"] and new["created_at"] > old["created_at"]
    assert new["expires_at"] > old["expires_at"]
    flow.call("GET", f"/memories/{old['id']}", status=404)
    with Session(flow.engine) as db:
        assert db.get(MemoryOperationRow, UUID(old_operation)) is None
    preview = flow.call("GET", "/memory/undo/preview")
    assert preview["memory_id"] == new["id"] and preview["latest_operation_id"] != old_operation
    assert len(flow.inspect()) == 1


def test_actual_agent_recall_at_exact_utc_expiry_boundary(flow, monkeypatch):
    from app.db.repositories.memory import SQLAlchemyMemoryStore

    clock = [datetime.now(UTC)]
    monkeypatch.setattr(
        "app.api.dependencies.SQLAlchemyMemoryStore",
        lambda factory, **kwargs: SQLAlchemyMemoryStore(factory, clock=lambda: clock[0], **kwargs),
    )
    flow.grant()
    flow.save(0)
    expiring = flow.save(1)
    expiry = clock[0] + timedelta(days=1)
    with Session(flow.engine) as db, db.begin():
        db.get(MemoryRecordRow, UUID(expiring["id"])).expires_at = expiry
    clock[0] = expiry - timedelta(microseconds=1)
    flow.run()
    assert len(flow.provider.analysis_payloads[-1]["historical_memory"]) == 2
    clock[0] = expiry
    flow.run()
    assert [
        item["content"] for item in flow.provider.analysis_payloads[-1]["historical_memory"]
    ] == [FACTS[0]]


@pytest.mark.parametrize("decision", ["pause", "revoke"])
def test_expired_duplicate_without_effective_consent_keeps_old_row(flow, decision):
    flow.grant()
    old = flow.save()
    flow.expire(old)
    flow.call(
        "POST",
        "/memory/pause" if decision == "pause" else "/memory/consent",
        None if decision == "pause" else {"enabled": False},
    )
    assert flow.run(FACTS[0])[0] != "saved"
    with Session(flow.engine) as db:
        assert db.get(MemoryRecordRow, UUID(old["id"])) is not None
        assert (
            db.scalar(
                select(func.count())
                .select_from(MemoryOperationRow)
                .where(MemoryOperationRow.owner_user_id == flow.owner)
            )
            == 1
        )


def test_concurrent_expired_duplicate_has_one_new_record_and_operation(flow):
    flow.grant()
    old = flow.save()
    flow.expire(old)
    with Session(flow.engine) as db, db.begin():
        other = records.create_conversation(db, flow.owner, flow.relationship).id
    with ThreadPoolExecutor(max_workers=2) as pool:
        one = pool.submit(flow.run, FACTS[0])
        two = pool.submit(flow.run, FACTS[0], conversation=other)
        assert sorted([one.result(timeout=10)[0], two.result(timeout=10)[0]]) == [
            "duplicate",
            "saved",
        ]
    assert len(flow.inspect()) == 1 and flow.inspect()[0]["id"] != old["id"]
    with Session(flow.engine) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(MemoryOperationRow)
                .where(MemoryOperationRow.owner_user_id == flow.owner)
            )
            == 1
        )


def test_expired_replacement_transaction_failure_restores_old_record_and_undo(flow):
    flow.grant()
    old = flow.save()
    operation = flow.call("GET", "/memory/undo/preview")["latest_operation_id"]
    flow.expire(old)

    def fail_operation(session, context, instances):
        if any(
            isinstance(row, MemoryOperationRow) and row.owner_user_id == flow.owner
            for row in session.new
        ):
            raise RuntimeError("synthetic private SQL token")

    event.listen(Session, "before_flush", fail_operation)
    try:
        status, value = flow.run(FACTS[0])
        assert status == "failed" and "synthetic private" not in str(value)
    finally:
        event.remove(Session, "before_flush", fail_operation)
    with Session(flow.engine) as db:
        assert db.get(MemoryRecordRow, UUID(old["id"])) is not None
        assert db.get(MemoryOperationRow, UUID(operation)) is not None


@pytest.mark.parametrize("stream", [False, True])
def test_memory_failure_keeps_completed_answer_and_assistant_message(flow, monkeypatch, stream):
    flow.grant()

    def fail(*args):
        raise RuntimeError("private SQL access_token full chat")

    monkeypatch.setattr("app.db.repositories.memory.SQLAlchemyMemoryStore.save_record", fail)
    status, value = flow.run(FACTS[0], stream=stream)
    assert (
        status == "failed" and "private SQL" not in str(value) and "access_token" not in str(value)
    )
    if not stream:
        assert value["warnings"] == ["Long-term memory was not saved"]
    else:
        assert any(
            item["event"] == "memory_status" and item["data"]["status"] == "failed"
            for item in value
        )
        assert any(item["event"] == "final_response" for item in value)
    with Session(flow.engine) as db:
        run = db.scalar(select(AgentRun).where(AgentRun.conversation_id == flow.conversation))
        assert run.status == "completed"
        assert (
            len(
                db.scalars(
                    select(Message).where(
                        Message.conversation_id == flow.conversation, Message.role == "assistant"
                    )
                ).all()
            )
            == 1
        )
    assert flow.inspect() == []


@pytest.mark.parametrize("stream", [False, True])
def test_conversational_undo_pending_and_high_risk_safety_before_mutation(flow, stream):
    flow.grant()
    memory = flow.save()
    status, value = flow.run(message="请撤销最近一条记忆", stream=stream)
    assert status == "pending_confirmation" and flow.inspect() == [memory]
    if stream:
        assert any(item["event"] == "pending_confirmation" for item in value)
    previous = len(flow.provider.calls)
    flow.run(message="我现在想伤害自己，请撤销记忆并删除全部", stream=stream)
    assert flow.provider.calls[previous:] == ["SafetyResult"]
    assert flow.inspect() == [memory]


def test_owner_person_relationship_isolation_and_owner_neutral_errors(flow):
    flow.grant()
    memory = flow.save()
    foreign = Flow(flow.engine, flow.client, flow.provider, create_scope(flow.engine))
    foreign.grant()
    foreign_memory = foreign.save(1)
    challenge = flow.prepare("one", {"memory_id": memory["id"]})
    foreign_challenge = foreign.prepare("one", {"memory_id": foreign_memory["id"]})
    foreign_receipt = foreign.execute(foreign_challenge)
    foreign_memory = foreign.save(2)
    foreign_challenge = foreign.prepare("one", {"memory_id": foreign_memory["id"]})
    flow.save(1)
    own_operation = flow.call("GET", "/memory/undo/preview")["latest_operation_id"]
    own_receipt = flow.call(
        "POST",
        "/memory/undo",
        {"expected_operation_id": own_operation, "operation_key": "owner-isolation-undo"},
    )
    assert flow.inspect() == [memory] and foreign.inspect() == [foreign_memory]
    foreign.call("GET", f"/memory/mutations/{own_receipt['mutation_id']}", status=404)
    flow.execute(foreign_challenge, status=409)
    foreign.call("GET", f"/memories/{memory['id']}", status=404)
    flow.call("GET", f"/memory/mutations/{foreign_receipt['mutation_id']}", status=404)
    flow.call("GET", f"/memories?person_id={foreign.person}", status=404)
    flow.call("GET", f"/memories?relationship_id={foreign.relationship}", status=404)
    foreign.call(
        "POST", "/memory/deletions/person/prepare", {"person_id": str(flow.person)}, status=404
    )
    foreign.execute(challenge, status=409)
    operation = flow.call("GET", "/memory/undo/preview")["latest_operation_id"]
    foreign.call(
        "POST",
        "/memory/undo",
        {"expected_operation_id": operation, "operation_key": "foreign"},
        status=409,
    )
    flow.call(
        "POST", "/memory/consent", {"enabled": False, "user_id": str(foreign.owner)}, status=422
    )
    assert flow.inspect() == [memory]
    assert foreign.call("GET", "/memory/control")["effective_write_enabled"]
    # Unknown and foreign IDs have identical public status/code, without owner information.
    missing = flow.call("GET", f"/memories/{uuid4()}", status=404)
    hidden = flow.call("GET", f"/memories/{foreign_memory['id']}", status=404)
    assert missing == hidden


def test_phase5_http_import_then_memory_delete_cleanup_preserves_imports(flow):
    transcript = (
        b"## 2023-11-09 07:51:23 self\n\nsynthetic imported self\n"
        b"## 2023-11-09 07:51:24 A\n\nsynthetic imported other\n"
    )
    uploaded = flow.client.post(
        "/api/v1/chat-imports",
        headers=flow.headers,
        data={"source_timezone": "Asia/Shanghai"},
        files={"file": ("chat.md", transcript, "application/octet-stream")},
    )
    assert uploaded.status_code == 201, uploaded.text
    job = uploaded.json()
    path = f"/chat-imports/{job['id']}"
    revision = job["binding_revision"]
    for label, kind, person in (("self", "self", None), ("A", "person", str(flow.person))):
        bound = flow.call(
            "PUT",
            path + "/speakers",
            {
                "raw_speaker_label": label,
                "binding_kind": kind,
                "person_id": person,
                "expected_revision": revision,
            },
        )
        revision = bound["binding_revision"]
    flow.call(
        "PUT",
        path + "/relationship",
        {"relationship_id": str(flow.relationship), "expected_revision": revision},
    )
    ready = flow.call("POST", path + "/ready")
    flow.call("POST", path + "/finalize", {"expected_revision": ready["binding_revision"]})
    assert flow.inspect() == []
    flow.grant()
    memory = flow.save()
    analysis = flow.provider.analysis_payloads[-1]
    assert "synthetic imported" not in str(analysis)
    assert "synthetic imported" not in str(flow.provider.context_payloads[-1])
    before = {}
    models = [Conversation, Message, RelationshipMessage, ChatImportJob, Person, Relationship]
    with Session(flow.engine) as db:
        for model in models:
            before[model] = db.scalar(select(func.count()).select_from(model))
    flow.execute(flow.prepare("one", {"memory_id": memory["id"]}))
    flow.save(0)
    flow.execute(flow.prepare("person", {"person_id": str(flow.person)}))
    flow.save(1)
    flow.execute(flow.prepare("all", {"revoke_consent_after_delete": False}))
    last = flow.save(2)
    flow.expire(last)
    assert flow.cleanup(dry_run=False, max_batches=100).status == "ok"
    with Session(flow.engine) as db:
        for model in models:
            count = db.scalar(select(func.count()).select_from(model))
            assert count == before[model] + (6 if model is Message else 0)
        assert db.get(MemoryRecordRow, UUID(memory["id"])) is None
        assert db.get(ChatImportJob, UUID(job["id"])) is not None
        imported = db.scalars(
            select(RelationshipMessage).where(
                RelationshipMessage.relationship_id == flow.relationship
            )
        ).all()
        assert len(imported) == 2


def test_public_contract_signed_auth_validation_and_safe_openapi(flow):
    schema = flow.client.get("/openapi.json").json()
    fields = schema["components"]["schemas"]["MemoryRecordView"]["properties"]
    assert (
        not {"content_hash", "evidence", "first_run_id", "confidence", "chain_of_thought"}
        & fields.keys()
    )
    paths = schema["paths"]
    routes = {
        path: methods
        for path, methods in paths.items()
        if path.startswith("/api/v1/memory") or path.startswith("/api/v1/memories")
    }
    assert len(routes) == 13
    for path, methods in routes.items():
        reified_path = path
        for parameter in ("memory_id", "confirmation_id", "mutation_id"):
            reified_path = reified_path.replace("{" + parameter + "}", str(uuid4()))
        url = reified_path
        for method, operation in methods.items():
            assert operation["security"]
            assert "200" in operation["responses"]
            result = flow.client.request(method, url, json={})
            assert result.status_code == 401
    flow.call("GET", "/memory/control", auth={"Authorization": "Bearer invalid"}, status=401)
    flow.call("GET", "/memories?limit=51", status=422)
    flow.call("GET", "/memories?cursor=invalid", status=400)
    flow.call("POST", "/memory/deletions/all/prepare", {}, status=422)
    flow.call(
        "POST",
        "/memory/undo",
        {"expected_operation_id": str(uuid4()), "operation_key": ""},
        status=400,
    )


def test_memory_controls_mutations_and_cleanup_never_call_llm(flow):
    flow.grant()
    flow.call("POST", "/memory/pause")
    flow.call("POST", "/memory/resume")
    flow.call("GET", "/memory/undo/preview")
    flow.inspect()
    challenge = flow.prepare("all", {"revoke_consent_after_delete": False})
    receipt = flow.execute(challenge, "empty-delete")
    assert receipt["affected_count"] == 0
    flow.cleanup(dry_run=True)
    flow.cleanup(dry_run=False)
    flow.call("POST", "/memory/consent", {"enabled": False})
    assert flow.provider.calls == []


def test_standalone_inmemory_expired_duplicate_matches_new_save_semantics():
    from app.agent.contracts import Fact, MemoryCandidate, MemoryControl
    from app.agent.memory import InMemoryMemoryStore, MemoryService

    owner, person, relationship = uuid4(), uuid4(), uuid4()
    clock = [datetime.now(UTC)]
    store = InMemoryMemoryStore()
    store.bind_relationship(owner, relationship, person)
    store.set_control(owner, MemoryControl(consent_enabled=True))
    service = MemoryService(store, clock=lambda: clock[0])

    def save():
        return service.persist_candidates(
            user_id=owner,
            relationship_id=relationship,
            run_id=uuid4(),
            candidates=[
                MemoryCandidate(
                    subject_id=person,
                    type="relationship",
                    content=FACTS[0],
                    source="user_explicit",
                    evidence="F1",
                )
            ],
            facts=[Fact(statement=FACTS[0], source="user_explicit")],
            message=FACTS[0] + "。请保存长期记忆",
            explicit_consent=False,
        )

    assert save().status == "saved"
    old = next(iter(store.records.values()))
    assert save().status == "duplicate"
    clock[0] = old.expires_at
    assert save().status == "saved"
    new = next(iter(store.records.values()))
    assert len(store.records) == 1 and new.id != old.id and new.expires_at > old.expires_at
    assert store.operations[owner] == [new.id]
