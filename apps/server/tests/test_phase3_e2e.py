"""Eight representative full-pipeline standalone Phase 3 acceptance cases."""

import asyncio
from uuid import uuid4

from agent_demo import CaptureMock, queue_run

from app.agent import AgentInput, AgentResult
from app.agent.contracts import MemoryWriteStatus, Route
from app.agent.dependencies import RuntimeDependencies
from app.agent.events import CompletedEvent, FinalResponseEvent, MemoryStatusEvent
from app.agent.memory import InMemoryMemoryStore, MemoryService
from app.agent.runtime import AgentRuntime
from app.llm.mock import MockLLMProvider
from evals.phase3e_analysis import fixture_analysis
from evals.phase3f_action_response import fixture_action, fixture_response
from evals.phase3g_memory import run_memory_case


class RecordingMock(MockLLMProvider):
    def __init__(self):
        super().__init__()
        self.schemas = []

    async def structured_output(self, messages, schema, **kwargs):
        self.schemas.append(schema.__name__)
        return await super().structured_output(messages, schema, **kwargs)


def request(message, *, user_id=None, relationship_id=None):
    return AgentInput(
        user_id=user_id or uuid4(),
        conversation_id=uuid4(),
        relationship_id=relationship_id,
        memory_enabled=relationship_id is not None,
        message=message,
    )


def queue_full(provider, *, scenario="reply", route="ordinary", alias=None):
    alias = alias or scenario
    provider.queue_structured(
        {
            "risk_level": "normal",
            "safety_route_required": False,
            "risk_categories": ["explicit_refusal"] if route == "boundary" else [],
        }
    )
    provider.queue_structured({"primary": scenario, "reason_summary": "E2E fixture"})
    fiu = {"facts": [], "inferences": [], "unknowns": []}
    provider.queue_structured(fiu)
    provider.queue_structured(fixture_analysis(alias=alias, fiu=fiu, route=route))
    action = fixture_action(scenario=scenario, route=route)
    provider.queue_structured(action)
    provider.queue_structured(fixture_response(action))


def memory_setup():
    user, person, relationship = uuid4(), uuid4(), uuid4()
    store = InMemoryMemoryStore()
    store.bind_relationship(user, relationship, person)
    service = MemoryService(store)
    provider = CaptureMock()
    queue_run(provider, first=True, person_id=person)
    runtime = AgentRuntime(
        dependencies=RuntimeDependencies(llm_provider=provider, memory_service=service)
    )
    return runtime, provider, service, store, user, person, relationship


def test_e2e_01_ordinary_reply_traverses_full_pipeline():
    provider = RecordingMock()
    queue_full(provider)
    result = asyncio.run(
        AgentRuntime(dependencies=RuntimeDependencies(llm_provider=provider)).run(
            request("她问我周末过得怎样，这句话怎么回？")
        )
    )
    assert isinstance(result, AgentResult)
    assert provider.schemas == [
        "SafetyResult",
        "ScenarioResult",
        "FactExtractionResult",
        "AnalysisResult",
        "ActionPlan",
        "ResponseResult",
    ]
    assert result.route == Route.ORDINARY
    assert "reply" in result.knowledge.selected_references
    assert result.analysis is not None and result.action.contact_policy == "reply"
    assert result.final_answer.startswith(result.action.message_suggestion)


def test_e2e_02_explicit_refusal_respects_boundary():
    provider = RecordingMock()
    queue_full(provider, route="boundary", alias="consent")
    result = asyncio.run(
        AgentRuntime(dependencies=RuntimeDependencies(llm_provider=provider)).run(
            request("她明确拒绝了我，我该怎么回复？")
        )
    )
    assert isinstance(result, AgentResult)
    assert result.route == Route.BOUNDARY
    assert result.action.contact_policy == "stop_contact"
    assert "停止联系" in result.final_answer
    assert result.action.message_suggestion is None


def test_e2e_03_high_risk_uses_safety_reference_only():
    provider = RecordingMock()
    provider.queue_structured(
        {
            "risk_level": "high",
            "safety_route_required": True,
            "risk_categories": ["violence"],
        }
    )
    result = asyncio.run(
        AgentRuntime(dependencies=RuntimeDependencies(llm_provider=provider)).run(
            request("有人正在伤害我")
        )
    )
    assert isinstance(result, AgentResult)
    assert provider.schemas == ["SafetyResult"]
    assert result.route == Route.SAFETY
    assert "safety" in result.knowledge.selected_references
    assert result.analysis is None and result.action is None


