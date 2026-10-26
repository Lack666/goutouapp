"""Transport-independent streaming lifecycle and privacy checks."""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.agent import AgentFailure, AgentInput, AgentResult
from app.agent.contracts import Fact, MemoryCandidate, MemoryDecision, MemoryRecord
from app.agent.dependencies import RuntimeDependencies
from app.agent.events import (
    AGENT_EVENT_ADAPTER,
    CompletedEvent,
    FailedEvent,
    FinalResponseEvent,
    MemoryStatusEvent,
    ProgressStatus,
    StatusEvent,
)
from app.agent.memory import InMemoryMemoryStore, MemoryService
from app.agent.runtime import AgentRuntime
from app.llm.errors import LLMUnavailableError
from app.llm.mock import MockLLMProvider
from evals.phase3e_analysis import fixture_analysis
from evals.phase3f_action_response import fixture_action, fixture_response


class CountingMock(MockLLMProvider):
    def __init__(self):
        super().__init__()
        self.structured_calls = 0

    async def structured_output(self, messages, schema, **kwargs):
        self.structured_calls += 1
        return await super().structured_output(messages, schema, **kwargs)


def request(message="她问我周末过得怎样，这句话怎么回？", *, relationship_id=None):
    return AgentInput(
        user_id=uuid4(),
        conversation_id=uuid4(),
        relationship_id=relationship_id,
        message=message,
        memory_enabled=relationship_id is not None,
    )


def queue_ordinary(provider, *, scenario="reply", route="ordinary", facts=None, alias=None):
    alias = alias or scenario
    fiu = {"facts": facts or [], "inferences": [], "unknowns": []}
    provider.queue_structured(
        {
            "risk_level": "normal",
            "safety_route_required": False,
            "risk_categories": ["explicit_refusal"] if route == "boundary" else [],
        }
    )
    provider.queue_structured({"primary": scenario, "reason_summary": "Fixture"})
    provider.queue_structured(fiu)
    provider.queue_structured(fixture_analysis(alias=alias, fiu=fiu, route=route))
    action = fixture_action(scenario=scenario, route=route)
    provider.queue_structured(action)
    provider.queue_structured(fixture_response(action))


async def collect(agent, input_value):
    return [event async for event in agent.stream(input_value)]


def test_stream_order_serialization_and_single_graph_execution():
    provider = CountingMock()
    queue_ordinary(provider)
    agent = AgentRuntime(dependencies=RuntimeDependencies(llm_provider=provider))
    events = asyncio.run(collect(agent, request()))
    types = [event.type for event in events]
    assert types[0] == "run_started" and types[-1] == "completed"
    assert types.count("final_response") == 1
    assert types.index("final_response") < types.index("completed")
    assert all(event.run_id == events[0].run_id for event in events)
    assert provider.structured_calls == 6
    assert isinstance(events[-1], CompletedEvent)
    assert isinstance(events[-1].result, AgentResult)
    with pytest.raises(ValidationError):
        CompletedEvent(run_id=uuid4(), result=events[-1].result)
    assert events[-1].result.final_answer == next(
        event.answer for event in events if isinstance(event, FinalResponseEvent)
    )
    for event in events:
        assert AGENT_EVENT_ADAPTER.validate_json(event.model_dump_json()) == event
        assert "node_started" not in event.model_dump_json()
    assert [event.status for event in events if isinstance(event, StatusEvent)] == [
        ProgressStatus.PREPARING,
        ProgressStatus.CHECKING_SAFETY,
        ProgressStatus.UNDERSTANDING_REQUEST,
        ProgressStatus.LOADING_CONTEXT,
        ProgressStatus.ANALYZING,
        ProgressStatus.PLANNING,
        ProgressStatus.COMPOSING,
    ]


def test_run_stream_parity_and_boundary_policy():
    input_value = request("她已经明确拒绝我，我该怎么回复？")
    run_provider, stream_provider = CountingMock(), CountingMock()
    queue_ordinary(run_provider, scenario="reply", route="boundary", alias="consent")
    queue_ordinary(stream_provider, scenario="reply", route="boundary", alias="consent")
    run_result = asyncio.run(
        AgentRuntime(dependencies=RuntimeDependencies(llm_provider=run_provider)).run(input_value)
    )
    events = asyncio.run(
        collect(
            AgentRuntime(dependencies=RuntimeDependencies(llm_provider=stream_provider)),
            input_value,
        )
    )
    stream_result = events[-1].result
    assert isinstance(run_result, AgentResult) and isinstance(stream_result, AgentResult)
    assert run_result.model_dump(exclude={"run_id"}) == stream_result.model_dump(exclude={"run_id"})
    assert stream_result.action.contact_policy == "stop_contact"
    assert "停止联系" in stream_result.final_answer
    # Safety/Scenario/FIU/Analysis call the provider; the validated no-contact
    # Action/Response policy is now local in both execution modes.
    assert run_provider.structured_calls == stream_provider.structured_calls == 4


