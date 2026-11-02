"""Anonymous, actual signed HTTP + PostgreSQL ICA-A acceptance (zero Provider)."""

import json
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from test_agent_rest import headers, settings
from test_import_api import finalize, scope

from app.chat_import.analysis_scope import calendar_window
from app.db.models import (
    ImportedAnalysisGrant,
    MemoryControlRow,
    MemoryRecordRow,
    RelationshipMessage,
)
from app.main import create_app
from app.services.agent_service import actor_from_verified_identity
from app.services.imported_analysis import ImportedAnalysisService

BASE = "/api/v1/imported-analysis"


def jsonl(count, days=7):
    start, _ = calendar_window("Asia/Shanghai", datetime.now(UTC), days=days)
    rows = [
        {
            "_type": "header",
            "chatlab": {
                "version": "0.0.2",
                "exportedAt": int(datetime.now(UTC).timestamp()),
                "generator": "WeFlow",
            },
            "meta": {"name": "Anonymous", "platform": "wechat", "type": "private"},
        }
    ]
    rows += [
        {"_type": "member", "platformId": label, "accountName": "Same nickname"}
        for label in ("self-id", "person-id")
    ]
    rows += [
        {
            "_type": "message",
            "sender": "self-id" if i % 2 else "person-id",
            "accountName": "Same nickname",
            "timestamp": int((start + timedelta(seconds=i)).timestamp()),
            "type": 0,
            "content": "好😀",
            "platformMessageId": str(i),
            **({"replyToMessageId": str(i - 1)} if i else {}),
        }
        for i in range(count)
    ]
    return ("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n").encode()


def imported(client, who, count=2100, days=7, content=None):
    owner, person, relationship, _ = who
    upload = client.post(
        "/api/v1/chat-imports",
        headers=headers(owner),
        data={"source_timezone": "Asia/Shanghai", "source_format": "chatlab_jsonl_v0_0_2"},
        files={
            "file": ("anonymous.jsonl", content or jsonl(count, days), "application/octet-stream")
        },
    )
    assert upload.status_code == 201, upload.text
    job = upload.json()
    path = f"/api/v1/chat-imports/{job['id']}"
    bindings = [("self-id", "self", None), ("person-id", "person", person)]
    if any(s["raw_speaker_label"] == "system-id" for s in job["speakers"]):
        bindings.append(("system-id", "system", None))
    for label, kind, pid in bindings:
        response = client.put(
            path + "/speakers",
            headers=headers(owner),
            json={
                "raw_speaker_label": label,
                "binding_kind": kind,
                "person_id": str(pid) if pid else None,
                "expected_revision": job["binding_revision"],
            },
        )
        assert response.status_code == 200, response.text
        job = response.json()
    response = client.put(
        path + "/relationship",
        headers=headers(owner),
        json={"relationship_id": str(relationship), "expected_revision": job["binding_revision"]},
    )
    assert response.status_code == 200, response.text
    ready = client.post(path + "/ready", headers=headers(owner))
    assert ready.status_code == 200, ready.text
    result = finalize(client, owner, ready.json())
    assert result.status_code == 200, result.text
    return result.json()


@pytest.fixture
def api(database_engine, tmp_path):
    app = create_app(settings(database_engine, chat_import_artifact_root=tmp_path / "artifacts"))
    a, b = scope(database_engine), scope(database_engine)
    with TestClient(app) as client:
        yield app, client, a, b


def preparation(client, who, dataset, days=7, **changes):
    body = {
        "dataset_id": dataset,
        "relationship_id": str(who[2]),
        "person_id": str(who[1]),
        "timezone": "Asia/Shanghai",
        "windows": [{"days": days}],
        "question": "匿名复盘问题",
        "model": "future-model-unquoted",
        "max_tokens": 100_000_000,
        "max_requests": 104,
        **changes,
    }
    return client.post(BASE + "/prepare", headers=headers(who[0]), json=body)


def confirmation(prepared, **changes):
    return {
        "preparation_id": prepared["preparation_id"],
        "challenge": prepared["challenge"],
        "binding_hash": prepared["binding_hash"],
        "operation_key": "ica-" + uuid4().hex,
        "confirmed": True,
        **changes,
    }


def confirm(client, who, prepared, **changes):
    return client.post(
        BASE + "/confirm", headers=headers(who[0]), json=confirmation(prepared, **changes)
    )


