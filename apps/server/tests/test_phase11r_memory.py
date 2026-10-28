"""Phase 11R: real PostgreSQL canaries for current-request Memory authorization."""

from uuid import uuid4

import pytest
from agent_demo import CaptureMock, queue_run
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_memory_control import _app, _headers

from app.agent import AgentInput, initial_state
from app.agent.contracts import (
    Fact,
    MemoryCandidate,
    MemoryDecision,
    MemoryIntent,
    MemoryWriteStatus,
    Route,
)
from app.agent.dependencies import RuntimeDependencies
from app.agent.memory import MemoryService, asks_to_save, explicit_save_consent
from app.agent.memory_nodes import load_memory, persist_memory, resolve_memory_intent
from app.db.models import MemoryControlRow, MemoryOperationRow, MemoryRecordRow
from app.db.repositories import records
from app.db.repositories.memory import SQLAlchemyMemoryStore
from app.llm.mock import MockLLMProvider


def scope(engine):
    with Session(engine) as db:
        owner, outsider = records.create_user(db), records.create_user(db)
        people = [records.create_person(db, owner.id, name) for name in ("R11 A", "R11 B")]
        relations = [
            records.create_relationship(db, owner.id, person.id, "classmate", "active")
            for person in people
        ]
        conversation = records.create_conversation(db, owner.id, relations[0].id)
        ids = (
            owner.id,
            outsider.id,
            [p.id for p in people],
            [r.id for r in relations],
            conversation.id,
        )
        db.commit()
    service = MemoryService(SQLAlchemyMemoryStore(lambda: Session(engine)))
    return service, ids


def current_state(service, ids, message):
    owner, _, _, relations, conversation = ids
    state = initial_state(
        AgentInput(
            user_id=owner,
            conversation_id=conversation,
            relationship_id=relations[0],
            message=message,
            memory_enabled=True,
        )
    )
    state["route"] = Route.ORDINARY
    deps = RuntimeDependencies(llm_provider=MockLLMProvider(), memory_service=service)
    state.update(load_memory(state, deps))
    state.update(resolve_memory_intent(state, deps))
    return state, deps


def snapshot(engine):
    with Session(engine) as db:
        return {
            model.__name__: sorted(
                (
                    tuple(str(getattr(row, col.name)) for col in model.__table__.columns)
                    for row in db.scalars(select(model))
                ),
            )
            for model in (MemoryControlRow, MemoryRecordRow, MemoryOperationRow)
        }


@pytest.mark.parametrize("consent", [False, True])
@pytest.mark.parametrize(
    "message",
    [
        "请解释暂停记忆的含义，不要实际执行。",
        "请解释“我明确同意保存长期记忆”这句话，不要保存。",
        "我没有同意保存长期记忆。",
        "我不是不同意保存长期记忆，先解释流程。",
        "不要删除编号 mem_a_17。",
        "讨论一下恢复长期记忆有什么后果。",
        "引用：我撤回长期记忆同意。",
        "我明确同意保存长期关系档案：我们已确认关系。不要实际保存。",
        "假如我说我明确同意保存长期记忆，会发生什么？",
    ],
)
def test_sa13_sa14_discussion_negation_quote_has_zero_sql_effect(database_engine, consent, message):
    service, ids = scope(database_engine)
    if consent:
        service.grant_consent(ids[0], confirmed=True)
    state, deps = current_state(service, ids, message)
    assert state["memory_intent"].decision == MemoryDecision.NO_WRITE
    before = snapshot(database_engine)
    # An injected/stale intent still cannot authorize the persistence node.
    state["memory_intent"] = MemoryIntent(decision=MemoryDecision.RESUME)
    persist_memory(state, deps)
    assert snapshot(database_engine) == before