def test_high_risk_stream_skips_ordinary_statuses_and_nodes():
    provider = CountingMock()
    provider.queue_structured(
        {
            "risk_level": "high",
            "safety_route_required": True,
            "risk_categories": ["violence"],
        }
    )
    events = asyncio.run(
        collect(
            AgentRuntime(dependencies=RuntimeDependencies(llm_provider=provider)),
            request("现在有人正在伤害我"),
        )
    )
    assert [event.type for event in events][-2:] == ["final_response", "completed"]
    assert provider.structured_calls == 1
    assert events[-1].result.analysis is None and events[-1].result.action is None
    statuses = {event.status for event in events if isinstance(event, StatusEvent)}
    assert ProgressStatus.PREPARING_SAFETY_RESPONSE in statuses
    assert statuses.isdisjoint(
        {
            ProgressStatus.ANALYZING,
            ProgressStatus.PLANNING,
            ProgressStatus.COMPOSING,
            ProgressStatus.UPDATING_MEMORY,
        }
    )


def test_failure_is_correlated_and_does_not_leak_provider_secret():
    provider = MockLLMProvider()
    provider.queue_error("structured_output", LLMUnavailableError())
    events = asyncio.run(
        collect(AgentRuntime(dependencies=RuntimeDependencies(llm_provider=provider)), request())
    )
    assert events[0].type == "run_started" and events[-1].type == "failed"
    assert all(event.run_id == events[0].run_id for event in events)
    assert isinstance(events[-1], FailedEvent)
    assert isinstance(events[-1].failure, AgentFailure)
    assert "private" not in events[-1].model_dump_json()
    assert not any(isinstance(event, FinalResponseEvent) for event in events)
    invalid = asyncio.run(
        collect(
            AgentRuntime(dependencies=RuntimeDependencies(llm_provider=MockLLMProvider())), None
        )
    )
    assert [event.type for event in invalid] == ["run_started", "failed"]


def test_memory_failure_after_answer_emits_memory_status_then_completes():
    class BrokenStore(InMemoryMemoryStore):
        def save_record(self, record):
            raise RuntimeError("postgresql://private-password@host")

    input_value = request("我们已确认关系，我明确同意存入长期关系档案。", relationship_id=uuid4())
    store = BrokenStore()
    person = uuid4()
    store.bind_relationship(input_value.user_id, input_value.relationship_id, person)
    provider = CountingMock()
    queue_ordinary(
        provider,
        scenario="memory",
        facts=[
            {
                "statement": "我们已确认关系",
                "source": "user_explicit",
            }
        ],
    )
    provider.queue_structured(
        {
            "candidates": [
                {
                    "subject_id": str(person),
                    "type": "relationship",
                    "content": "我们已确认关系",
                    "source": "user_explicit",
                    "evidence": "F1",
                }
            ]
        }
    )
    events = asyncio.run(
        collect(
            AgentRuntime(
                dependencies=RuntimeDependencies(
                    llm_provider=provider, memory_service=MemoryService(store)
                )
            ),
            input_value,
        )
    )
    assert [event.type for event in events][-3:] == [
        "final_response",
        "memory_status",
        "completed",
    ]
    assert isinstance(events[-2], MemoryStatusEvent)
    assert events[-2].receipt.status.value == "failed"
    assert events[-1].result.final_answer
    assert "private-password" not in "".join(event.model_dump_json() for event in events)
    assert provider.structured_calls == 7


def test_pending_destructive_intent_has_typed_memory_event():
    input_value = request("请删除全部长期记忆", relationship_id=uuid4())
    store = InMemoryMemoryStore()
    store.bind_relationship(input_value.user_id, input_value.relationship_id, uuid4())
    provider = MockLLMProvider()
    queue_ordinary(provider, scenario="memory")
    events = asyncio.run(
        collect(
            AgentRuntime(
                dependencies=RuntimeDependencies(
                    llm_provider=provider, memory_service=MemoryService(store)
                )
            ),
            input_value,
        )
    )
    memory_event = next(event for event in events if isinstance(event, MemoryStatusEvent))
    assert memory_event.receipt.status.value == "pending_confirmation"
    assert memory_event.decision.value == "delete_all"


