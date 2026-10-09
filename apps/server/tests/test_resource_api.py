"""Actual signed JWT -> public API -> service -> committed PostgreSQL, without auth overrides."""

import base64
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Event
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from memory_phase6_support import Phase6Mock
from resource_demo_support import ResourceFlow, create_owners, headers, settings
from sqlalchemy import event, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import AgentRun, Conversation, MemoryRecordRow, Message, Person, Relationship
from app.db.repositories import records
from app.main import create_app
from app.schemas.resources import PageRequest, PersonCreateRequest
from app.services.resources import ResourceError, ResourceErrorCode, ResourceService

MODELS = {"persons": Person, "relationships": Relationship, "conversations": Conversation}


@pytest.fixture
def flow(database_engine, monkeypatch, tmp_path):
    provider = Phase6Mock()
    monkeypatch.setattr("app.api.dependencies.create_llm_provider", lambda _settings: provider)
    app = create_app(settings(database_engine, chat_import_artifact_root=tmp_path / "artifacts"))
    owner, foreign = create_owners(database_engine)
    assert not app.dependency_overrides
    with TestClient(app) as client:
        value = ResourceFlow(client, owner)
        value.engine, value.foreign, value.app, value.provider = (
            database_engine,
            foreign,
            app,
            provider,
        )
        yield value


def row_count(flow, domain, resource_id):
    with Session(flow.engine) as db:
        model = MODELS[domain]
        return db.scalar(
            select(func.count()).select_from(model).where(model.id == UUID(resource_id))
        )


@pytest.mark.parametrize("domain", MODELS)
def test_create_list_detail_lost_response_retry_across_app_restart(flow, domain):
    body = flow.body(domain)
    first = flow.call("POST", f"/{domain}", body, status=201)
    with TestClient(create_app(settings(flow.engine))) as other_client:
        replay = ResourceFlow(other_client, flow.owner).call("POST", f"/{domain}", body, status=201)
    assert first == replay
    assert row_count(flow, domain, body["id"]) == 1
    assert flow.call("GET", f"/{domain}/{body['id']}") == first
    assert first in flow.call("GET", f"/{domain}")["items"]
    assert not {"user_id", "owner_user_id", "profile", "evidence"} & first.keys()


@pytest.mark.parametrize("domain", MODELS)
def test_changed_creation_payload_is_conflict_and_keeps_original(flow, domain):
    body = flow.body(domain)
    first = flow.call("POST", f"/{domain}", body, status=201)
    changed = dict(body)
    if domain == "persons":
        changed["display_name"] = "Synthetic changed"
    elif domain == "relationships":
        changed["person_id"] = flow.person()["id"]
        changed["status"] = "explicit_changed"
    else:
        changed["relationship_id"] = None
    conflict = flow.call("POST", f"/{domain}", changed, status=409)
    assert conflict["error"]["code"] == "resource_creation_conflict"
    assert flow.call("GET", f"/{domain}/{body['id']}") == first
    assert row_count(flow, domain, body["id"]) == 1


def test_explicit_unknown_relationship_and_generic_conversation_remain_valid(flow):
    relationship = flow.relationship()
    assert relationship["relationship_type"] == relationship["status"] == "unknown"
    generic = flow.conversation()
    assert generic["relationship_id"] is None
    for omitted in ("relationship_type", "status"):
        body = flow.body("relationships")
        del body[omitted]
        flow.call("POST", "/relationships", body, status=422)


@pytest.mark.parametrize("domain", MODELS)
def test_owner_neutral_details_and_lists(flow, domain):
    own = flow.call("POST", f"/{domain}", flow.body(domain), status=201)
    foreign_auth = headers(flow.foreign)
    denied = flow.call("GET", f"/{domain}/{own['id']}", status=404, auth=foreign_auth)
    missing = flow.call("GET", f"/{domain}/{uuid4()}", status=404, auth=foreign_auth)
    assert denied == missing == {"error": {"code": "not_found", "message": "Resource not found"}}
    assert flow.call("GET", f"/{domain}", auth=foreign_auth) == {"items": [], "next_cursor": None}