@pytest.mark.parametrize("count,days,k", [(900, 3, 5), (2100, 7, 11)])
def test_signed_demo(api, database_engine, count, days, k):
    app, client, a, b = api
    from test_memory_control import _save

    from app.db.repositories.memory import SQLAlchemyMemoryStore

    assert (
        _save(
            SQLAlchemyMemoryStore(lambda: Session(database_engine)),
            a[0],
            a[1],
            a[2],
            "Synthetic retained memory",
        ).saved_count
        == 1
    )
    assert client.post("/api/v1/memory/pause", headers=headers(a[0])).status_code == 200
    control_before = client.get("/api/v1/memory/control", headers=headers(a[0])).json()
    with Session(database_engine) as db:
        before = (
            db.scalar(select(func.count()).select_from(MemoryRecordRow)),
            db.scalar(select(func.count()).select_from(MemoryControlRow)),
        )
    raw = jsonl(count, days)
    receipt = imported(client, a, count, days, raw)
    dataset = receipt["dataset_job_id"]
    duplicate = imported(client, a, count, days, raw)
    assert duplicate["dataset_job_id"] == dataset
    tracemalloc.start()
    response = preparation(client, a, dataset, days)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert response.status_code == 200, response.text
    prepared = response.json()
    assert prepared["preview"]["messages"] == count
    assert prepared["preview"]["chunks"] == k
    assert prepared["preview"]["planned_requests"] == 3 * k + 8
    assert prepared["preview"]["body_bytes"] == count * len("好😀".encode())
    assert prepared["preview"]["cost_cap"] is None
    assert len(prepared["preview"]["windows"][0]["daily"]) == days
    with Session(database_engine) as db:
        row = db.get(ImportedAnalysisGrant, UUID(prepared["preparation_id"]))
        assert row.status == "prepared" and row.confirmed_at is None
    assert confirm(client, b, prepared).status_code == 404
    assert confirm(client, a, prepared, challenge="x" * 43).status_code == 409
    assert confirm(client, a, prepared, binding_hash="f" * 64).status_code == 409
    assert confirm(client, a, prepared, confirmed=1).status_code == 422
    assert confirm(client, a, prepared, confirmed=False).status_code == 422
    grant = confirm(client, a, prepared)
    assert grant.status_code == 200, grant.text
    grant = grant.json()
    core = [i for m in grant["manifests"] for i in m["core"]]
    assert len(core) == len(set(core)) == count
    assert all(set(m["stages"].values()) == {"pending"} for m in grant["manifests"])
    alias = next(iter(grant["evidence_aliases"]))
    url = BASE + f"/grants/{grant['grant_id']}/evidence/{alias}"
    evidence = client.post(url, headers=headers(a[0]), json={"start": 1, "end": 2, "quote": "😀"})
    assert evidence.status_code == 200, evidence.text
    assert evidence.json()["external_message_id"] is not None
    assert (
        client.post(
            url, headers=headers(b[0]), json={"start": 0, "end": 1, "quote": "好"}
        ).status_code
        == 404
    )
    assert (
        client.post(
            url, headers=headers(a[0]), json={"start": 1, "end": 3, "quote": "😀"}
        ).status_code
        == 409
    )
    deletion = {"domain": "dataset", "target_id": dataset, "relationship_id": str(a[2])}
    challenge = client.post("/api/v1/erasures/prepare", headers=headers(a[0]), json=deletion)
    assert challenge.status_code == 200, challenge.text
    deleted = client.post(
        "/api/v1/erasures/execute",
        headers=headers(a[0]),
        json={
            **deletion,
            "confirmation_id": challenge.json()["confirmation_id"],
            "operation_key": "ica-delete",
        },
    )
    assert deleted.status_code == 200, deleted.text
    assert (
        client.post(
            url, headers=headers(a[0]), json={"start": 1, "end": 2, "quote": "😀"}
        ).status_code
        == 409
    )
    with Session(database_engine) as db:
        row = db.get(ImportedAnalysisGrant, UUID(grant["grant_id"]))
        assert row.status == "deleted" and row.payload == {}
        after = (
            db.scalar(select(func.count()).select_from(MemoryRecordRow)),
            db.scalar(select(func.count()).select_from(MemoryControlRow)),
        )
        assert before == after
    assert app.state.agent_service is None
    assert client.get("/api/v1/memory/control", headers=headers(a[0])).json() == control_before
    output = Path(".cache/ica-completion-evidence")
    output.mkdir(exist_ok=True)
    (output / f"signed-demo-{count}.json").write_text(
        json.dumps(
            {
                "preview": prepared["preview"],
                "manifests": grant["manifests"],
                "core_count": len(core),
                "peak_python_bytes": peak,
                "confirmed": True,
                "tamper_rejected": True,
                "outsider_rejected": True,
                "deleted_read_rejected": True,
                "memory_unchanged": True,
                "provider_calls": 0,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_expiry_revocation_concurrency_and_source_change(api, database_engine):
    _, client, a, _ = api
    receipt = imported(client, a, 20)
    dataset = receipt["dataset_job_id"]
    prepared = preparation(client, a, dataset).json()
    body = confirmation(prepared)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(
                lambda _: client.post(BASE + "/confirm", headers=headers(a[0]), json=body), range(2)
            )
        )
    assert all(r.status_code == 200 for r in responses), [r.text for r in responses]
    assert responses[0].json() == responses[1].json()
    gid = prepared["preparation_id"]
    assert confirm(client, a, prepared).status_code == 409
    assert client.post(BASE + f"/grants/{gid}/revoke", headers=headers(a[0])).status_code == 200
    assert client.post(BASE + f"/grants/{gid}/revoke", headers=headers(a[0])).status_code == 200
    assert client.get(BASE + f"/grants/{gid}", headers=headers(a[0])).status_code == 409
    prepared = preparation(client, a, dataset).json()
    with Session(database_engine) as db, db.begin():
        row = db.get(ImportedAnalysisGrant, UUID(prepared["preparation_id"]))
        row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert confirm(client, a, prepared).status_code == 409
    service = ImportedAnalysisService(lambda: Session(database_engine))
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: service.cleanup(), range(2)))
    with Session(database_engine) as db:
        assert db.get(ImportedAnalysisGrant, UUID(prepared["preparation_id"])).payload == {}
    prepared = preparation(client, a, dataset).json()
    grant = confirm(client, a, prepared).json()
    with Session(database_engine) as db, db.begin():
        message = db.scalar(
            select(RelationshipMessage).where(RelationshipMessage.import_job_id == UUID(dataset))
        )
        message.content = "source changed"
    assert (
        client.get(BASE + f"/grants/{grant['grant_id']}", headers=headers(a[0])).status_code == 409
    )
    prepared = preparation(client, a, dataset).json()
    expiring = confirm(client, a, prepared).json()
    with Session(database_engine) as db, db.begin():
        db.get(ImportedAnalysisGrant, UUID(expiring["grant_id"])).expires_at = datetime.now(
            UTC
        ) - timedelta(seconds=1)
    assert (
        client.get(BASE + f"/grants/{expiring['grant_id']}", headers=headers(a[0])).status_code
        == 409
    )
    service.cleanup()
    with Session(database_engine) as db:
        assert db.get(ImportedAnalysisGrant, UUID(expiring["grant_id"])).payload == {}


