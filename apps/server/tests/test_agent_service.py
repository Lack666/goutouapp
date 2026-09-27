"""Phase 4A service orchestration against disposable PostgreSQL and MockLLM."""

import asyncio
from uuid import uuid4

import pytest
from agent_demo import CaptureMock, queue_run
from sqlalchemy import Engine, select
from sqlalchemy.orm import sessionmaker

from app.agent.contracts import AgentRunStatus, MemoryWriteStatus
from app.agent.dependencies import RuntimeDependencies
from app.agent.memory import InMemoryMemoryStore, MemoryService
from app.agent.runtime import AgentRuntime
from app.db.models import AgentRun, Message
from app.db.repositories import records
from app.db.repositories.memory import SQLAlchemyMemoryStore
from app.llm.mock import MockLLMProvider
from app.services.agent_service import (
    AgentService,
    AgentServiceError,
    AgentServiceErrorCode,
    AuthenticatedActor,
    actor_from_verified_identity,
)


def factory(engine: Engine):
    return sessionmaker(bind=engine, expire_on_commit=False)


def create_scope(make_session, *, relationship=False):
    with make_session() as db, db.begin():
        user = records.create_user(db)
        rel_id = None
        person_id = None
        if relationship:
            person = records.create_person(db, user.id, "Synthetic person")
            rel = records.create_relationship(db, user.id, person.id, "dating", "active")
            rel_id, person_id = rel.id, person.id
        conversation = records.create_conversation(db, user.id, rel_id)
        return user.id, conversation.id, rel_id, person_id


def queue_safety(provider: MockLLMProvider, count=1):
    for _ in range(count):
        provider.queue_structured(
            {"risk_level": "high", "safety_route_required": True, "risk_categories": ["violence"]}
        )


class SpyRuntime:
    def __init__(self, runtime, engine):
        self.runtime = runtime
        self.engine = engine
        self.requests = []
        self.checked_out = []

    async def run(self, request):
        self.requests.append(request)
        self.checked_out.append(self.engine.pool.checkedout())
        return await self.runtime.run(request)


def service_with_mock(engine):
    provider = MockLLMProvider()
    spy = SpyRuntime(AgentRuntime(dependencies=RuntimeDependencies(llm_provider=provider)), engine)
    return AgentService(factory(engine), spy), provider, spy


def persisted(make_session, conversation_id):
    with make_session() as db:
        messages = list(
            db.scalars(select(Message).where(Message.conversation_id == conversation_id))
        )
        runs = list(db.scalars(select(AgentRun).where(AgentRun.conversation_id == conversation_id)))
        return messages, runs


def test_actor_contract_requires_trusted_issuer(database_engine):
    user_id = uuid4()
    with pytest.raises(TypeError):
        AuthenticatedActor(user_id, _issuer=object())
    service, _, spy = service_with_mock(database_engine)
    with pytest.raises(AgentServiceError) as caught:
        asyncio.run(service.execute(actor=user_id, conversation_id=uuid4(), message="hello"))
    assert caught.value.code == AgentServiceErrorCode.INVALID_ACTOR
    assert spy.requests == []
    assert database_engine.pool.checkedout() == 0


def test_success_persists_across_sessions_and_releases_connection(database_engine):
    make_session = factory(database_engine)
    user_id, conversation_id, _, _ = create_scope(make_session)
    service, provider, spy = service_with_mock(database_engine)
    queue_safety(provider)
    result = asyncio.run(
        service.execute(
            actor=actor_from_verified_identity(user_id),
            conversation_id=conversation_id,
            message="有人正在伤害我",
            operation_key="synthetic-client-request-1",
        )
    )
    messages, runs = persisted(make_session, conversation_id)
    assert result.status == AgentRunStatus.COMPLETED
    assert result.assistant_message.content
    assert [(row.role, row.content) for row in messages] == [
        ("user", "有人正在伤害我"),
        ("assistant", result.assistant_message.content),
    ]
    assert len(runs) == 1
    assert runs[0].id == spy.requests[0].run_id == result.run_id
    assert runs[0].status == "completed"
    assert runs[0].started_at and runs[0].completed_at
    assert runs[0].failure_code is None
    assert spy.checked_out == [0]


def test_owner_denial_has_no_side_effect_or_runtime_call(database_engine):
    make_session = factory(database_engine)
    _, conversation_id, _, _ = create_scope(make_session)
    other_user, _, _, _ = create_scope(make_session)
    service, _, spy = service_with_mock(database_engine)
    with pytest.raises(AgentServiceError) as caught:
        asyncio.run(
            service.execute(
                actor=actor_from_verified_identity(other_user),
                conversation_id=conversation_id,
                message="越权请求",
            )
        )
    assert caught.value.code == AgentServiceErrorCode.CONVERSATION_FORBIDDEN
    assert persisted(make_session, conversation_id) == ([], [])
    assert spy.requests == []


