"""Fault/metadata integrity checks for the opt-in native test fixture only."""

import asyncio
import json
from types import SimpleNamespace

import jwt
import pytest
from native_acceptance_support import NativeAcceptanceWire

from app.core.config import Settings


class Reply:
    def __init__(self):
        self.state = SimpleNamespace(settings=Settings(_env_file=None, auth_jwt_secret="x" * 48))
        self.committed = False

    async def __call__(self, scope, receive, send):
        self.committed = True
        await send(
            {"type": "http.response.start", "status": 200, "headers": [(b"content-length", b"15")]}
        )
        await send({"type": "http.response.body", "body": b"private content", "more_body": False})


def test_verified_labels_use_signature_and_never_export_tokens_secrets_or_body():
    asyncio.run(verified_labels())


async def verified_labels():
    app = Reply()
    settings = app.state.settings
    token = jwt.encode(
        {"sub": "synthetic-a", "iss": settings.auth_jwt_issuer, "aud": settings.auth_jwt_audience},
        "x" * 48,
        algorithm="HS256",
    )
    wire = NativeAcceptanceWire(app, {"synthetic-a": "a"})
    sent = []

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "path": "/api/v1/persons",
        "method": "GET",
        "headers": [(b"authorization", ("Bearer " + token).encode())],
    }
    await wire(scope, None, send)
    assert wire.evidence()["requests"][0]["verified_owner"] == "a"
    scope["headers"] = [(b"authorization", b"Bearer invalid")]
    await wire(scope, None, send)
    assert wire.evidence()["requests"][1]["verified_owner"] == "invalid"
    exported = json.dumps(wire.evidence())
    assert token not in exported and "x" * 48 not in exported
    assert "private content" not in exported
    assert len(sent) == 4  # Observer does not replace the real app's authorization/result.


def test_loss_occurs_after_application_commit_and_is_one_shot():
    asyncio.run(loss_after_commit())


async def loss_after_commit():
    app = Reply()
    wire = NativeAcceptanceWire(app, {})
    wire.arm("agent_drop")
    sent = []

    async def send(message):
        assert app.committed
        sent.append(message)

    scope = {
        "type": "http",
        "path": "/api/v1/conversations/synthetic/agent-runs",
        "method": "POST",
        "headers": [],
    }
    with pytest.raises(RuntimeError, match="Controlled response loss"):
        await wire(scope, None, send)
    assert sent[-1] == {"type": "http.response.body", "body": b"", "more_body": True}
    assert len(wire.evidence()["faults"]) == 1
    await wire(scope, None, send)
    assert sent[-1]["body"] == b"private content"
    assert len(wire.evidence()["faults"]) == 1