@pytest.mark.parametrize(
    "domain,parent", [("relationships", "person_id"), ("conversations", "relationship_id")]
)
def test_foreign_and_missing_parent_bindings_are_identical_and_atomic(flow, domain, parent):
    body = flow.body(domain)
    foreign_flow = ResourceFlow(flow.client, flow.foreign)
    target = foreign_flow.person() if parent == "person_id" else foreign_flow.relationship()
    body[parent] = target["id"]
    denied = flow.call("POST", f"/{domain}", body, status=404)
    body[parent] = str(uuid4())
    missing = flow.call("POST", f"/{domain}", body, status=404)
    assert denied == missing
    assert row_count(flow, domain, body["id"]) == 0


@pytest.mark.parametrize("domain", MODELS)
@pytest.mark.parametrize("field", ["owner_user_id", "user_id", "profile", "operation_key"])
def test_creation_rejects_owner_override_and_unsupported_fields(flow, domain, field):
    body = flow.body(domain)
    body[field] = str(flow.foreign)
    flow.call("POST", f"/{domain}", body, status=422)
    assert row_count(flow, domain, body["id"]) == 0


@pytest.mark.parametrize("bad_id", ["demo-a", str(UUID(int=0)), str(UUID(int=1))])
def test_creation_requires_stable_uuid_v4(flow, bad_id):
    flow.call("POST", "/persons", {"id": bad_id, "display_name": "Synthetic"}, status=422)
    flow.call("POST", "/persons", {"display_name": "Synthetic"}, status=422)