def test_missing_and_relationship_scope_rejected_before_write(database_engine):
    make_session = factory(database_engine)
    user, conversation, relationship, person = create_scope(make_session, relationship=True)
    service, _, spy = service_with_mock(database_engine)
    for conversation_id, relation, person_scope, expected in [
        (uuid4(), None, None, AgentServiceErrorCode.CONVERSATION_NOT_FOUND),
        (conversation, uuid4(), None, AgentServiceErrorCode.INVALID_RELATIONSHIP_SCOPE),
        (conversation, relationship, uuid4(), AgentServiceErrorCode.INVALID_RELATIONSHIP_SCOPE),
    ]:
        with pytest.raises(AgentServiceError) as caught:
            asyncio.run(
                service.execute(
                    actor=actor_from_verified_identity(user),
                    conversation_id=conversation_id,
                    relationship_id=relation,
                    person_id=person_scope,
                    message="测试范围",
                )
            )
        assert caught.value.code == expected
    assert person is not None
    assert persisted(make_session, conversation) == ([], [])
    assert spy.requests == []


def test_runtime_failure_retains_user_message_and_failed_run(database_engine):
    make_session = factory(database_engine)
    user, conversation, _, _ = create_scope(make_session)
    service, _, _ = service_with_mock(database_engine)  # Empty Mock queue fails at safety.
    with pytest.raises(AgentServiceError) as caught:
        asyncio.run(
            service.execute(
                actor=actor_from_verified_identity(user),
                conversation_id=conversation,
                message="模型故障测试",
            )
        )
    messages, runs = persisted(make_session, conversation)
    assert caught.value.code == AgentServiceErrorCode.RUNTIME_FAILURE
    assert caught.value.run_id == runs[0].id
    assert [(row.role, row.content) for row in messages] == [("user", "模型故障测试")]
    assert runs[0].status == "failed" and runs[0].failure_code
    assert runs[0].completed_at is not None


def test_history_is_bounded_ordered_scoped_and_excludes_current(database_engine):
    make_session = factory(database_engine)
    user, conversation, _, _ = create_scope(make_session)
    _, other_conversation, _, _ = create_scope(make_session)
    for index in range(24):
        with make_session() as db, db.begin():
            records.create_message(
                db,
                user,
                conversation,
                "user" if index % 2 == 0 else "assistant",
                f"old-{index:02d}",
            )
    with make_session() as db, db.begin():
        records.create_message(db, user, other_conversation, "assistant", "other owner")
    service, provider, spy = service_with_mock(database_engine)
    queue_safety(provider)
    asyncio.run(
        service.execute(
            actor=actor_from_verified_identity(user),
            conversation_id=conversation,
            message="current",
        )
    )
    history = spy.requests[0].recent_messages
    assert [item.content for item in history] == [f"old-{index:02d}" for index in range(4, 24)]
    assert [item.role for item in history] == [
        "user" if index % 2 == 0 else "assistant" for index in range(4, 24)
    ]
    assert "current" not in [item.content for item in history]


def test_db_failure_before_runtime_rolls_back_everything(database_engine, monkeypatch):
    make_session = factory(database_engine)
    user, conversation, _, _ = create_scope(make_session)
    service, _, spy = service_with_mock(database_engine)

    def fail(*args, **kwargs):
        raise RuntimeError("synthetic database failure with private detail")

    monkeypatch.setattr(records, "start_agent_run", fail)
    with pytest.raises(AgentServiceError) as caught:
        asyncio.run(
            service.execute(
                actor=actor_from_verified_identity(user),
                conversation_id=conversation,
                message="hello",
            )
        )
    assert caught.value.code == AgentServiceErrorCode.PERSISTENCE_FAILURE
    assert "private detail" not in str(caught.value)
    assert persisted(make_session, conversation) == ([], [])
    assert spy.requests == []


def test_db_failure_after_answer_rolls_back_assistant_and_recovers_run(
    database_engine, monkeypatch
):
    make_session = factory(database_engine)
    user, conversation, _, _ = create_scope(make_session)
    service, provider, _ = service_with_mock(database_engine)
    queue_safety(provider)
    original = records.create_message

    def fail_assistant(db, user_id, conversation_id, role, content, speaker=None):
        if role == "assistant":
            raise RuntimeError("private database detail")
        return original(db, user_id, conversation_id, role, content, speaker)

    monkeypatch.setattr(records, "create_message", fail_assistant)
    with pytest.raises(AgentServiceError) as caught:
        asyncio.run(
            service.execute(
                actor=actor_from_verified_identity(user),
                conversation_id=conversation,
                message="危险",
            )
        )
    messages, runs = persisted(make_session, conversation)
    assert caught.value.code == AgentServiceErrorCode.PERSISTENCE_FAILURE
    assert caught.value.recovery_status == "failed"
    assert "private" not in str(caught.value)
    assert [row.role for row in messages] == ["user"]
    assert runs[0].status == "failed" and runs[0].failure_code == "persistence_failure"


