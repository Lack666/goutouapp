"""Signed HTTP, PostgreSQL and Agent integration for public memory controls."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Event
from uuid import UUID, uuid4

import jwt
import pytest
from agent_demo import CaptureMock, queue_run
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.agent.contracts import Fact, MemoryCandidate, MemoryWriteStatus
from app.agent.dependencies import RuntimeDependencies
from app.agent.memory import MemoryService
from app.agent.runtime import AgentRuntime
from app.core.config import Settings
from app.db.models import MemoryControlRow, MemoryRecordRow
from app.db.repositories import records
from app.db.repositories.memory import SQLAlchemyMemoryStore
from app.main import create_app
from app.services.agent_service import AgentService, actor_from_verified_identity
from app.services.memory_control import (
    MemoryControlError,
    MemoryControlErrorCode,
    MemoryControlService,
)

SECRET = "phase6a-synthetic-secret-with-more-than-32-bytes"


def _headers(user_id: UUID) -> dict[str, str]:
    token = jwt.encode(
        {
            "sub": str(user_id),
            "exp": datetime.now(UTC) + timedelta(minutes=5),
            "iss": "phase6a-test",
            "aud": "phase6a-api",
        },
        SECRET,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def _app(engine):
    return create_app(
        Settings(
            app_env="test",
            database_url=engine.url.render_as_string(hide_password=False),
            auth_jwt_secret=SECRET,
            auth_jwt_issuer="phase6a-test",
            auth_jwt_audience="phase6a-api",
            llm_provider="mock",
            _env_file=None,
        )
    )


def _scope(engine):
    with Session(engine) as db:
        owner, outsider = records.create_user(db), records.create_user(db)
        person_a = records.create_person(db, owner.id, "Synthetic A")
        person_b = records.create_person(db, owner.id, "Synthetic B")
        relation_a = records.create_relationship(db, owner.id, person_a.id, "dating", "active")
        relation_b = records.create_relationship(db, owner.id, person_b.id, "dating", "active")
        conversation = records.create_conversation(db, owner.id, relation_a.id)
        ids = (
            owner.id,
            outsider.id,
            person_a.id,
            person_b.id,
            relation_a.id,
            relation_b.id,
            conversation.id,
        )
        db.commit()
        return ids


def _save(store, owner, person, relationship, content):
    from app.agent.contracts import Fact, MemoryCandidate

    return MemoryService(store).persist_candidates(
        user_id=owner,
        relationship_id=relationship,
        run_id=uuid4(),
        candidates=[
            MemoryCandidate(
                subject_id=person,
                type="relationship",
                content=content,
                source="user_explicit",
                evidence="F1",
            )
        ],
        facts=[Fact(statement=content, source="user_explicit")],
        message=f"我明确同意记住：{content}",
        explicit_consent=True,
    )


def test_controls_are_durable_idempotent_and_signed(database_engine, monkeypatch):
    owner, outsider, *_ = _scope(database_engine)
    app = _app(database_engine)
    calls = []
    monkeypatch.setattr(
        "app.api.dependencies.create_llm_provider",
        lambda _settings: calls.append(1),
    )
    with TestClient(app) as client:
        assert client.get("/api/v1/memory/control").status_code == 401
        assert client.get("/api/v1/memory/control", headers=_headers(uuid4())).status_code == 401
        assert (
            client.get(
                "/api/v1/memory/control", headers={"Authorization": "Bearer bad"}
            ).status_code
            == 401
        )
        h = _headers(owner)
        initial = client.get("/api/v1/memory/control", headers=h).json()
        assert initial["consent_enabled"] is False
        assert initial["updated_at"] is None
        for _ in range(2):
            granted = client.post("/api/v1/memory/consent", json={"enabled": True}, headers=h)
            assert granted.status_code == 200
            assert granted.json()["effective_write_enabled"] is True
        grant_time = granted.json()["updated_at"]
        assert grant_time
        paused = client.post("/api/v1/memory/pause", headers=h).json()
        assert paused["paused"] and not paused["effective_read_enabled"]
        assert client.post("/api/v1/memory/pause", headers=h).json() == paused
        assert client.get("/api/v1/memory/control", headers=h).json() == paused
        with Session(database_engine) as db:
            rows = db.scalars(
                select(MemoryControlRow).where(MemoryControlRow.user_id == owner)
            ).all()
            assert len(rows) == 1
        assert client.post("/api/v1/memory/resume", headers=h).json()["effective_read_enabled"]
        revoked = client.post("/api/v1/memory/consent", json={"enabled": False}, headers=h).json()
        assert revoked["paused"] and not revoked["consent_enabled"]
        assert client.post("/api/v1/memory/resume", headers=h).json() == revoked
        assert (
            client.post("/api/v1/memory/consent", json={"enabled": False}, headers=h).json()
            == revoked
        )
        assert (
            client.get("/api/v1/memory/control", headers=_headers(outsider)).json()[
                "consent_enabled"
            ]
            is False
        )
        assert (
            client.post(
                "/api/v1/memory/consent",
                json={"enabled": True, "user_id": str(outsider)},
                headers=h,
            ).status_code
            == 422
        )
        assert client.post("/api/v1/memory/consent", json={"enabled": True}, headers=h).json()[
            "paused"
        ]
    fresh = MemoryControlService(SQLAlchemyMemoryStore(lambda: Session(database_engine)))
    state = fresh.inspect_control(actor_from_verified_identity(owner))
    assert state.consent_enabled and state.paused and state.updated_at is not None
    assert calls == [] and app.state.agent_service is None


def test_inspect_scope_pagination_and_privacy(database_engine):
    owner, outsider, person_a, person_b, relation_a, relation_b, _ = _scope(database_engine)
    store = SQLAlchemyMemoryStore(lambda: Session(database_engine))
    for n in range(5):
        assert _save(store, owner, person_a, relation_a, f"我们计划第{n}周见面").saved_count == 1
    assert _save(store, owner, person_b, relation_b, "我们计划明年见面").saved_count == 1
    # Equal timestamps exercise the UUID tiebreaker.
    with Session(database_engine) as db:
        rows = db.scalars(
            select(MemoryRecordRow).where(MemoryRecordRow.owner_user_id == owner)
        ).all()
        stamp = rows[0].created_at
        for row in rows:
            row.created_at = stamp
        db.commit()
    with TestClient(_app(database_engine)) as client:
        h = _headers(owner)
        seen = []
        cursor = None
        while True:
            params = {"limit": 2}
            if cursor:
                params["cursor"] = cursor
            response = client.get("/api/v1/memories", headers=h, params=params)
            assert response.status_code == 200
            payload = response.json()
            assert "may no longer be accurate" in payload["historical_notice"]
            for item in payload["items"]:
                assert set(item) == {
                    "id",
                    "type",
                    "content",
                    "subject_id",
                    "person_id",
                    "relationship_id",
                    "source",
                    "provenance_summary",
                    "created_at",
                    "updated_at",
                    "historical_notice",
                }
                seen.append(item["id"])
            cursor = payload["next_cursor"]
            if cursor is None:
                break
        assert len(seen) == len(set(seen)) == 6
        assert client.get(f"/api/v1/memories/{seen[0]}", headers=h).json()["id"] == seen[0]
        assert (
            client.get(f"/api/v1/memories/{seen[0]}", headers=_headers(outsider)).json()["error"][
                "code"
            ]
            == "memory_not_found"
        )
        assert (
            client.get(f"/api/v1/memories/{uuid4()}", headers=h).json()["error"]["code"]
            == "memory_not_found"
        )
        assert (
            len(
                client.get(
                    "/api/v1/memories", headers=h, params={"person_id": str(person_a)}
                ).json()["items"]
            )
            == 5
        )
        assert (
            len(
                client.get(
                    "/api/v1/memories", headers=h, params={"relationship_id": str(relation_b)}
                ).json()["items"]
            )
            == 1
        )
        assert client.get("/api/v1/memories", headers=_headers(outsider)).json()["items"] == []
        assert (
            client.get(
                "/api/v1/memories", headers=_headers(outsider), params={"person_id": str(person_a)}
            ).status_code
            == 404
        )
        assert (
            client.get(
                "/api/v1/memories",
                headers=_headers(outsider),
                params={"relationship_id": str(relation_a)},
            ).status_code
            == 404
        )
        assert (
            client.get(
                "/api/v1/memories",
                headers=h,
                params={"person_id": str(person_b), "relationship_id": str(relation_a)},
            ).json()["error"]["code"]
            == "invalid_scope"
        )
        assert client.get("/api/v1/memories", headers=h, params={"limit": 51}).status_code == 422
        assert (
            client.get("/api/v1/memories", headers=h, params={"cursor": "not-base64"}).json()[
                "error"
            ]["code"]
            == "invalid_scope"
        )
    with Session(database_engine) as db:
        assert (
            len(
                db.scalars(
                    select(MemoryRecordRow).where(MemoryRecordRow.owner_user_id == owner)
                ).all()
            )
            == 6
        )


def test_signed_api_controls_agent_runtime_and_inspect(database_engine):
    owner, _, person, _, relationship, _, conversation = _scope(database_engine)
    app = _app(database_engine)
    store = SQLAlchemyMemoryStore(app.state.database.session)
    actor = actor_from_verified_identity(owner)

    def run(first: bool):
        provider = CaptureMock()
        queue_run(provider, first=first, person_id=person)
        service = AgentService(
            app.state.database.session,
            AgentRuntime(
                dependencies=RuntimeDependencies(
                    llm_provider=provider, memory_service=MemoryService(store)
                )
            ),
        )
        message = (
            "请记住我们已确认关系，写入长期记忆。" if first else "请根据之前的关系背景分析现状。"
        )
        result = asyncio.run(
            service.execute(
                actor=actor,
                conversation_id=conversation,
                relationship_id=relationship,
                person_id=person,
                message=message,
            )
        )
        return result, provider

    with TestClient(app) as client:
        h = _headers(owner)
        assert run(True)[0].memory_status != "saved"
        assert client.get("/api/v1/memories", headers=h).json()["items"] == []
        assert (
            client.post("/api/v1/memory/consent", headers=h, json={"enabled": True}).status_code
            == 200
        )
        saved, _ = run(True)
        assert saved.memory_status == "saved"
        inspect = client.get("/api/v1/memories", headers=h).json()
        assert len(inspect["items"]) == 1
        record_id = inspect["items"][0]["id"]
        assert client.post("/api/v1/memory/pause", headers=h).status_code == 200
        paused, provider = run(True)
        assert paused.memory_status != "saved"
        assert provider.analysis_payloads[0]["historical_memory"] == []
        assert len(client.get("/api/v1/memories", headers=h).json()["items"]) == 1
        assert client.post("/api/v1/memory/resume", headers=h).json()["effective_write_enabled"]
        resumed, provider = run(False)
        assert resumed.status == "completed"
        assert len(provider.analysis_payloads[0]["historical_memory"]) == 1
        assert (
            client.post("/api/v1/memory/consent", headers=h, json={"enabled": False}).status_code
            == 200
        )
        blocked, provider = run(True)
        assert blocked.memory_status != "saved"
        assert provider.analysis_payloads[0]["historical_memory"] == []
        assert client.get("/api/v1/memories", headers=h).json()["items"][0]["id"] == record_id
        assert client.post("/api/v1/memory/consent", headers=h, json={"enabled": True}).json()[
            "paused"
        ]
        assert client.post("/api/v1/memory/resume", headers=h).json()["effective_read_enabled"]
        assert len(MemoryService(store).load_for_context(owner, relationship, enabled=True)) == 1


def test_concurrent_control_requests_leave_one_valid_row(database_engine):
    owner, *_ = _scope(database_engine)
    with TestClient(_app(database_engine)) as client:
        h = _headers(owner)
        client.post("/api/v1/memory/consent", headers=h, json={"enabled": True})

        def mutate(index):
            if index % 2:
                return client.post("/api/v1/memory/pause", headers=h)
            return client.post("/api/v1/memory/resume", headers=h)

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(mutate, range(16)))
        assert all(response.status_code == 200 for response in results)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(
                pool.map(
                    lambda index: client.post(
                        "/api/v1/memory/consent", headers=h, json={"enabled": bool(index % 2)}
                    ),
                    range(16),
                )
            )
        assert all(response.status_code == 200 for response in results)
        final = client.get("/api/v1/memory/control", headers=h).json()
        assert final["effective_read_enabled"] == final["effective_write_enabled"]
        assert final["effective_read_enabled"] == (final["consent_enabled"] and not final["paused"])
    with Session(database_engine) as db:
        rows = db.scalars(select(MemoryControlRow).where(MemoryControlRow.user_id == owner)).all()
        assert len(rows) == 1


def test_openapi_read_only_inspection_and_safe_errors(database_engine, monkeypatch):
    owner, outsider, person, _, relationship, _, _ = _scope(database_engine)
    app = _app(database_engine)
    store = SQLAlchemyMemoryStore(app.state.database.session)
    _save(store, owner, person, relationship, "我们计划下周见面")
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()
        for path in (
            "/api/v1/memory/control",
            "/api/v1/memory/consent",
            "/api/v1/memory/pause",
            "/api/v1/memory/resume",
            "/api/v1/memories",
            "/api/v1/memories/{memory_id}",
        ):
            for operation in schema["paths"][path].values():
                assert operation["security"] == [{"BearerCredential": []}]
        h = _headers(owner)
        before_control = store.control_state(owner)
        with Session(database_engine) as db:
            before_record = db.scalar(
                select(MemoryRecordRow).where(MemoryRecordRow.owner_user_id == owner)
            ).updated_at
        client.get("/api/v1/memory/control", headers=h)
        client.get("/api/v1/memories", headers=h)
        assert store.control_state(owner) == before_control
        with Session(database_engine) as db:
            after_record = db.scalar(
                select(MemoryRecordRow).where(MemoryRecordRow.owner_user_id == owner)
            ).updated_at
        assert before_record == after_record
        assert (
            client.get(
                "/api/v1/memories", headers=_headers(outsider), params={"person_id": str(person)}
            ).json()["error"]["code"]
            == "person_not_found"
        )

    service = MemoryControlService(store)
    with pytest.raises(MemoryControlError) as exc:
        service.inspect_control(owner)
    assert exc.value.code == MemoryControlErrorCode.UNAUTHORIZED
    monkeypatch.setattr(store, "owner_exists", lambda _id: (_ for _ in ()).throw(SQLAlchemyError()))
    with pytest.raises(MemoryControlError) as exc:
        service.inspect_control(actor_from_verified_identity(owner))
    assert exc.value.code == MemoryControlErrorCode.PERSISTENCE_FAILURE


@pytest.mark.parametrize(
    ("operation", "expected"),
    [
        ("pause", MemoryWriteStatus.SKIPPED_PAUSED),
        ("revoke", MemoryWriteStatus.SKIPPED_NO_CONSENT),
    ],
)
def test_control_change_during_agent_write_blocks_commit(
    database_engine, monkeypatch, operation, expected
):
    owner, _, person, _, relationship, _, _ = _scope(database_engine)
    store = SQLAlchemyMemoryStore(lambda: Session(database_engine))
    service = MemoryService(store)
    service.grant_consent(owner, confirmed=True)
    entered, release = Event(), Event()
    actual_save = store.save_record

    def delayed_save(record):
        entered.set()
        if not release.wait(5):
            raise RuntimeError("test write gate did not resume")
        return actual_save(record)

    monkeypatch.setattr(store, "save_record", delayed_save)

    def write():
        content = "我们计划下周见面"
        return service.persist_candidates(
            user_id=owner,
            relationship_id=relationship,
            run_id=uuid4(),
            candidates=[
                MemoryCandidate(
                    subject_id=person,
                    type="relationship",
                    content=content,
                    source="user_explicit",
                    evidence="F1",
                )
            ],
            facts=[Fact(statement=content, source="user_explicit")],
            message=f"请记住{content}，写入长期记忆。",
            explicit_consent=False,
        )

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(write)
        try:
            assert entered.wait(5)
            with TestClient(_app(database_engine)) as client:
                h = _headers(owner)
                if operation == "pause":
                    assert client.post("/api/v1/memory/pause", headers=h).status_code == 200
                else:
                    assert (
                        client.post(
                            "/api/v1/memory/consent", headers=h, json={"enabled": False}
                        ).status_code
                        == 200
                    )
        finally:
            release.set()
        assert future.result(timeout=5).status == expected
    assert store.list_records(owner) == []