def test_e2e_04_explicit_consent_saved_then_loaded_in_new_conversation():
    runtime, provider, service, store, user, person, relationship = memory_setup()
    queue_run(provider, first=False, person_id=person)

    async def first_stream():
        return [
            event
            async for event in runtime.stream(
                request(
                    "关于对象A：我们已确认关系。我明确同意把这项稳定信息存入长期关系档案。",
                    user_id=user,
                    relationship_id=relationship,
                )
            )
        ]

    first_events = asyncio.run(first_stream())
    first = first_events[-1].result
    second = asyncio.run(
        runtime.run(
            request(
                "请根据之前的关系背景分析现状。",
                user_id=user,
                relationship_id=relationship,
            )
        )
    )
    assert isinstance(first, AgentResult) and isinstance(second, AgentResult)
    assert first.memory_receipt.status == MemoryWriteStatus.SAVED
    assert [event.type for event in first_events][-3:] == [
        "final_response",
        "memory_status",
        "completed",
    ]
    assert len(service.list_for_user(user)) == 1
    assert len(store.operations[user]) == 1
    assert first.run_id != second.run_id
    assert len(provider.analysis_payloads[1]["historical_memory"]) == 1
    assert second.evidence.facts == []


def test_e2e_05_same_fact_without_consent_writes_zero():
    result, service, user, _person = run_memory_case("pair_d2")
    assert result.memory_receipt.saved_count == 0
    assert service.list_for_user(user) == []


def test_e2e_06_memory_failure_keeps_stream_answer():
    class BrokenStore(InMemoryMemoryStore):
        def save_record(self, record):
            raise RuntimeError("postgresql://private-secret@host")

    runtime, provider, _service, _store, user, person, relationship = memory_setup()
    broken = BrokenStore()
    broken.bind_relationship(user, relationship, person)
    runtime = AgentRuntime(
        dependencies=RuntimeDependencies(
            llm_provider=provider, memory_service=MemoryService(broken)
        )
    )

    async def collect():
        return [
            event
            async for event in runtime.stream(
                request(
                    "关于对象A：我们已确认关系。我明确同意把这项稳定信息存入长期关系档案。",
                    user_id=user,
                    relationship_id=relationship,
                )
            )
        ]

    events = asyncio.run(collect())
    assert [event.type for event in events][-3:] == [
        "final_response",
        "memory_status",
        "completed",
    ]
    assert isinstance(events[-3], FinalResponseEvent)
    assert isinstance(events[-2], MemoryStatusEvent)
    assert events[-2].receipt.status == MemoryWriteStatus.FAILED
    assert isinstance(events[-1], CompletedEvent)
    assert events[-1].result.final_answer == events[-3].answer
    assert "private-secret" not in "".join(event.model_dump_json() for event in events)


def test_e2e_07_person_b_never_receives_person_a_history():
    runtime, provider, service, store, user, _person_a, relation_a = memory_setup()
    person_b, relation_b = uuid4(), uuid4()
    store.bind_relationship(user, relation_b, person_b)
    queue_run(provider, first=False, person_id=person_b)
    first = asyncio.run(
        runtime.run(
            request(
                "关于对象A：我们已确认关系。我明确同意把这项稳定信息存入长期关系档案。",
                user_id=user,
                relationship_id=relation_a,
            )
        )
    )
    second = asyncio.run(
        runtime.run(
            request(
                "请分析对象B的现状。",
                user_id=user,
                relationship_id=relation_b,
            )
        )
    )
    assert isinstance(first, AgentResult) and isinstance(second, AgentResult)
    assert len(service.list_for_user(user)) == 1
    assert provider.analysis_payloads[1]["historical_memory"] == []


def test_e2e_08_run_stream_final_result_parity():
    input_value = request("她问我周末过得怎样，这句话怎么回？")
    run_provider, stream_provider = RecordingMock(), RecordingMock()
    queue_full(run_provider)
    queue_full(stream_provider)
    run_result = asyncio.run(
        AgentRuntime(dependencies=RuntimeDependencies(llm_provider=run_provider)).run(input_value)
    )

    async def collect():
        agent = AgentRuntime(dependencies=RuntimeDependencies(llm_provider=stream_provider))
        return [event async for event in agent.stream(input_value)]

    events = asyncio.run(collect())
    stream_result = events[-1].result
    assert isinstance(run_result, AgentResult) and isinstance(stream_result, AgentResult)
    assert run_result.model_dump(exclude={"run_id"}) == stream_result.model_dump(exclude={"run_id"})
    assert run_provider.schemas == stream_provider.schemas