def test_two_conversations_execute_without_shared_state(database_engine):
    make_session = factory(database_engine)
    user_a, conversation_a, _, _ = create_scope(make_session)
    user_b, conversation_b, _, _ = create_scope(make_session)
    service, provider, spy = service_with_mock(database_engine)
    queue_safety(provider, 2)

    async def execute_both():
        return await asyncio.gather(
            service.execute(
                actor=actor_from_verified_identity(user_a),
                conversation_id=conversation_a,
                message="甲的消息",
            ),
            service.execute(
                actor=actor_from_verified_identity(user_b),
                conversation_id=conversation_b,
                message="乙的消息",
            ),
        )

    a, b = asyncio.run(execute_both())
    assert a.run_id != b.run_id
    assert {request.user_id for request in spy.requests} == {user_a, user_b}
    for conversation_id, run_id, content in [
        (conversation_a, a.run_id, "甲的消息"),
        (conversation_b, b.run_id, "乙的消息"),
    ]:
        messages, runs = persisted(make_session, conversation_id)
        assert len(messages) == 2 and {row.role for row in messages} == {"user", "assistant"}
        assert next(row.content for row in messages if row.role == "user") == content
        assert [run.id for run in runs] == [run_id]


def test_same_user_two_conversations_execute_independently(database_engine):
    make_session = factory(database_engine)
    user, conversation_a, _, _ = create_scope(make_session)
    with make_session() as db, db.begin():
        conversation_b = records.create_conversation(db, user).id
    service, provider, spy = service_with_mock(database_engine)
    queue_safety(provider, 2)

    async def both():
        return await asyncio.gather(
            service.execute(
                actor=actor_from_verified_identity(user),
                conversation_id=conversation_a,
                message="会话甲",
            ),
            service.execute(
                actor=actor_from_verified_identity(user),
                conversation_id=conversation_b,
                message="会话乙",
            ),
        )

    a, b = asyncio.run(both())
    assert a.run_id != b.run_id
    assert all(request.recent_messages == [] for request in spy.requests)
    assert [
        row.content for row in persisted(make_session, conversation_a)[0] if row.role == "user"
    ] == ["会话甲"]
    assert [
        row.content for row in persisted(make_session, conversation_b)[0] if row.role == "user"
    ] == ["会话乙"]


def test_memory_failure_is_warning_and_run_completes(database_engine):
    class BrokenStore(InMemoryMemoryStore):
        def save_record(self, record):
            raise RuntimeError("private storage detail")

    make_session = factory(database_engine)
    user, conversation, relationship, person = create_scope(make_session, relationship=True)
    store = BrokenStore()
    store.bind_relationship(user, relationship, person)
    provider = CaptureMock()
    queue_run(provider, first=True, person_id=person)
    runtime = AgentRuntime(
        dependencies=RuntimeDependencies(llm_provider=provider, memory_service=MemoryService(store))
    )
    service = AgentService(make_session, runtime)
    result = asyncio.run(
        service.execute(
            actor=actor_from_verified_identity(user),
            conversation_id=conversation,
            relationship_id=relationship,
            person_id=person,
            message="关于对象A：我们已确认关系。我明确同意把这项稳定信息存入长期关系档案。",
        )
    )
    messages, runs = persisted(make_session, conversation)
    assert result.memory_status == MemoryWriteStatus.FAILED
    assert result.warnings and "private" not in repr(result)
    assert result.status == AgentRunStatus.COMPLETED
    assert [row.role for row in messages] == ["user", "assistant"]
    assert runs[0].status == "completed"


def test_sql_memory_scope_remains_person_isolated_through_service(database_engine):
    make_session = factory(database_engine)
    user, conversation_a, relationship_a, person_a = create_scope(make_session, relationship=True)
    with make_session() as db, db.begin():
        person_b = records.create_person(db, user, "Synthetic B")
        relationship_b = records.create_relationship(db, user, person_b.id, "dating", "active")
        conversation_b = records.create_conversation(db, user, relationship_b.id)
        relation_b_id, conversation_b_id = relationship_b.id, conversation_b.id
    provider = CaptureMock()
    queue_run(provider, first=True, person_id=person_a)
    queue_run(provider, first=False, person_id=person_b.id)
    queue_run(provider, first=False, person_id=person_a)
    runtime = AgentRuntime(
        dependencies=RuntimeDependencies(
            llm_provider=provider,
            memory_service=MemoryService(SQLAlchemyMemoryStore(make_session)),
        )
    )
    service = AgentService(make_session, runtime)
    first = asyncio.run(
        service.execute(
            actor=actor_from_verified_identity(user),
            conversation_id=conversation_a,
            message="关于对象A：我们已确认关系。我明确同意把这项稳定信息存入长期关系档案。",
        )
    )
    second = asyncio.run(
        service.execute(
            actor=actor_from_verified_identity(user),
            conversation_id=conversation_b_id,
            relationship_id=relation_b_id,
            person_id=person_b.id,
            message="请分析对象B的现状。",
        )
    )
    third = asyncio.run(
        service.execute(
            actor=actor_from_verified_identity(user),
            conversation_id=conversation_a,
            relationship_id=relationship_a,
            person_id=person_a,
            message="请分析对象A的现状。",
        )
    )
    assert first.memory_status == MemoryWriteStatus.SAVED
    assert second.status == third.status == AgentRunStatus.COMPLETED
    assert provider.analysis_payloads[1]["historical_memory"] == []
    assert len(provider.analysis_payloads[2]["historical_memory"]) == 1
