"""Versioned SSE framing and authentication preflight without PostgreSQL."""

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from app.agent.contracts import MemoryWriteStatus
from app.agent.events import ProgressStatus
from app.core.config import Settings
from app.main import create_app
from app.schemas.stream_event import NETWORK_EVENT_ADAPTER, encode_sse, to_network_event
from app.services.agent_stream import (
    AgentServiceStream,
    ServiceCompleted,
    ServiceFailed,
    ServiceFinalResponse,
    ServiceMemoryStatus,
    ServiceRunStarted,
    ServiceStatus,
)

SECRET = "phase4c-synthetic-secret-with-more-than-32-bytes"


def token(user_id, *, key=SECRET, **changes):
    claims = {
        "sub": str(user_id),
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        "iss": "stream-issuer",
        "aud": "stream-api",
    }
    claims.update(changes)
    return jwt.encode(claims, key, algorithm="HS256")


def make_app():
    return create_app(
        Settings(
            app_env="test",
            database_url=None,  # Keep the stub adapter independent of env DB URLs.
            auth_jwt_secret=SECRET,
            auth_jwt_issuer="stream-issuer",
            auth_jwt_audience="stream-api",
            _env_file=None,
        )
    )


def parse_frames(chunks: list[bytes]):
    raw = b"".join(chunks)
    frames = []
    for frame in raw.split(b"\n\n"):
        if not frame:
            continue
        lines = frame.decode("utf-8").split("\n")
        assert len(lines) == 2
        assert lines[0].startswith("event: ") and lines[1].startswith("data: ")
        payload = NETWORK_EVENT_ADAPTER.validate_json(lines[1][6:])
        assert payload.event == lines[0][7:]
        frames.append(payload)
    return frames


def test_every_public_event_round_trips_with_utf8_and_arbitrary_byte_chunks():
    run_id, assistant_id = uuid4(), uuid4()
    answer = ("你好 😀\n下一行。" * 900) + "结束"
    values = [
        ServiceRunStarted(run_id),
        ServiceStatus(run_id, ProgressStatus.PREPARING),
        ServiceFinalResponse(run_id, assistant_id, answer),
        ServiceMemoryStatus(run_id, MemoryWriteStatus.FAILED),
        ServiceMemoryStatus(run_id, MemoryWriteStatus.PENDING_CONFIRMATION),
        ServiceCompleted(run_id, assistant_id, MemoryWriteStatus.FAILED),
        ServiceFailed(run_id, "persistence_failure", "running_unknown"),
    ]
    encoded = [encode_sse(to_network_event(event)) for event in values]
    assert all(frame.endswith(b"\n\n") for frame in encoded)
    # Split inside UTF-8 code points and SSE fields; the client reassembles bytes.
    wire = b"".join(encoded)
    parsed = parse_frames([wire[index : index + 7] for index in range(0, len(wire), 7)])
    assert [item.event for item in parsed] == [
        "run_started",
        "status",
        "final_response",
        "memory_status",
        "pending_confirmation",
        "completed",
        "failed",
    ]
    assert all(item.schema_version == "1" and item.run_id == run_id for item in parsed)
    assert parsed[2].data.answer == answer
    assert parsed[5].data.assistant_message_id == assistant_id
    assert "\n" not in encoded[2].decode("utf-8").split("data: ", 1)[1].split("\n", 1)[0]
    assert json.loads(encoded[2].decode("utf-8").split("data: ", 1)[1])["event"] == (
        "final_response"
    )


def test_auth_fails_before_stream_service_is_called_and_openapi_marks_bearer():
    class NeverCalled:
        def __init__(self):
            self.calls = 0

        async def stream(self, **_kwargs):
            self.calls += 1
            raise AssertionError("invalid auth called service")

    app = make_app()
    service = NeverCalled()
    app.state.agent_service = service
    path = f"/api/v1/conversations/{uuid4()}/agent-runs/stream"
    subject = uuid4()
    invalid = [
        {},
        {"Authorization": "Bearer malformed"},
        {"Authorization": f"Bearer {token(subject, key='wrong-signing-key-over-32-bytes-long')}"},
        {"Authorization": f"Bearer {token(subject, exp=datetime.now(UTC) - timedelta(seconds=1))}"},
    ]
    with TestClient(app) as client:
        for headers in invalid:
            response = client.post(path, json={"message": "private input"}, headers=headers)
            assert response.status_code == 401
            assert response.headers["WWW-Authenticate"] == "Bearer"
            assert response.json()["error"]["code"] == "invalid_credential"
        schema = client.get("/openapi.json").json()
    assert service.calls == 0
    operation = schema["paths"]["/api/v1/conversations/{conversation_id}/agent-runs/stream"]["post"]
    assert operation["security"] == [{"BearerCredential": []}]
    assert "text/event-stream" in operation["responses"]["200"]["content"]


def test_stream_response_is_sse_and_has_single_run_id_with_stub_service():
    class StubService:
        def __init__(self):
            self.calls = 0
            self.cancel_calls = 0

        async def stream(self, **kwargs):
            self.calls += 1
            run_id, assistant_id = uuid4(), uuid4()
            assert kwargs["actor"].user_id == subject

            async def events():
                yield ServiceRunStarted(run_id)
                yield ServiceStatus(run_id, ProgressStatus.PREPARING)
                yield ServiceFinalResponse(run_id, assistant_id, "你好 😀")
                yield ServiceCompleted(run_id, assistant_id, MemoryWriteStatus.NONE)

            def cancel():
                self.cancel_calls += 1

            return AgentServiceStream(run_id, events(), cancel)

    subject = uuid4()
    app = make_app()
    service = StubService()
    app.state.agent_service = service
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/conversations/{uuid4()}/agent-runs/stream",
            json={"message": "hi"},
            headers={"Authorization": f"Bearer {token(subject)}"},
        )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    frames = parse_frames([response.content])
    assert [item.event for item in frames] == [
        "run_started",
        "status",
        "final_response",
        "completed",
    ]
    assert len({event.run_id for event in frames}) == 1
    assert service.calls == service.cancel_calls == 1
