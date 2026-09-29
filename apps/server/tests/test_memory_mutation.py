"""Phase 6B PostgreSQL, signed HTTP, retry and Agent deletion gates."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from agent_demo import CaptureMock, queue_run
from fastapi.testclient import TestClient
from memory_control_demo import run_agent
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_import_merge import factory, merge, ready_job, transcript
from test_memory_control import _app, _headers, _save, _scope

from app.agent.contracts import Fact, MemoryCandidate, MemoryWriteStatus
from app.agent.memory import MemoryService
from app.db.models import (
    ChatImportJob,
    Conversation,
    MemoryConfirmationRow,
    MemoryMutationRow,
    MemoryOperationRow,
    Message,
    Person,
    Relationship,
    RelationshipMessage,
)
from app.db.repositories import records
from app.db.repositories.memory import SQLAlchemyMemoryStore
from app.services.agent_service import actor_from_verified_identity
from app.services.memory_mutation import (
    MemoryMutationError,
    MemoryMutationErrorCode,
    MemoryMutationService,
)


def _store(engine):
    return SQLAlchemyMemoryStore(lambda: Session(engine))


def _service(engine, *, clock=None):
    return MemoryMutationService(lambda: Session(engine), clock=clock)


def _failure(code, call):
    with pytest.raises(MemoryMutationError) as caught:
        call()
    assert caught.value.code == code


def _save_without_new_consent(store, owner, person, relationship, content):
    return MemoryService(store).persist_candidates(
        user_id=owner,
        relationship_id=relationship,
        run_id=uuid4(),
        candidates=[
            MemoryCandidate(
                subject_id=person,
                type="relationship",
                content=content,
                source="user_explicit",
                evidence="F1",
            )
        ],
        facts=[Fact(statement=content, source="user_explicit")],
        message=f"请记住{content}，写入长期记忆。",
        explicit_consent=False,
    )


def test_undo_preview_guarded_retry_and_new_attempt(database_engine):
    owner, _, person, _, relationship, _, _ = _scope(database_engine)
    store = _store(database_engine)
    first, second = "我们计划第一周见面", "我们计划第二周见面"
    _save(store, owner, person, relationship, first)
    _save(store, owner, person, relationship, second)
    actor = actor_from_verified_identity(owner)
    service = _service(database_engine)
    with Session(database_engine) as db:
        operations_before = {
            (row.id, row.updated_at) for row in db.scalars(select(MemoryOperationRow)).all()
        }
    preview = service.preview_undo(actor)
    assert preview.available and preview.type == "relationship"
    assert preview.memory_id == next(
        row.id for row in store.list_records(owner) if row.content == second
    )
    with Session(database_engine) as db:
        assert {
            (row.id, row.updated_at) for row in db.scalars(select(MemoryOperationRow)).all()
        } == operations_before
    receipt = service.undo(
        actor, expected_operation_id=preview.latest_operation_id, operation_key="undo-1"
    )
    assert receipt.status == "undone" and receipt.affected_count == 1
    assert receipt.undone_memory_id == preview.memory_id and not receipt.replayed
    replay = _service(database_engine).undo(
        actor, expected_operation_id=preview.latest_operation_id, operation_key="undo-1"
    )
    assert replay.mutation_id == receipt.mutation_id and replay.replayed
    assert [record.content for record in store.list_records(owner)] == [first]
    _failure(
        MemoryMutationErrorCode.STALE_UNDO,
        lambda: service.undo(
            actor, expected_operation_id=preview.latest_operation_id, operation_key="undo-2"
        ),
    )
    _failure(
        MemoryMutationErrorCode.MUTATION_CONFLICT,
        lambda: service.undo(actor, expected_operation_id=uuid4(), operation_key="undo-1"),
    )
    next_preview = service.preview_undo(actor)
    service.undo(
        actor, expected_operation_id=next_preview.latest_operation_id, operation_key="undo-2"
    )
    assert store.list_records(owner) == []
    assert not service.preview_undo(actor).available
    _failure(
        MemoryMutationErrorCode.UNDO_UNAVAILABLE,
        lambda: service.undo(actor, expected_operation_id=uuid4(), operation_key="undo-3"),
    )


def test_concurrent_undo_same_expected_operation(database_engine):
    owner, _, person, _, relationship, _, _ = _scope(database_engine)
    store = _store(database_engine)
    _save(store, owner, person, relationship, "我们计划第一周见面")
    _save(store, owner, person, relationship, "我们计划第二周见面")
    actor = actor_from_verified_identity(owner)
    expected = _service(database_engine).preview_undo(actor).latest_operation_id

    def attempt(index):
        try:
            return (
                _service(database_engine)
                .undo(actor, expected_operation_id=expected, operation_key=f"race-undo-{index}")
                .status
            )
        except MemoryMutationError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))
    assert sorted(results) == ["stale_undo", "undone"]
    assert len(store.list_records(owner)) == 1


def test_runtime_undo_changes_public_expected_operation(database_engine):
    owner, _, person, _, relationship, _, _ = _scope(database_engine)
    store = _store(database_engine)
    _save(store, owner, person, relationship, "我们计划第一周见面")
    _save(store, owner, person, relationship, "我们计划第二周见面")
    actor = actor_from_verified_identity(owner)
    preview = _service(database_engine).preview_undo(actor)
    assert MemoryService(store).undo_last(owner).status == MemoryWriteStatus.UNDONE
    _failure(
        MemoryMutationErrorCode.STALE_UNDO,
        lambda: _service(database_engine).undo(
            actor, expected_operation_id=preview.latest_operation_id, operation_key="runtime-race"
        ),
    )
    assert len(store.list_records(owner)) == 1


def test_delete_one_challenge_replay_owner_and_history(database_engine):
    owner, outsider, person, other_person, relationship, other_relationship, _ = _scope(
        database_engine
    )
    store = _store(database_engine)
    _save(store, owner, person, relationship, "我们计划第一周见面")
    _save(store, owner, other_person, other_relationship, "我们计划第二周见面")
    first_id = next(row.id for row in store.list_records(owner) if row.person_id == person)
    actor, foreign = actor_from_verified_identity(owner), actor_from_verified_identity(outsider)
    moment = [datetime.now(UTC)]
    service = _service(database_engine, clock=lambda: moment[0])
    _failure(
        MemoryMutationErrorCode.MEMORY_NOT_FOUND,
        lambda: service.prepare_delete_one(
            foreign, memory_id=first_id, person_id=person, relationship_id=relationship
        ),
    )
    _failure(
        MemoryMutationErrorCode.MEMORY_NOT_FOUND,
        lambda: service.prepare_delete_one(
            actor, memory_id=first_id, person_id=other_person, relationship_id=relationship
        ),
    )
    challenge = service.prepare_delete_one(
        actor, memory_id=first_id, person_id=person, relationship_id=relationship
    )
    assert challenge.expected_count == 1 and len(store.list_records(owner)) == 2
    _failure(
        MemoryMutationErrorCode.CONFIRMATION_REQUIRED,
        lambda: service.execute_delete(
            foreign, confirmation_id=challenge.confirmation_id, operation_key="foreign"
        ),
    )
    receipt = service.execute_delete(
        actor, confirmation_id=challenge.confirmation_id, operation_key="one-key"
    )
    assert receipt.action == "delete_one" and receipt.affected_count == 1
    assert receipt.primary_store_only and not receipt.replayed
    moment[0] += timedelta(minutes=6)
    replay = _service(database_engine, clock=lambda: moment[0]).execute_delete(
        actor, confirmation_id=challenge.confirmation_id, operation_key="one-key"
    )
    assert replay.mutation_id == receipt.mutation_id and replay.replayed
    _failure(
        MemoryMutationErrorCode.CONFIRMATION_STALE,
        lambda: service.execute_delete(
            actor, confirmation_id=challenge.confirmation_id, operation_key="new-key"
        ),
    )
    assert store.get_record(owner, first_id) is None
    assert len(store.list_records(owner)) == 1
    assert service.preview_undo(actor).memory_id == store.list_records(owner)[0].id
    with Session(database_engine) as db:
        assert (
            db.scalar(select(MemoryOperationRow).where(MemoryOperationRow.record_id == first_id))
            is None
        )
    _failure(
        MemoryMutationErrorCode.MUTATION_NOT_FOUND,
        lambda: service.inspect_receipt(foreign, receipt.mutation_id),
    )
    assert service.inspect_receipt(actor, receipt.mutation_id).mutation_id == receipt.mutation_id


def test_person_and_all_delete_preserve_domains_and_consent(database_engine):
    owner, _, person_a, person_b, relation_a, relation_b, conversation_a = _scope(database_engine)
    store = _store(database_engine)
    _save(store, owner, person_a, relation_a, "我们计划第一周见面")
    _save(store, owner, person_a, relation_a, "我们计划第二周见面")
    _save(store, owner, person_b, relation_b, "我们计划第三周见面")
    with Session(database_engine) as db:
        conversation_b = records.create_conversation(db, owner, relation_b)
        message = records.create_message(db, owner, conversation_a, "user", "Synthetic message")
        assert message is not None
        message_id = message.id
        conversation_b_id = conversation_b.id
        db.commit()
    actor, service = actor_from_verified_identity(owner), _service(database_engine)
    source = transcript((1, "我", "Synthetic import"), (2, "A", "Synthetic reply"))
    _, import_job_id, _, _, revision = ready_job(
        factory(database_engine),
        source,
        actor=actor,
        person_id=person_a,
        relationship_id=relation_a,
    )
    merge(factory(database_engine), actor, import_job_id, revision, source)
    challenge = service.prepare_delete_person(actor, person_id=person_a)
    assert challenge.expected_count == 2 and len(store.list_records(owner)) == 3
    receipt = service.execute_delete(
        actor, confirmation_id=challenge.confirmation_id, operation_key="person-key"
    )
    assert receipt.affected_count == 2
    assert [row.person_id for row in store.list_records(owner)] == [person_b]
    assert MemoryService(store).load_for_context(owner, relation_a, enabled=True) == []
    assert len(MemoryService(store).load_for_context(owner, relation_b, enabled=True)) == 1
    assert (
        asyncio.run(
            run_agent(
                database_engine, owner, person_a, relation_a, conversation_a, store, save=False
            )
        )[1]
        == 0
    )
    assert (
        asyncio.run(
            run_agent(
                database_engine, owner, person_b, relation_b, conversation_b_id, store, save=False
            )
        )[1]
        == 1
    )
    all_challenge = service.prepare_delete_all(actor, revoke_consent_after_delete=False)
    assert all_challenge.expected_count == 1
    service.execute_delete(
        actor, confirmation_id=all_challenge.confirmation_id, operation_key="all-keep-key"
    )
    assert store.list_records(owner) == []
    assert MemoryService(store).control(owner).consent_enabled
    assert (
        asyncio.run(
            run_agent(
                database_engine, owner, person_b, relation_b, conversation_b_id, store, save=False
            )
        )[1]
        == 0
    )
    assert (
        _save_without_new_consent(store, owner, person_b, relation_b, "我们计划第四周见面").status
        == MemoryWriteStatus.SAVED
    )
    revoke_challenge = service.prepare_delete_all(actor, revoke_consent_after_delete=True)
    service.execute_delete(
        actor, confirmation_id=revoke_challenge.confirmation_id, operation_key="all-revoke-key"
    )
    assert store.list_records(owner) == []
    assert not MemoryService(store).control(owner).consent_enabled
    assert (
        _save_without_new_consent(store, owner, person_b, relation_b, "我们计划第五周见面").status
        == MemoryWriteStatus.SKIPPED_NO_CONSENT
    )
    with Session(database_engine) as db:
        assert db.get(Conversation, conversation_a) is not None
        assert db.get(Conversation, conversation_b_id) is not None
        assert db.get(Message, message_id) is not None
        assert db.get(Person, person_a) is not None
        assert db.get(Relationship, relation_a) is not None
        assert (
            db.scalar(
                select(func.count())
                .select_from(MemoryOperationRow)
                .where(MemoryOperationRow.owner_user_id == owner)
            )
            == 0
        )
        assert db.get(ChatImportJob, import_job_id) is not None
        assert (
            db.scalar(
                select(func.count())
                .select_from(RelationshipMessage)
                .where(RelationshipMessage.owner_user_id == owner)
            )
            == 2
        )


def test_confirmation_expiry_staleness_and_target_binding(database_engine):
    owner, _, person_a, person_b, relation_a, relation_b, _ = _scope(database_engine)
    store = _store(database_engine)
    _save(store, owner, person_a, relation_a, "我们计划第一周见面")
    actor = actor_from_verified_identity(owner)
    moment = [datetime.now(UTC)]
    service = _service(database_engine, clock=lambda: moment[0])
    challenge = service.prepare_delete_all(actor, revoke_consent_after_delete=False)
    assert challenge.expected_count == 1 and len(store.list_records(owner)) == 1
    _save(store, owner, person_b, relation_b, "我们计划第二周见面")
    _failure(
        MemoryMutationErrorCode.CONFIRMATION_STALE,
        lambda: service.execute_delete(
            actor, confirmation_id=challenge.confirmation_id, operation_key="stale-key"
        ),
    )
    assert len(store.list_records(owner)) == 2
    person_challenge = service.prepare_delete_person(actor, person_id=person_a)
    assert person_challenge.target_id == person_a and person_challenge.action == "delete_person"
    _failure(
        MemoryMutationErrorCode.MUTATION_CONFLICT,
        lambda: (
            service.execute_delete(
                actor, confirmation_id=person_challenge.confirmation_id, operation_key="same-key"
            ),
            service.execute_delete(
                actor, confirmation_id=challenge.confirmation_id, operation_key="same-key"
            ),
        ),
    )
    expiring = service.prepare_delete_all(actor, revoke_consent_after_delete=False)
    moment[0] += timedelta(minutes=6)
    _failure(
        MemoryMutationErrorCode.CONFIRMATION_EXPIRED,
        lambda: service.execute_delete(
            actor, confirmation_id=expiring.confirmation_id, operation_key="expired-key"
        ),
    )
    assert len(store.list_records(owner)) == 1


def test_concurrent_delete_all_one_receipt(database_engine):
    owner, _, person, _, relation, _, _ = _scope(database_engine)
    store = _store(database_engine)
    _save(store, owner, person, relation, "我们计划第一周见面")
    actor = actor_from_verified_identity(owner)
    service = _service(database_engine)
    first = service.prepare_delete_all(actor, revoke_consent_after_delete=False)
    second = service.prepare_delete_all(actor, revoke_consent_after_delete=False)

    def attempt(index):
        challenge = (first, second)[index]
        try:
            return (
                _service(database_engine)
                .execute_delete(
                    actor,
                    confirmation_id=challenge.confirmation_id,
                    operation_key=f"all-race-{index}",
                )
                .status
            )
        except MemoryMutationError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))
    assert sorted(results) == ["confirmation_stale", "deleted"]
    assert store.list_records(owner) == []
    with Session(database_engine) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(MemoryMutationRow)
                .where(MemoryMutationRow.owner_user_id == owner)
            )
            == 1
        )


def test_delete_and_undo_roll_back_if_receipt_fails(database_engine, monkeypatch):
    owner, _, person, _, relation, _, _ = _scope(database_engine)
    store = _store(database_engine)
    _save(store, owner, person, relation, "我们计划第一周见面")
    actor = actor_from_verified_identity(owner)
    service = _service(database_engine)
    challenge = service.prepare_delete_all(actor, revoke_consent_after_delete=False)
    original = service._add_receipt

    def fail(_db, _row):
        raise RuntimeError("synthetic receipt storage failure")

    monkeypatch.setattr(service, "_add_receipt", fail)
    _failure(
        MemoryMutationErrorCode.PERSISTENCE_FAILURE,
        lambda: service.execute_delete(
            actor, confirmation_id=challenge.confirmation_id, operation_key="rollback-delete"
        ),
    )
    assert len(store.list_records(owner)) == 1
    with Session(database_engine) as db:
        assert db.get(MemoryConfirmationRow, challenge.confirmation_id).consumed_at is None
        assert (
            db.scalar(
                select(func.count())
                .select_from(MemoryMutationRow)
                .where(MemoryMutationRow.owner_user_id == owner)
            )
            == 0
        )
    preview = service.preview_undo(actor)
    _failure(
        MemoryMutationErrorCode.PERSISTENCE_FAILURE,
        lambda: service.undo(
            actor, expected_operation_id=preview.latest_operation_id, operation_key="rollback-undo"
        ),
    )
    assert len(store.list_records(owner)) == 1
    monkeypatch.setattr(service, "_add_receipt", original)
    service.execute_delete(
        actor, confirmation_id=challenge.confirmation_id, operation_key="rollback-delete"
    )
    assert store.list_records(owner) == []


def test_signed_http_flow_and_no_control_llm(database_engine, monkeypatch):
    owner, outsider, person, _, relation, _, _ = _scope(database_engine)
    store = _store(database_engine)
    _save(store, owner, person, relation, "我们计划第一周见面")
    _save(store, owner, person, relation, "我们计划第二周见面")
    app = _app(database_engine)
    provider_calls = []
    monkeypatch.setattr(
        "app.api.dependencies.create_llm_provider", lambda _settings: provider_calls.append(1)
    )
    with TestClient(app) as client:
        h = _headers(owner)
        assert client.get("/api/v1/memory/undo/preview").status_code == 401
        schema = client.get("/openapi.json").json()
        for path in (
            "/api/v1/memory/undo/preview",
            "/api/v1/memory/undo",
            "/api/v1/memory/deletions/one/prepare",
            "/api/v1/memory/deletions/person/prepare",
            "/api/v1/memory/deletions/all/prepare",
            "/api/v1/memory/deletions/{confirmation_id}/execute",
            "/api/v1/memory/mutations/{mutation_id}",
        ):
            for operation in schema["paths"][path].values():
                assert operation["security"] == [{"BearerCredential": []}]
        preview = client.get("/api/v1/memory/undo/preview", headers=h).json()
        body = {
            "expected_operation_id": preview["latest_operation_id"],
            "operation_key": "http-undo",
        }
        undone = client.post("/api/v1/memory/undo", headers=h, json=body)
        replay = client.post("/api/v1/memory/undo", headers=h, json=body)
        assert undone.status_code == replay.status_code == 200
        assert undone.json()["mutation_id"] == replay.json()["mutation_id"]
        assert replay.json()["replayed"]
        assert len(store.list_records(owner)) == 1
        selected = store.list_records(owner)[0]
        prepared = client.post(
            "/api/v1/memory/deletions/one/prepare",
            headers=h,
            json={
                "memory_id": str(selected.id),
                "person_id": str(person),
                "relationship_id": str(relation),
            },
        )
        assert prepared.status_code == 200 and prepared.json()["expected_count"] == 1
        challenge_id = prepared.json()["confirmation_id"]
        assert (
            client.post(
                f"/api/v1/memory/deletions/{challenge_id}/execute",
                headers=_headers(outsider),
                json={"operation_key": "foreign"},
            ).json()["error"]["code"]
            == "confirmation_required"
        )
        assert (
            client.post(
                f"/api/v1/memory/deletions/{challenge_id}/execute",
                headers=h,
                json={"operation_key": "http-delete", "target_id": str(uuid4())},
            ).status_code
            == 422
        )
        deleted = client.post(
            f"/api/v1/memory/deletions/{challenge_id}/execute",
            headers=h,
            json={"operation_key": "http-delete"},
        )
        retried = client.post(
            f"/api/v1/memory/deletions/{challenge_id}/execute",
            headers=h,
            json={"operation_key": "http-delete"},
        )
        assert deleted.status_code == retried.status_code == 200
        assert deleted.json()["mutation_id"] == retried.json()["mutation_id"]
        assert retried.json()["replayed"]
        assert client.get("/api/v1/memories", headers=h).json()["items"] == []
        receipt_id = deleted.json()["mutation_id"]
        assert client.get(f"/api/v1/memory/mutations/{receipt_id}", headers=h).status_code == 200
        assert (
            client.get(f"/api/v1/memory/mutations/{receipt_id}", headers=_headers(outsider)).json()[
                "error"
            ]["code"]
            == "mutation_not_found"
        )
    assert provider_calls == [] and app.state.agent_service is None


def test_agent_http_cannot_bypass_guarded_undo(database_engine, monkeypatch):
    owner, _, person, _, relation, _, conversation = _scope(database_engine)
    store = _store(database_engine)
    _save(store, owner, person, relation, "我们计划第一周见面")
    _save(store, owner, person, relation, "我们计划第二周见面")
    provider = CaptureMock()
    queue_run(provider, first=False, person_id=person)
    queue_run(provider, first=False, person_id=person)
    provider.queue_structured(
        {"risk_level": "high", "safety_route_required": True, "risk_categories": ["self_harm"]}
    )
    monkeypatch.setattr("app.api.dependencies.create_llm_provider", lambda _settings: provider)
    app = _app(database_engine)
    path = f"/api/v1/conversations/{conversation}/agent-runs"
    with TestClient(app) as client:
        for suffix in ("", "/stream"):
            response = client.post(
                path + suffix,
                headers=_headers(owner),
                json={"message": "撤销刚才的记忆", "operation_key": f"guarded-{suffix or 'sync'}"},
            )
            assert response.status_code == 200
            if suffix:
                assert "pending_confirmation" in response.text
            else:
                assert response.json()["memory_status"] == "pending_confirmation"
        safety = client.post(
            path,
            headers=_headers(owner),
            json={"message": "撤销记忆，不然我要伤害自己", "operation_key": "safety-priority"},
        )
        assert safety.status_code == 200
        assert safety.json()["memory_status"] == "none"
    assert len(store.list_records(owner)) == 2
    with Session(database_engine) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(Message)
                .where(Message.conversation_id == conversation)
            )
            == 6
        )