@pytest.mark.parametrize("label", ["   ", "a\u0000b", "a\nb", "\ud800", "a" * 121, 123])
def test_invalid_labels_are_masked_without_database_writes(flow, label):
    body = {"id": str(uuid4()), "display_name": label}
    response = flow.client.post(
        "/api/v1/persons",
        content=json.dumps(body),
        headers={**flow.headers, "Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json() == {"error": {"code": "validation_error", "message": "Invalid request"}}
    assert row_count(flow, "persons", body["id"]) == 0


def test_label_canonicalization_is_deterministic_on_retry(flow):
    body = {"id": str(uuid4()), "display_name": "  e\u0301 🥰  "}
    first = flow.call("POST", "/persons", body, status=201)
    assert first["display_name"] == "é 🥰"
    body["display_name"] = "é 🥰"
    assert flow.call("POST", "/persons", body, status=201) == first


AUTH_ROUTES = [
    (method, path)
    for domain in MODELS
    for method, path in (
        ("POST", f"/{domain}"),
        ("GET", f"/{domain}"),
        ("GET", f"/{domain}/{{id}}"),
    )
] + [("GET", "/conversations/{id}/messages")]


@pytest.mark.parametrize("method,path", AUTH_ROUTES)
@pytest.mark.parametrize("credential", ["missing", "unknown_subject"])
def test_every_new_route_requires_signed_existing_user(flow, method, path, credential):
    auth = {} if credential == "missing" else headers(uuid4())
    body = flow.body(path.strip("/")) if method == "POST" else None
    response = flow.call(method, path.replace("{id}", str(uuid4())), body, status=401, auth=auth)
    assert response["error"]["code"] == "invalid_credential"
    assert flow.provider.calls == []


@pytest.mark.parametrize(
    "claim,value", [("iss", "foreign"), ("aud", "foreign"), ("sub", "demo-a"), ("exp", 1)]
)
def test_invalid_claims_never_reach_resource_creation(flow, claim, value):
    body = flow.body("persons")
    flow.call("POST", "/persons", body, status=401, auth=headers(flow.owner, **{claim: value}))
    assert row_count(flow, "persons", body["id"]) == 0


@pytest.mark.parametrize("domain", MODELS)
def test_eight_concurrent_duplicate_creates_have_one_committed_row(flow, domain):
    body = flow.body(domain)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(
            pool.map(lambda _: flow.call("POST", f"/{domain}", body, status=201), range(8))
        )
    assert all(result == results[0] for result in results)
    assert row_count(flow, domain, body["id"]) == 1


@pytest.mark.parametrize("domain", [*MODELS, "messages"])
def test_equal_timestamps_exhaust_stable_bounded_pages_without_loss(flow, domain):
    timestamp = datetime(2023, 1, 1, tzinfo=UTC)
    ids = [uuid4() for _ in range(61)]
    person, relationship, conversation = flow.person(), flow.relationship(), flow.conversation()
    path = f"/{domain}" if domain != "messages" else f"/conversations/{conversation['id']}/messages"
    with Session(flow.engine) as db, db.begin():
        for index, resource_id in enumerate(ids):
            common = {"id": resource_id, "created_at": timestamp, "updated_at": timestamp}
            if domain == "persons":
                row = Person(user_id=flow.owner, display_name="Same synthetic label", **common)
            elif domain == "relationships":
                row = Relationship(
                    user_id=flow.owner,
                    person_id=UUID(person["id"]),
                    relationship_type="unknown",
                    status="unknown",
                    **common,
                )
            elif domain == "conversations":
                row = Conversation(
                    user_id=flow.owner, relationship_id=UUID(relationship["id"]), **common
                )
            else:
                row = Message(
                    conversation_id=UUID(conversation["id"]),
                    role="user" if index % 2 else "assistant",
                    content="Same synthetic text",
                    speaker="internal speaker marker",
                    **common,
                )
            db.add(row)
        if domain == "messages":
            db.add(
                Message(
                    conversation_id=UUID(conversation["id"]),
                    role="tool",
                    content="private tool content",
                    created_at=timestamp,
                )
            )
    items = flow.pages(path, limit=7)
    assert [UUID(row["id"]) for row in items[:61]] == sorted(ids)
    assert items == flow.pages(path, limit=9)
    if domain == "messages":
        assert len(items) == 61  # Not the Agent's internal 20-message limit.
        assert {row["role"] for row in items} == {"user", "assistant"}
        assert all("speaker" not in row for row in items)


@pytest.mark.parametrize(
    "query",
    [
        {"limit": 0},
        {"limit": 101},
        {"cursor": ""},
        {"cursor": "x" * 513},
        {"owner_user_id": "demo-a"},
        {"offset": 30},
    ],
)
def test_pagination_rejects_unbounded_or_unsupported_queries(flow, query):
    for domain in MODELS:
        flow.call("GET", f"/{domain}", status=422, params=query)
    conversation = flow.conversation()
    flow.call("GET", f"/conversations/{conversation['id']}/messages", status=422, params=query)


def test_invalid_cursor_and_owner_domain_conversation_reuse_are_rejected(flow):
    flow.person()
    flow.person()
    cursor = flow.call("GET", "/persons", params={"limit": 1})["next_cursor"]
    assert cursor
    for domain, auth in (
        ("persons", headers(flow.foreign)),
        ("relationships", flow.headers),
        ("conversations", flow.headers),
    ):
        flow.call("GET", f"/{domain}", auth=auth, status=422, params={"cursor": cursor})
    malformed = [
        "?",
        "e30",
        base64.urlsafe_b64encode(
            json.dumps([1, "wrong-context", "naive", "bad-id"]).encode()
        ).decode(),
    ]
    for value in malformed:
        result = flow.call("GET", "/persons", status=422, params={"cursor": value})
        assert result["error"]["code"] == "invalid_cursor"
    decoded = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
    for timestamp, resource_id in ((None, 123), ("2023-01-01", "bad"), ({}, [])):
        value = base64.urlsafe_b64encode(
            json.dumps([1, decoded[1], timestamp, resource_id]).encode()
        ).decode()
        flow.call("GET", "/persons", status=422, params={"cursor": value})
    first, second = flow.conversation(), flow.conversation()
    with Session(flow.engine) as db, db.begin():
        for _ in range(3):
            records.create_message(db, flow.owner, UUID(first["id"]), "user", "synthetic")
    cursor = flow.call("GET", f"/conversations/{first['id']}/messages", params={"limit": 1})[
        "next_cursor"
    ]
    flow.call(
        "GET", f"/conversations/{second['id']}/messages", status=422, params={"cursor": cursor}
    )
    denied = flow.call(
        "GET",
        f"/conversations/{first['id']}/messages",
        status=404,
        auth=headers(flow.foreign),
        params={"cursor": cursor},
    )
    missing = flow.call(
        "GET", f"/conversations/{uuid4()}/messages", status=404, auth=headers(flow.foreign)
    )
    assert denied == missing


def test_new_api_conversation_runs_existing_agent_and_reads_persisted_public_history(flow):
    relationship = flow.relationship()
    conversation = flow.conversation(relationship)
    path = f"/conversations/{conversation['id']}"
    denied = flow.call(
        "POST",
        path + "/agent-runs",
        {"message": "Synthetic input", "expected_relationship_id": str(uuid4())},
        status=404,
    )
    assert denied["error"]["code"] == "not_found"
    assert flow.provider.calls == []
    body = {
        "message": "请分析合成背景",
        "expected_relationship_id": relationship["id"],
        "operation_key": uuid4().hex,
    }
    result = flow.call("POST", path + "/agent-runs", body)
    assert flow.call("POST", path + "/agent-runs", body) == result
    history = flow.pages(path + "/messages", limit=1)
    assert [row["role"] for row in history] == ["user", "assistant"]
    assert history[1]["id"] == result["assistant_message"]["id"]
    assert history[1]["content"] == result["assistant_message"]["content"]
    with Session(flow.engine) as db:
        assert db.get(AgentRun, UUID(result["run_id"])).status == "completed"
        assert db.get(Message, UUID(history[1]["id"])).content == history[1]["content"]
        assert (
            db.scalar(
                select(func.count())
                .select_from(MemoryRecordRow)
                .where(MemoryRecordRow.owner_user_id == flow.owner)
            )
            == 0
        )
    generic = flow.conversation()
    assert (
        flow.call(
            "POST", f"/conversations/{generic['id']}/agent-runs", {"message": "合成通用对话"}
        )["status"]
        == "completed"
    )


def test_concurrent_history_read_sees_only_committed_messages_and_continues_after_append(flow):
    conversation = flow.conversation()
    conversation_id = UUID(conversation["id"])
    timestamp = datetime(2023, 1, 1, tzinfo=UTC)
    with Session(flow.engine) as db, db.begin():
        existing = []
        for _ in range(12):
            row = records.create_message(db, flow.owner, conversation_id, "user", "Synthetic past")
            row.created_at = timestamp
            existing.append(row.id)
    path = f"/conversations/{conversation_id}/messages"
    first = flow.call("GET", path, params={"limit": 3})
    entered, release = Event(), Event()

    def write():
        with Session(flow.engine) as db, db.begin():
            new = [
                records.create_message(db, flow.owner, conversation_id, role, "Synthetic new").id
                for role in ("user", "assistant")
            ]
            entered.set()
            assert release.wait(10)
        return new

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(write)
        try:
            assert entered.wait(10)
            during = flow.pages(path, limit=2)
            assert {UUID(row["id"]) for row in during} == set(existing)
        finally:
            release.set()
        appended = future.result(timeout=10)
    remaining = flow.pages(path, limit=3, cursor=first["next_cursor"])
    all_items = first["items"] + remaining
    assert len(all_items) == 14
    assert {UUID(row["id"]) for row in all_items} == set(existing + appended)


def test_imported_domain_is_not_returned_or_used_by_agent_history(flow):
    person = flow.person()
    relationship = flow.relationship(person)
    conversation = flow.conversation(relationship)
    transcript = (
        b"## 2023-11-09 07:51:23 self\n\nSynthetic imported self\n"
        b"## 2023-11-09 07:51:24 A\n\nSynthetic imported other\n"
    )
    uploaded = flow.client.post(
        "/api/v1/chat-imports",
        headers=flow.headers,
        data={"source_timezone": "Asia/Shanghai"},
        files={"file": ("synthetic.md", transcript, "application/octet-stream")},
    )
    assert uploaded.status_code == 201
    job = uploaded.json()
    path = f"/chat-imports/{job['id']}"
    revision = job["binding_revision"]
    for label, kind, person_id in (("self", "self", None), ("A", "person", person["id"])):
        revision = flow.call(
            "PUT",
            path + "/speakers",
            {
                "raw_speaker_label": label,
                "binding_kind": kind,
                "person_id": person_id,
                "expected_revision": revision,
            },
        )["binding_revision"]
    flow.call(
        "PUT",
        path + "/relationship",
        {"relationship_id": relationship["id"], "expected_revision": revision},
    )
    ready = flow.call("POST", path + "/ready")
    assert (
        flow.call("POST", path + "/finalize", {"expected_revision": ready["binding_revision"]})[
            "new_message_count"
        ]
        == 2
    )
    history_path = f"/conversations/{conversation['id']}/messages"
    assert flow.pages(history_path) == []
    imported = flow.pages(f"/relationships/{relationship['id']}/messages")
    assert {row["sender_kind"] for row in imported} == {"self", "person"}
    flow.call(
        "POST", f"/conversations/{conversation['id']}/agent-runs", {"message": "请分析合成背景"}
    )
    assert [row["role"] for row in flow.pages(history_path)] == ["user", "assistant"]
    assert "Synthetic imported" not in str(flow.provider.context_payloads)
    assert "Synthetic imported" not in str(flow.provider.analysis_payloads)


def test_resource_logs_omit_tokens_content_and_sql_error(flow, monkeypatch, caplog):
    marker = "Synthetic-private-label-not-for-logs"
    body = {"id": str(uuid4()), "display_name": marker}
    flow.call("POST", "/persons", body, status=201)
    flow.call("POST", "/persons", {**body, "display_name": "changed"}, status=409)
    assert marker not in caplog.text
    assert flow.headers["Authorization"] not in caplog.text


def test_service_rejects_untrusted_actor_before_any_session(flow):
    def no_session():
        pytest.fail("Untrusted actor opened a database session")

    service = ResourceService(no_session)
    with pytest.raises(ResourceError) as caught:
        service.create_person(None, PersonCreateRequest(id=uuid4(), display_name="Synthetic"))
    assert caught.value.code == ResourceErrorCode.UNAUTHORIZED
    with pytest.raises(ResourceError):
        service.list_persons(None, PageRequest())


def test_real_uvicorn_socket_resource_agent_history_demo(database_engine):
    from resource_api_demo import run_demo

    result = run_demo(database_engine)
    assert result["real_socket"] and result["signed_jwt"] and result["postgresql"]
    assert result["response_loss_retries"] == 3
    assert result["owned_resource_counts"] == {"persons": 1, "relationships": 1, "conversations": 1}


@pytest.mark.parametrize("domain", MODELS)
def test_concurrent_changed_payload_has_one_winner_and_one_conflict(flow, domain):
    body = flow.body(domain)
    changed = dict(body)
    changed.update(
        {
            "persons": {"display_name": "changed"},
            "relationships": {"status": "changed"},
            "conversations": {"relationship_id": None},
        }[domain]
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(
                lambda value: flow.client.post(
                    f"/api/v1/{domain}", json=value, headers=flow.headers
                ),
                (body, changed),
            )
        )
    assert sorted(response.status_code for response in responses) == [201, 409]
    assert row_count(flow, domain, body["id"]) == 1


@pytest.mark.parametrize("domain", MODELS)
def test_two_owners_racing_same_uuid_cannot_claim_each_others_record(flow, domain):
    other = ResourceFlow(flow.client, flow.foreign)
    first, second = flow.body(domain), other.body(domain)
    second["id"] = first["id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(
                lambda args: flow.client.post(f"/api/v1/{domain}", json=args[0], headers=args[1]),
                ((first, flow.headers), (second, other.headers)),
            )
        )
    assert sorted(response.status_code for response in responses) == [201, 404]
    assert row_count(flow, domain, first["id"]) == 1


@pytest.mark.parametrize("domain", MODELS)
@pytest.mark.parametrize("stage", ["after_flush", "commit"])
def test_storage_failure_rolls_back_then_same_id_can_retry(flow, monkeypatch, domain, stage):
    body = flow.body(domain)
    message = "synthetic-private-SQL-and-resource-content"
    function = f"create_{domain[:-1]}" if domain != "persons" else "create_person"
    original = getattr(records, function)

    def fail_after_flush(*args, **kwargs):
        original(*args, **kwargs)
        raise SQLAlchemyError(message)

    def fail_commit(_session):
        raise SQLAlchemyError(message)

    if stage == "after_flush":
        monkeypatch.setattr(records, function, fail_after_flush)
    else:
        event.listen(Session, "before_commit", fail_commit)
    try:
        response = flow.call("POST", f"/{domain}", body, status=503)
    finally:
        if stage == "after_flush":
            monkeypatch.setattr(records, function, original)
        else:
            event.remove(Session, "before_commit", fail_commit)
    assert message not in json.dumps(response)
    assert row_count(flow, domain, body["id"]) == 0
    flow.call("POST", f"/{domain}", body, status=201)
    assert row_count(flow, domain, body["id"]) == 1
