"""Phase 9B: signed credentials and production services against migrated PostgreSQL."""

import base64
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from test_agent_rest import SECRET, headers, safety_provider, settings, signed_token
from test_import_api import bind, finalize, scope, upload
from test_phase6_e2e import flow as phase6_flow

from app.main import create_app

flow = phase6_flow


@pytest.fixture
def security_api(database_engine, tmp_path, monkeypatch):
    provider = safety_provider()
    provider.queue_structured(
        {"risk_level": "high", "safety_route_required": True, "risk_categories": ["violence"]}
    )
    monkeypatch.setattr("app.api.dependencies.create_llm_provider", lambda _settings: provider)
    app = create_app(settings(database_engine, chat_import_artifact_root=tmp_path / "artifacts"))
    assert not app.dependency_overrides
    with TestClient(app, raise_server_exceptions=False) as client:
        yield app, client, scope(database_engine), scope(database_engine)


@pytest.mark.parametrize(
    "case",
    [
        "missing",
        "signature",
        "expired",
        "future",
        "malformed",
        "algorithm",
        "unsigned",
        "unknown_user",
        "subject",
        "subject_type",
        "issuer",
        "audience",
        "tampered",
        "exp_infinity",
        "nbf_infinity",
        "iat_infinity",
        "required_exp",
        "required_sub",
    ],
)
def test_jwt_negative_contract(security_api, case):
    _app, client, owner, _foreign = security_api
    token = signed_token(owner[0])
    now = datetime.now(UTC)
    changes = {
        "expired": {"exp": now - timedelta(seconds=2)},
        "future": {"nbf": now + timedelta(hours=1)},
        "unknown_user": {"sub": str(uuid4())},
        "subject": {"sub": "invalid"},
        "subject_type": {"sub": 123},
        "issuer": {"iss": "foreign"},
        "audience": {"aud": "foreign"},
        "exp_infinity": {"exp": float("inf")},
        "nbf_infinity": {"nbf": float("inf")},
        "iat_infinity": {"iat": float("inf")},
        "required_exp": {"exp": None},
        "required_sub": {"sub": None},
    }
    if case in changes:
        token = signed_token(owner[0], **changes[case])
    elif case == "signature":
        token = signed_token(owner[0], key="untrusted-synthetic-key-longer-than-thirty-two-bytes")
    elif case in {"algorithm", "unsigned"}:
        claims = jwt.decode(token, options={"verify_signature": False})
        token = jwt.encode(
            claims,
            SECRET if case == "algorithm" else "",
            algorithm="HS384" if case == "algorithm" else "none",
        )
    elif case == "malformed":
        token = "invalid.credential"
    elif case == "tampered":
        parts = token.split(".")
        parts[1] = (
            base64.urlsafe_b64encode(json.dumps({"sub": str(owner[0])}).encode())
            .decode()
            .rstrip("=")
        )
        token = ".".join(parts)
    response = client.get(
        "/api/v1/persons", headers={} if case == "missing" else {"Authorization": "Bearer " + token}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credential"
    assert token not in response.text


def test_every_sensitive_operation_requires_real_bearer(security_api):
    app, client, _a, _b = security_api
    count = 0
    for path, operations in app.openapi()["paths"].items():
        for method, operation in operations.items():
            if not operation.get("security"):
                continue
            count += 1
            target = path
            for parameter in operation.get("parameters", []):
                if parameter["in"] == "path":
                    target = target.replace("{" + parameter["name"] + "}", str(uuid4()))
            kwargs = (
                {
                    "data": {"source_timezone": "Asia/Shanghai"},
                    "files": {"file": ("synthetic.md", b"synthetic")},
                }
                if path == "/api/v1/chat-imports"
                else {"json": {}}
            )
            response = client.request(method, target, **kwargs)
            assert response.status_code == 401
    assert count == 33


@pytest.mark.parametrize("environment", ["test", "staging", "production"])
def test_development_issuer_refuses_other_environments(monkeypatch, environment):
    import dev_auth_cli

    from app.core.config import Settings

    monkeypatch.setattr(
        dev_auth_cli, "Settings", lambda: Settings(app_env=environment, _env_file=None)
    )
    monkeypatch.setattr("sys.argv", ["dev_auth_cli.py", "bootstrap"])
    with pytest.raises(RuntimeError, match="only with APP_ENV=development"):
        dev_auth_cli.main()


@pytest.mark.parametrize("value", [0, {}, [], None, True])
def test_malformed_memory_cursor_is_controlled(security_api, value):
    _app, client, owner, _foreign = security_api
    cursor = base64.urlsafe_b64encode(
        json.dumps([datetime.now(UTC).isoformat(), value]).encode()
    ).decode()
    response = client.get("/api/v1/memories", params={"cursor": cursor}, headers=headers(owner[0]))
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_scope"


def test_cross_owner_resources_and_same_uuid_reservations(security_api):
    _app, client, a, b = security_api
    for domain, resource_id in (
        ("persons", a[1]),
        ("relationships", a[2]),
        ("conversations", a[3]),
    ):
        foreign = client.get(f"/api/v1/{domain}/{resource_id}", headers=headers(b[0]))
        missing = client.get(f"/api/v1/{domain}/{uuid4()}", headers=headers(b[0]))
        assert foreign.status_code == missing.status_code == 404
        assert foreign.json() == missing.json()
        result = client.get(f"/api/v1/{domain}", headers=headers(b[0]))
        assert str(resource_id) not in result.text
        assert "user_id" not in result.text
    bodies = [
        ("persons", {"id": str(a[1]), "display_name": "Synthetic"}),
        (
            "relationships",
            {
                "id": str(a[2]),
                "person_id": str(b[1]),
                "relationship_type": "dating",
                "status": "active",
            },
        ),
        ("conversations", {"id": str(a[3]), "relationship_id": str(b[2])}),
        (
            "relationships",
            {
                "id": str(uuid4()),
                "person_id": str(a[1]),
                "relationship_type": "dating",
                "status": "active",
            },
        ),
        ("conversations", {"id": str(uuid4()), "relationship_id": str(a[2])}),
    ]
    for domain, body in bodies:
        assert client.post(f"/api/v1/{domain}", headers=headers(b[0]), json=body).status_code == 404


@pytest.mark.parametrize("stream_first", [False, True])
def test_agent_rest_sse_cross_owner_and_cross_transport_replay(security_api, stream_first):
    _app, client, a, b = security_api
    path = f"/api/v1/conversations/{a[3]}/agent-runs"
    body = {
        "message": "Synthetic safety request",
        "operation_key": uuid4().hex,
        "expected_relationship_id": str(a[2]),
    }
    first = client.post(
        path + ("/stream" if stream_first else ""), json=body, headers=headers(a[0])
    )
    assert first.status_code == 200
    for suffix in ("", "/stream"):
        forbidden = client.post(path + suffix, json=body, headers=headers(b[0]))
        assert forbidden.status_code == 404
        assert "run_id" not in forbidden.text and "text/event-stream" not in forbidden.headers.get(
            "content-type", ""
        )
    assert (
        client.get(f"/api/v1/conversations/{a[3]}/messages", headers=headers(b[0])).status_code
        == 404
    )
    replay = client.post(
        path + ("" if stream_first else "/stream"), json=body, headers=headers(a[0])
    )
    assert replay.status_code == 200
    # The same key is a namespace entry, never an authentication credential.
    body["expected_relationship_id"] = str(b[2])
    assert (
        client.post(
            f"/api/v1/conversations/{b[3]}/agent-runs", json=body, headers=headers(b[0])
        ).status_code
        == 200
    )


def test_import_binding_lifecycle_and_history_owner(security_api):
    _app, client, a, b = security_api
    job = upload(client, a[0]).json()
    own = upload(client, b[0]).json()
    path = f"/api/v1/chat-imports/{job['id']}"
    for method, suffix, body in [
        ("GET", "", None),
        ("POST", "/ready", None),
        ("POST", "/cancel", None),
        ("POST", "/finalize", {"expected_revision": job["binding_revision"]}),
        (
            "PUT",
            "/relationship",
            {"relationship_id": str(b[2]), "expected_revision": job["binding_revision"]},
        ),
        (
            "PUT",
            "/speakers",
            {
                "raw_speaker_label": "A",
                "binding_kind": "person",
                "person_id": str(b[1]),
                "expected_revision": job["binding_revision"],
            },
        ),
    ]:
        assert (
            client.request(method, path + suffix, headers=headers(b[0]), json=body).status_code
            == 404
        )
    for suffix, body in [
        (
            "speakers",
            {
                "raw_speaker_label": "A",
                "binding_kind": "person",
                "person_id": str(a[1]),
                "expected_revision": own["binding_revision"],
            },
        ),
        (
            "relationship",
            {"relationship_id": str(a[2]), "expected_revision": own["binding_revision"]},
        ),
    ]:
        assert (
            client.put(
                f"/api/v1/chat-imports/{own['id']}/{suffix}", json=body, headers=headers(b[0])
            ).status_code
            == 404
        )
    ready = bind(client, a[0], job, a[1], a[2])
    stale = client.post(path + "/finalize", headers=headers(a[0]), json={"expected_revision": 0})
    assert stale.status_code == 409
    assert finalize(client, a[0], ready).status_code == 200
    first = client.get(
        f"/api/v1/relationships/{a[2]}/messages?limit=1", headers=headers(a[0])
    ).json()
    assert first["next_cursor"]
    response = client.get(
        f"/api/v1/relationships/{b[2]}/messages",
        params={"cursor": first["next_cursor"]},
        headers=headers(b[0]),
    )
    assert response.status_code == 400
    assert (
        client.get(f"/api/v1/relationships/{a[2]}/messages", headers=headers(b[0])).status_code
        == 404
    )
    assert client.post(path + "/cancel", headers=headers(a[0])).status_code == 409
    assert (
        client.post(f"/api/v1/chat-imports/{own['id']}/cancel", headers=headers(b[0])).status_code
        == 200
    )
    assert (
        client.post(f"/api/v1/chat-imports/{own['id']}/ready", headers=headers(b[0])).status_code
        == 409
    )


def test_memory_confirmation_receipt_and_undo_owner(flow):
    a = flow
    b = scope(flow.engine)
    from test_phase6_e2e import headers as memory_headers

    foreign = memory_headers(b[0])
    a.grant()
    item = a.save()
    baseline = a.inspect()
    assert a.call("GET", "/memory/control", auth=foreign)["consent_enabled"] is False
    assert a.call("GET", "/memories", auth=foreign)["items"] == []
    foreign_preview = a.call("GET", "/memory/undo/preview", auth=foreign)
    assert foreign_preview["available"] is False
    assert foreign_preview["latest_operation_id"] is None
    for target in (item["id"], str(uuid4())):
        a.call("GET", f"/memories/{target}", auth=foreign, status=404)
    preview = a.call("GET", "/memory/undo/preview")
    a.call(
        "POST",
        "/memory/undo",
        {"expected_operation_id": preview["latest_operation_id"], "operation_key": uuid4().hex},
        auth=foreign,
        status=409,
    )
    a.call(
        "POST",
        "/memory/deletions/person/prepare",
        {"person_id": str(a.person)},
        auth=foreign,
        status=404,
    )
    a.call(
        "POST",
        "/memory/deletions/one/prepare",
        {"memory_id": item["id"], "person_id": str(b[1]), "relationship_id": str(b[2])},
        status=404,
    )
    a.call(
        "POST", "/memory/deletions/one/prepare", {"memory_id": item["id"]}, auth=foreign, status=404
    )
    for kind, body in (
        ("one", {"memory_id": item["id"]}),
        ("person", {"person_id": str(a.person)}),
        ("all", {"revoke_consent_after_delete": False}),
    ):
        challenge = a.prepare(kind, body)
        a.execute(challenge, auth=foreign, status=409)
        assert a.inspect() == baseline
    challenge = a.prepare("all", {"revoke_consent_after_delete": False})
    key = uuid4().hex
    receipt = a.execute(challenge, key=key)
    a.call("GET", f"/memory/mutations/{receipt['mutation_id']}", auth=foreign, status=404)
    a.execute(challenge, key=key, auth=foreign, status=409)
    # Foreign same-key traffic cannot alter A's immutable successful receipt.
    replay = a.execute(challenge, key=key)
    assert replay["mutation_id"] == receipt["mutation_id"] and replay["replayed"] is True
    a.execute(challenge, key=uuid4().hex, status=409)


def test_memory_cursor_binds_owner_person_and_relationship(flow):
    from test_phase6_e2e import headers as memory_headers

    flow.grant()
    flow.save(0)
    flow.save(1)
    b = scope(flow.engine)
    cursor = flow.client.get("/api/v1/memories", headers=flow.headers, params={"limit": 1}).json()[
        "next_cursor"
    ]
    assert cursor
    for auth, params in (
        (memory_headers(b[0]), {}),
        (flow.headers, {"person_id": str(flow.person)}),
        (flow.headers, {"relationship_id": str(flow.relationship)}),
    ):
        response = flow.client.get(
            "/api/v1/memories", headers=auth, params={"cursor": cursor, **params}
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "invalid_scope"
    response = flow.client.get("/api/v1/memories", headers=flow.headers, params={"cursor": cursor})
    assert response.status_code == 200 and len(response.json()["items"]) == 1
