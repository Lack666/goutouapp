"""HTTP auth and schema contract checks without an external database."""

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from app.agent.contracts import AgentRunStatus, MemoryWriteStatus
from app.core.config import Settings
from app.main import create_app
from app.services.agent_service import (
    AgentServiceError,
    AgentServiceErrorCode,
    AgentServiceResult,
    AssistantMessageResult,
)

SECRET = "phase4b-contract-secret-with-more-than-32-bytes"


class RecordingService:
    def __init__(self):
        self.calls = []

    async def execute(self, **kwargs):
        self.calls.append(kwargs)
        return AgentServiceResult(
            run_id=uuid4(),
            conversation_id=kwargs["conversation_id"],
            assistant_message=AssistantMessageResult(uuid4(), "assistant", "Safe synthetic answer"),
            status=AgentRunStatus.COMPLETED,
            memory_status=MemoryWriteStatus.NONE,
            warnings=(),
        )


def setup():
    app = create_app(
        Settings(
            app_env="test",
            auth_jwt_secret=SECRET,
            auth_jwt_issuer="contract-issuer",
            auth_jwt_audience="contract-api",
            _env_file=None,
        )
    )
    service = RecordingService()
    app.state.agent_service = service
    return app, service


def token(user_id, **overrides):
    claims = {
        "sub": str(user_id),
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        "iss": "contract-issuer",
        "aud": "contract-api",
    }
    claims.update(overrides)
    return jwt.encode(claims, SECRET, algorithm="HS256")


def test_signed_token_yields_actor_and_thin_service_call():
    app, service = setup()
    user_id, conversation_id, relationship_id = uuid4(), uuid4(), uuid4()
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/conversations/{conversation_id}/agent-runs",
            json={
                "message": "Synthetic input",
                "expected_relationship_id": str(relationship_id),
                "operation_key": "request-1",
            },
            headers={"Authorization": f"Bearer {token(user_id)}"},
        )
    assert response.status_code == 200
    assert response.json()["assistant_message"]["content"] == "Safe synthetic answer"
    assert len(service.calls) == 1
    call = service.calls[0]
    assert call["actor"].user_id == user_id
    assert call["conversation_id"] == conversation_id
    assert call["relationship_id"] == relationship_id
    assert call["operation_key"] == "request-1"
    assert call["message"] == "Synthetic input"
    assert "user_id" not in call and "person_id" not in call


def test_invalid_or_expired_credentials_never_call_service():
    app, service = setup()
    conversation_id = uuid4()
    user_id = uuid4()
    credentials = [
        None,
        "Bearer malformed",
        "Bearer " + token(user_id, exp=datetime.now(UTC) - timedelta(seconds=1)),
        "Bearer "
        + jwt.encode(
            {
                "sub": str(user_id),
                "exp": datetime.now(UTC) + timedelta(minutes=5),
                "iss": "contract-issuer",
                "aud": "contract-api",
            },
            "different-secret-with-more-than-32-bytes",
            algorithm="HS256",
        ),
    ]
    with TestClient(app) as client:
        for credential in credentials:
            response = client.post(
                f"/api/v1/conversations/{conversation_id}/agent-runs",
                json={"message": "Private message"},
                headers={"Authorization": credential} if credential else {},
            )
            assert response.status_code == 401
            assert response.headers["WWW-Authenticate"] == "Bearer"
            assert response.json()["error"]["code"] == "invalid_credential"
    assert service.calls == []


def test_authentication_precedes_invalid_body_validation():
    app, service = setup()
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/conversations/{uuid4()}/agent-runs",
            json={"message": "", "user_id": str(uuid4())},
        )
    assert response.status_code == 401
    assert service.calls == []


def test_duplicate_authorization_headers_are_rejected():
    app, service = setup()
    user_id = uuid4()
    value = f"Bearer {token(user_id)}"
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/conversations/{uuid4()}/agent-runs",
            json={"message": "Synthetic input"},
            headers=[("Authorization", value), ("Authorization", value)],
        )
    assert response.status_code == 401
    assert service.calls == []