@pytest.mark.parametrize(
    "message",
    [
        "我明确同意保存精简关系档案：我们已确认关系。",
        "关于对象A：我们已确认关系。我明确同意把这项稳定信息存入长期关系档案。",
        "我明确同意保存长期关系档案。记住：我们已确认关系。",
    ],
)
def test_sa13_explicit_save_is_grounded_and_durable(database_engine, message):
    service, ids = scope(database_engine)
    assert asks_to_save(message) and explicit_save_consent(message)
    state, deps = current_state(service, ids, message)
    assert state["memory_intent"].decision == MemoryDecision.ALLOW_CANDIDATE
    state["facts"] = [Fact(statement="我们已确认关系", source="user_explicit")]
    state["memory_candidates"] = [
        MemoryCandidate(
            subject_id=ids[2][0],
            type="relationship",
            content="我们已确认关系",
            source="user_explicit",
            evidence="F1",
        )
    ]
    update = persist_memory(state, deps)
    assert update["memory_receipt"].status == MemoryWriteStatus.SAVED
    fresh = MemoryService(SQLAlchemyMemoryStore(lambda: Session(database_engine)))
    assert fresh.control(ids[0]).consent_enabled
    assert len(fresh.list_for_user(ids[0])) == 1
    assert fresh.load_for_context(ids[0], ids[3][1], enabled=True) == []
    assert fresh.load_for_context(ids[1], ids[3][0], enabled=True) == []
    record = fresh.list_for_user(ids[0])[0]
    assert not fresh.delete_one(ids[1], record.id, person_id=ids[2][0])
    assert not fresh.delete_one(ids[0], record.id, person_id=ids[2][1])
    assert len(fresh.list_for_user(ids[0])) == 1


def test_sa14_direct_controls_and_deletion_requires_trusted_confirmation(database_engine):
    service, ids = scope(database_engine)
    service.grant_consent(ids[0], confirmed=True)
    for message, expected in [("暂停长期记忆", True), ("恢复长期记忆", False)]:
        state, deps = current_state(service, ids, message)
        persist_memory(state, deps)
        assert service.control(ids[0]).paused is expected
    state, deps = current_state(service, ids, "我撤回长期记忆同意")
    persist_memory(state, deps)
    assert not service.control(ids[0]).consent_enabled
    state, deps = current_state(service, ids, "请删除全部长期记忆")
    before = snapshot(database_engine)
    update = persist_memory(state, deps)
    assert update["memory_receipt"].status == MemoryWriteStatus.PENDING_CONFIRMATION
    assert snapshot(database_engine) == before


def test_sa18_disabled_safety_and_foreign_scope_cannot_mutate(database_engine):
    service, ids = scope(database_engine)
    message = "我明确同意保存长期关系档案。记住：我们已确认关系。"
    for mode in ("disabled", "safety", "foreign"):
        state, deps = current_state(service, ids, message)
        if mode == "disabled":
            state["memory_enabled"] = False
        elif mode == "safety":
            state["route"] = Route.SAFETY
        else:
            state["user_id"] = ids[1]
        before = snapshot(database_engine)
        persist_memory(state, deps)
        assert snapshot(database_engine) == before


def test_sa18_invalid_candidate_scope_cannot_grant_consent(database_engine):
    service, ids = scope(database_engine)
    before = snapshot(database_engine)
    result = service.persist_candidates(
        user_id=ids[1],
        relationship_id=ids[3][0],
        run_id=uuid4(),
        candidates=[
            MemoryCandidate(
                subject_id=ids[2][0],
                type="relationship",
                content="我们已确认关系",
                source="user_explicit",
                evidence="F1",
            )
        ],
        facts=[Fact(statement="我们已确认关系", source="user_explicit")],
        message="我明确同意记住：我们已确认关系",
        explicit_consent=True,
    )
    assert result.status == MemoryWriteStatus.REJECTED_VALIDATION
    assert snapshot(database_engine) == before


@pytest.mark.parametrize(
    "message,consent",
    [
        ("请解释暂停记忆的含义，不要实际执行。", True),
        ("请解释“我明确同意保存长期记忆”这句话，不要保存。", False),
    ],
)
def test_baseline_p0_requests_are_safe_through_signed_agent_http(
    database_engine, monkeypatch, message, consent
):
    service, ids = scope(database_engine)
    if consent:
        service.grant_consent(ids[0], confirmed=True)
    provider = CaptureMock()
    queue_run(provider, first=False, person_id=ids[2][0])
    monkeypatch.setattr("app.api.dependencies.create_llm_provider", lambda _settings: provider)
    path = f"/api/v1/conversations/{ids[4]}/agent-runs"
    body = {"message": message, "operation_key": "r11-auth-canary"}
    before = snapshot(database_engine)
    with TestClient(_app(database_engine)) as client:
        assert client.post(path, json=body).status_code == 401
        assert client.post(path, json=body, headers=_headers(ids[1])).status_code == 404
        response = client.post(path, json=body, headers=_headers(ids[0]))
        assert response.status_code == 200
    assert snapshot(database_engine) == before
