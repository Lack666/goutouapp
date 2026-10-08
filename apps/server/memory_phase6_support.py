"""Synthetic schema-driven Mock LLM shared by the signed HTTP Phase 6 demo/tests."""

import asyncio
import json
import re
from threading import Event
from uuid import uuid4

from agent_demo import CaptureMock, queue_run

from app.llm.mock import MockLLMProvider
from app.schemas.stream_event import NETWORK_EVENT_ADAPTER

FACTS = [f"我们计划第{week}周见面" for week in "一二三四五"]


class Phase6Mock(MockLLMProvider):
    """Choose by schema, so simultaneous runs never share an ordered response queue."""

    def __init__(self):
        super().__init__()
        self.analysis_payloads = []
        self.context_payloads = []
        self.calls = []
        self.candidate_entered = Event()
        self.candidate_release = Event()
        self.block_candidates = False

    async def structured_output(self, messages, schema, **kwargs):
        payload = json.loads(messages[1].content)
        name = schema.__name__
        self.calls.append(name)
        if name == "SafetyResult":
            self.context_payloads.append(payload)
        message = next(
            (
                payload[key]
                for key in (
                    "current_user_message",
                    "current_user_message_data",
                    "current_message_data",
                    "user_request_data",
                )
                if key in payload
            ),
            "",
        )
        found = re.search(r"我们计划第[一二三四五]周见面", message)
        fact = found.group() if found else None
        if name == "SafetyResult" and "想伤害自己" in message:
            return schema.model_validate_json(
                json.dumps(
                    {
                        "risk_level": "high",
                        "risk_categories": ["self_harm"],
                        "safety_route_required": True,
                    }
                )
            )
        if name == "MemoryCandidateBatch":
            if self.block_candidates:
                self.candidate_entered.set()
                if not await asyncio.to_thread(self.candidate_release.wait, 10):
                    raise TimeoutError("Synthetic candidate barrier timed out")
            return schema.model_validate_json(
                json.dumps(
                    {
                        "candidates": [
                            {
                                "subject_id": payload["person_id"],
                                "type": "relationship",
                                "content": fact,
                                "source": "user_explicit",
                                "evidence": "F1",
                            }
                        ]
                        if fact
                        else []
                    }
                )
            )
        if name == "AnalysisResult":
            self.analysis_payloads.append(payload)
            alias = payload["scenario"]["primary"]
        else:
            alias = "memory" if fact else "relationship"
        # Reuse the established, validator-compatible synthetic Agent responses.
        templates = CaptureMock()
        queue_run(templates, first=bool(fact), person_id=uuid4())
        index = {
            "SafetyResult": 0,
            "ScenarioResult": 1,
            "FactExtractionResult": 2,
            "AnalysisResult": 3,
            "ActionPlan": 4,
            "ResponseResult": 5,
        }[name]
        value = json.loads(
            json.dumps(list(templates._structured)[index], ensure_ascii=False)
            .replace("我们已确认关系", fact or "合成背景")
            .replace('"memory"', json.dumps(alias))
        )
        return schema.model_validate_json(json.dumps(value))


def stream_events(response):
    """Validate every wire frame against the public SSE contract."""
    assert response.headers["content-type"].startswith("text/event-stream")
    events = []
    for frame in response.content.split(b"\n\n"):
        if frame:
            name, data = frame.decode().split("\n")
            event = NETWORK_EVENT_ADAPTER.validate_json(data.removeprefix("data: "))
            assert name == f"event: {event.event}"
            events.append(event.model_dump(mode="json"))
    return events


def agent_request(client, headers, conversation, *, fact=None, message=None, stream=False):
    response = client.post(
        f"/api/v1/conversations/{conversation}/agent-runs" + ("/stream" if stream else ""),
        headers=headers,
        json={
            "message": message
            or (f"{fact}。请存入长期记忆。" if fact else "请根据之前的关系背景分析现状。"),
            "operation_key": f"phase6-{uuid4().hex}",
        },
    )
    assert response.status_code in {200, 201}, response.text
    if stream:
        events = stream_events(response)
        assert events[-1]["event"] == "completed", events
        return events[-1]["data"]["memory_status"], events
    value = response.json()
    assert value["status"] == "completed", value
    return value["memory_status"], value