def test_extra_user_id_blank_and_bad_uuid_are_uniform_errors():
    app, service = setup()
    user_id, conversation_id = uuid4(), uuid4()
    cases = [
        (str(conversation_id), {"message": "ok", "user_id": str(uuid4())}),
        (str(conversation_id), {"message": " \n"}),
        (str(conversation_id), {}),
        (str(conversation_id), {"message": "x" * 20001}),
        (str(conversation_id), {"message": "bad\x00text"}),
        (str(conversation_id), {"message": "ok", "person_id": str(uuid4())}),
        ("invalid-uuid", {"message": "ok"}),
    ]
    with TestClient(app) as client:
        for path_id, body in cases:
            response = client.post(
                f"/api/v1/conversations/{path_id}/agent-runs",
                json=body,
                headers={"Authorization": f"Bearer {token(user_id)}"},
            )
            assert response.status_code == 422
            assert response.json()["error"]["code"] == "validation_error"
    assert service.calls == []


def test_invalid_unicode_is_uniform_validation_error():
    app, service = setup()
    user_id, conversation_id = uuid4(), uuid4()
    body = json.dumps({"message": "bad" + chr(0xD800)}, ensure_ascii=True).encode("utf-8")
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/conversations/{conversation_id}/agent-runs",
            content=body,
            headers={
                "Authorization": f"Bearer {token(user_id)}",
                "Content-Type": "application/json",
            },
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert service.calls == []


def test_openapi_bearer_and_public_liveness():
    app, _service = setup()
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()
        assert client.get("/health").status_code == 200
        assert client.get("/api/v1/status").status_code == 200
    operation = schema["paths"]["/api/v1/conversations/{conversation_id}/agent-runs"]["post"]
    assert operation["security"] == [{"BearerCredential": []}]
    assert schema["components"]["securitySchemes"]["BearerCredential"]["type"] == "http"
    assert "security" not in schema["paths"]["/health"]["get"]


def test_missing_auth_configuration_keeps_health_but_closes_business_endpoint():
    app = create_app(Settings(app_env="test", auth_jwt_secret=None, _env_file=None))
    app.state.agent_service = RecordingService()
    user_id, conversation_id = uuid4(), uuid4()
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        response = client.post(
            f"/api/v1/conversations/{conversation_id}/agent-runs",
            json={"message": "Synthetic input"},
            headers={"Authorization": f"Bearer {token(user_id)}"},
        )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "authentication_unavailable"
    assert app.state.agent_service.calls == []


def test_typed_service_errors_use_uniform_envelope_and_preserve_recovery_id():
    class ErrorService:
        def __init__(self, error):
            self.error = error

        async def execute(self, **_kwargs):
            raise self.error

    app, _service = setup()
    user_id, conversation_id, run_id = uuid4(), uuid4(), uuid4()
    cases = [
        (AgentServiceError(AgentServiceErrorCode.CONVERSATION_FORBIDDEN), 404, "not_found"),
        (
            AgentServiceError(AgentServiceErrorCode.RUNTIME_FAILURE, run_id=run_id),
            502,
            "agent_failure",
        ),
        (
            AgentServiceError(
                AgentServiceErrorCode.PERSISTENCE_FAILURE,
                run_id=run_id,
                recovery_status="running_unknown",
            ),
            503,
            "persistence_failure",
        ),
    ]
    with TestClient(app) as client:
        for error, expected_status, expected_code in cases:
            app.state.agent_service = ErrorService(error)
            response = client.post(
                f"/api/v1/conversations/{conversation_id}/agent-runs",
                json={"message": "Private input"},
                headers={"Authorization": f"Bearer {token(user_id)}"},
            )
            assert response.status_code == expected_status
            assert response.json()["error"]["code"] == expected_code
            assert "Private input" not in response.text
            if error.recovery_status:
                assert response.json()["error"]["run_id"] == str(run_id)
                assert response.json()["error"]["recovery_status"] == "running_unknown"