def test_undo_intent_streams_actual_reversal_while_memory_is_paused():
    input_value = request("请撤销刚才的记忆", relationship_id=uuid4())
    person = uuid4()
    store = InMemoryMemoryStore()
    store.bind_relationship(input_value.user_id, input_value.relationship_id, person)
    service = MemoryService(store)
    service.grant_consent(input_value.user_id, confirmed=True)
    saved = service.persist_candidates(
        user_id=input_value.user_id,
        relationship_id=input_value.relationship_id,
        run_id=uuid4(),
        candidates=[
            MemoryCandidate(
                subject_id=person,
                type="relationship",
                content="我们已确认关系",
                source="user_explicit",
                evidence="F1",
            )
        ],
        facts=[Fact(statement="我们已确认关系", source="user_explicit")],
        message="请记住：我们已确认关系",
        explicit_consent=False,
    )
    assert saved.saved_count == 1
    service.apply_control(input_value.user_id, MemoryDecision.PAUSE)
    provider = MockLLMProvider()
    queue_ordinary(provider, scenario="memory")
    events = asyncio.run(
        collect(
            AgentRuntime(
                dependencies=RuntimeDependencies(llm_provider=provider, memory_service=service)
            ),
            input_value,
        )
    )
    memory_event = next(event for event in events if isinstance(event, MemoryStatusEvent))
    assert memory_event.decision == MemoryDecision.UNDO
    assert memory_event.receipt.status.value == "undone"
    assert [event.type for event in events][-3:] == [
        "final_response",
        "memory_status",
        "completed",
    ]
    assert service.list_for_user(input_value.user_id) == []


def test_stream_never_serializes_loaded_historical_memory_or_reference_text():
    input_value = request("请分析目前的关系", relationship_id=uuid4())
    person = uuid4()
    store = InMemoryMemoryStore()
    store.bind_relationship(input_value.user_id, input_value.relationship_id, person)
    service = MemoryService(store)
    service.grant_consent(input_value.user_id, confirmed=True)
    now = datetime.now(UTC)
    store.save_record(
        MemoryRecord(
            id=uuid4(),
            owner_user_id=input_value.user_id,
            subject_id=person,
            person_id=person,
            relationship_id=input_value.relationship_id,
            type="relationship",
            content="我们有一个只属于历史记录的约定",
            source="user_explicit",
            evidence=f"{uuid4()}: F1",
            created_at=now,
            updated_at=now,
        )
    )
    provider = MockLLMProvider()
    queue_ordinary(provider, scenario="relationship")
    events = asyncio.run(
        collect(
            AgentRuntime(
                dependencies=RuntimeDependencies(llm_provider=provider, memory_service=service)
            ),
            input_value,
        )
    )
    serialized = "".join(event.model_dump_json() for event in events)
    assert events[-1].type == "completed"
    assert "我们有一个只属于历史记录的约定" not in serialized
    assert "reference_knowledge" not in serialized
    assert "HISTORICAL MEMORY" not in serialized


def test_consumer_cancellation_closes_underlying_graph_without_extra_calls():
    class BlockingMock(MockLLMProvider):
        def __init__(self):
            super().__init__()
            self.started = asyncio.Event()
            self.cancelled = False
            self.calls = 0

        async def structured_output(self, messages, schema, **kwargs):
            self.calls += 1
            self.started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.cancelled = True
                raise

    async def exercise():
        provider = BlockingMock()
        agent = AgentRuntime(dependencies=RuntimeDependencies(llm_provider=provider))

        async def consume():
            async for _ in agent.stream(request()):
                pass

        task = asyncio.create_task(consume())
        await asyncio.wait_for(provider.started.wait(), 3)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert provider.cancelled and provider.calls == 1

    asyncio.run(exercise())


def test_explicit_generator_close_before_safety_has_no_model_or_memory_side_effect():
    async def exercise():
        provider = CountingMock()
        queue_ordinary(provider)
        input_value = request("请分析现状", relationship_id=uuid4())
        store = InMemoryMemoryStore()
        store.bind_relationship(input_value.user_id, input_value.relationship_id, uuid4())
        agent = AgentRuntime(
            dependencies=RuntimeDependencies(
                llm_provider=provider, memory_service=MemoryService(store)
            )
        )
        iterator = agent.stream(input_value)
        assert (await anext(iterator)).type == "run_started"
        assert (await anext(iterator)).status == ProgressStatus.PREPARING
        assert (await anext(iterator)).status == ProgressStatus.CHECKING_SAFETY
        await iterator.aclose()
        assert provider.structured_calls == 0
        assert store.records == {} and store.operations == {}

    asyncio.run(exercise())