def test_scope_isolation_budget_and_two_windows(api):
    _, client, a, b = api
    dataset = imported(client, a, 20)["dataset_job_id"]
    assert preparation(client, b, dataset).status_code == 404
    assert preparation(client, a, dataset, person_id=str(b[1])).status_code == 404
    assert preparation(client, a, dataset, relationship_id=str(b[2])).status_code == 404
    assert preparation(client, a, dataset, max_tokens=1).status_code == 409
    assert preparation(client, a, dataset, windows=[{"days": 3}, {"days": 7}]).status_code == 409
    today = datetime.now(UTC).date()
    windows = [
        {"first": str(today - timedelta(days=6)), "last": str(today - timedelta(days=4))},
        {"first": str(today - timedelta(days=3)), "last": str(today)},
    ]
    result = preparation(client, a, dataset, windows=windows)
    assert result.status_code == 200, result.text
    grant = confirm(client, a, result.json()).json()
    assert all(str(i).startswith("w") for i in grant["evidence_aliases"])
    bywindow = {
        i: {v["message_id"] for v in grant["evidence_aliases"].values() if v["window"] == i}
        for i in (0, 1)
    }
    for chunk in grant["manifests"]:
        assert (
            set(chunk["core"] + chunk["halo_before"] + chunk["halo_after"])
            <= bywindow[chunk["window"]]
        )


@pytest.mark.parametrize("domain", ["person", "relationship", "owner"])
def test_full_deletion_invalidates_grants(api, database_engine, domain):
    _, client, a, _ = api
    dataset = imported(client, a, 10)["dataset_job_id"]
    grant = confirm(client, a, preparation(client, a, dataset).json()).json()
    target = {
        "domain": domain,
        "target_id": str(a[0] if domain == "owner" else a[1] if domain == "person" else a[2]),
    }
    # Owner erasure is an existing development-operator operation, not a new ICA capability.
    if domain == "owner":
        from app.schemas.lifecycle import LifecycleExecute, LifecycleTarget
        from app.services.agent_writer import AgentWriterRegistry
        from app.services.lifecycle_erasure import LifecycleErasure

        app = api[0]
        service = LifecycleErasure(
            app.state.database.session,
            app.state.import_artifact_store,
            AgentWriterRegistry(app.state.settings.chat_import_artifact_root),
        )
        actor = actor_from_verified_identity(a[0])
        challenge = service.prepare(actor, LifecycleTarget(**target))
        service.execute(
            actor,
            LifecycleExecute(
                **target, confirmation_id=challenge.confirmation_id, operation_key="ica-full"
            ),
        )
    else:
        challenge = client.post(
            "/api/v1/lifecycle-erasures/prepare", headers=headers(a[0]), json=target
        )
        assert challenge.status_code == 200, challenge.text
        result = client.post(
            "/api/v1/lifecycle-erasures/execute",
            headers=headers(a[0]),
            json={
                **target,
                "confirmation_id": challenge.json()["confirmation_id"],
                "operation_key": "ica-full",
            },
        )
        assert result.status_code == 200, result.text
    assert client.get(BASE + f"/grants/{grant['grant_id']}", headers=headers(a[0])).status_code in (
        401,
        404,
        409,
    )
    with Session(database_engine) as db:
        row = db.get(ImportedAnalysisGrant, UUID(grant["grant_id"]))
        assert row.payload == {} and row.status == "deleted"


def test_native_restore_never_resurrects_grants(api, database_engine, tmp_path):
    from app.services.backup_restore import dump_synthetic, restore_synthetic

    _, client, a, _ = api
    dataset = imported(client, a, 10)["dataset_job_id"]
    prepared = preparation(client, a, dataset).json()
    grant = confirm(client, a, prepared).json()
    archive = tmp_path / "ica.dump"
    dump_synthetic(database_engine, archive)
    client.post(BASE + f"/grants/{grant['grant_id']}/revoke", headers=headers(a[0]))
    root = tmp_path / "restored-artifacts"
    root.mkdir()
    with restore_synthetic(database_engine, archive, root) as restored:
        assert not restored.released
        engine = restored.reconcile()
        assert restored.released
        with Session(engine) as db:
            row = db.get(ImportedAnalysisGrant, UUID(grant["grant_id"]))
            assert row.status == "restore_invalid" and row.payload == {}
        service = ImportedAnalysisService(lambda: Session(engine))
        from app.services.imported_analysis import AnalysisError

        with pytest.raises(AnalysisError):
            service.inspect(actor_from_verified_identity(a[0]), UUID(grant["grant_id"]))


def test_10k_keyset_sql_bounds_and_explain(api, database_engine):
    from sqlalchemy import event

    from app.chat_import.analysis_scope import AnalysisScope
    from app.services.imported_scope import read_scope

    _, client, a, _ = api
    dataset = imported(client, a, 10000)["dataset_job_id"]
    start, end = calendar_window("Asia/Shanghai", datetime.now(UTC), days=7)
    windows = AnalysisScope(a[0], a[1], UUID(dataset), "Asia/Shanghai", start, end)
    queries = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        if "FROM relationship_messages" in statement:
            queries.append(statement)

    event.listen(database_engine, "before_cursor_execute", capture)
    try:
        with Session(database_engine) as db, db.begin():
            tracemalloc.start()
            count = sum(1 for _ in read_scope(db, actor_from_verified_identity(a[0]), windows))
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
        assert count == 10000 and len(queries) == 21
        assert all("LIMIT" in q and "OFFSET" not in q for q in queries)
        assert all("timestamp_utc," in q for q in queries[1:])
    finally:
        event.remove(database_engine, "before_cursor_execute", capture)
    assert preparation(client, a, dataset).status_code == 409
    with Session(database_engine) as db:
        plan = db.execute(
            text(
                "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) SELECT id, timestamp_utc "
                "FROM relationship_messages WHERE owner_user_id=:owner AND import_job_id=:dataset "
                "AND timestamp_utc>=:start AND timestamp_utc<:end "
                "ORDER BY timestamp_utc,id LIMIT 500"
            ),
            {"owner": a[0], "dataset": UUID(dataset), "start": start, "end": end},
        ).scalar()
    Path(".cache/ica-completion-evidence/sql-10k.json").write_text(
        json.dumps(
            {
                "count": count,
                "pages": 21,
                "page_limit": 500,
                "python_peak_bytes": peak,
                "explain": plan,
            },
            default=str,
            indent=2,
        ),
        encoding="utf-8",
    )


def test_migration_roundtrip_and_database_isolation():
    from alembic import command
    from alembic.config import Config
    from memory_control_demo import disposable_database

    with disposable_database() as engine:
        config = Config("alembic.ini")
        config.attributes["database_url"] = engine.url.render_as_string(hide_password=False)
        command.downgrade(config, "20261014_01")
        with engine.connect() as conn:
            assert conn.scalar(text("SELECT to_regclass('imported_analysis_grants')")) is None
        command.upgrade(config, "head")
        with engine.connect() as conn:
            assert conn.scalar(text("SELECT count(*) FROM imported_analysis_grants")) == 0
            name = conn.scalar(text("SELECT current_database()"))
            assert name.endswith(engine.url.database[-12:]) and "_test_" in name
    # disposable_database drops only the unique database it created.
    import os

    from sqlalchemy import create_engine
    from sqlalchemy.engine import make_url

    admin = create_engine(make_url(os.environ["TEST_DATABASE_URL"]).set(database="postgres"))
    try:
        with admin.connect() as conn:
            assert (
                conn.scalar(
                    text("SELECT count(*) FROM pg_database WHERE datname=:name"), {"name": name}
                )
                == 0
            )
    finally:
        admin.dispose()


def test_sql_dst_reverse_equal_times_media_system_and_empty_days(api, database_engine):
    _, client, a, _ = api
    rows = [json.loads(line) for line in jsonl(5).decode().splitlines()]
    rows.insert(3, {"_type": "member", "platformId": "system-id", "accountName": "System"})
    times = [1793514600, 1793511000, 1793511000, 1793511000, 1793511000]
    messages = [r for r in rows if r["_type"] == "message"]
    for m, ts in zip(messages, times, strict=True):
        m["timestamp"] = ts
    messages[2].update(sender="system-id", type=80, content="System notice")
    messages[3].update(type=1, content=None)
    raw = ("\n".join(json.dumps(r) for r in rows) + "\n").encode()
    dataset = imported(client, a, content=raw)["dataset_job_id"]
    result = preparation(
        client,
        a,
        dataset,
        timezone="America/New_York",
        windows=[{"first": "2026-10-31", "last": "2026-11-02"}],
    )
    assert result.status_code == 200, result.text
    stats = result.json()["preview"]["windows"][0]
    assert stats["messages"] == 5 and stats["nontext"] == 2
    assert stats["media"] == stats["system"] == 1
    assert stats["analyzable_text"] == 3
    assert sum(stats["daily"]["2026-10-31"].values()) == 0
    assert sum(stats["daily"]["2026-11-01"].values()) == 5
    grant = confirm(client, a, result.json()).json()
    with Session(database_engine) as db:
        source = list(
            db.scalars(
                select(RelationshipMessage)
                .where(RelationshipMessage.import_job_id == UUID(dataset))
                .order_by(RelationshipMessage.timestamp_utc, RelationshipMessage.id)
            )
        )
        assert grant["manifests"][0]["core"] == [str(m.id) for m in source]
        assert len({m.id for m in source}) == 5


def test_jsonl_http_invalid_version_is_rejected(api):
    _, client, a, _ = api
    raw = jsonl(2).replace(b"0.0.2", b"9.9.9")
    result = client.post(
        "/api/v1/chat-imports",
        headers=headers(a[0]),
        data={"source_timezone": "UTC", "source_format": "chatlab_jsonl_v0_0_2"},
        files={"file": ("invalid.jsonl", raw, "application/octet-stream")},
    )
    assert result.status_code == 422, result.text
