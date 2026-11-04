"""Signed HTTP + actual PostgreSQL + keyless Runtime engineering acceptance."""

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Event
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_agent_rest import headers, settings
from test_ica_signed import BASE, confirm, confirmation, imported, jsonl, preparation
from test_import_api import scope

from app.db.models import (
    ImportedAnalysisGrant,
    ImportedAnalysisRun,
    MemoryControlRow,
    MemoryRecordRow,
    RelationshipMessage,
)
from app.llm.mock import MockLLMProvider
from app.main import create_app
from app.services.agent_service import actor_from_verified_identity
from app.services.imported_analysis import ImportedAnalysisService

REVIEW = dict(
    approved=True,
    grounded=True,
    respects_boundaries=True,
    preserves_counterevidence=True,
    reason_codes=[],
)


def queue_empty(k, provider=None):
    provider = provider or MockLLMProvider()
    for _ in range(k):
        provider.queue_structured({"decision": "normal", "risks": []})
    for _ in range(k):
        provider.queue_structured({"candidates": []})
    provider.queue_structured({"findings": []})
    provider.queue_structured(REVIEW)
    return provider


@pytest.fixture
def execution_api(database_engine, tmp_path):
    app = create_app(
        settings(
            database_engine,
            ica_mock_execution_enabled=True,
            chat_import_artifact_root=tmp_path / "artifacts",
        )
    )
    a, b = scope(database_engine), scope(database_engine)
    with TestClient(app) as client:
        yield app, client, a, b


def authorized(client, who, count=10, days=7):
    dataset = imported(client, who, count, days)["dataset_job_id"]
    prepared = preparation(client, who, dataset, days, model="mock").json()
    grant = confirm(client, who, prepared).json()
    response = client.post(
        BASE + "/execution-prepare", headers=headers(who[0]), json={"grant_id": grant["grant_id"]}
    )
    assert response.status_code == 200, response.text
    pending = response.json()
    body = confirmation(pending)
    confirmed = client.post(BASE + "/execution-confirm", headers=headers(who[0]), json=body)
    assert confirmed.status_code == 200, confirmed.text
    return grant, pending, body, confirmed.json()


@pytest.mark.parametrize("count,days,k", [(900, 3, 5), (2100, 7, 11)])
def test_signed_complete_coverage_and_memory_unchanged(
    execution_api, database_engine, count, days, k
):
    app, client, a, b = execution_api
    from test_memory_control import _save

    from app.db.repositories.memory import SQLAlchemyMemoryStore

    assert (
        _save(
            SQLAlchemyMemoryStore(lambda: Session(database_engine)),
            a[0],
            a[1],
            a[2],
            "Anonymous retained control",
        ).saved_count
        == 1
    )
    client.post("/api/v1/memory/pause", headers=headers(a[0]))
    control = client.get("/api/v1/memory/control", headers=headers(a[0])).json()
    with Session(database_engine) as db:
        before = [
            [(str(r.id), r.updated_at) for r in db.scalars(select(cls))]
            for cls in (MemoryControlRow, MemoryRecordRow)
        ]
    grant, _, _, run = authorized(client, a, count, days)
    app.state.ica_mock_provider_factory = lambda: queue_empty(k)
    response = client.post(BASE + f"/runs/{run['run_id']}/execute", headers=headers(a[0]))
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "completed", result
    assert result["mock_calls"] == 2 * k + 2
    assert result["external_provider_calls"] == 0
    report = result["report"]
    assert report["outcome"] == "insufficient_evidence" and report["findings"] == []
    assert sum(w["message_count"] for w in report["coverage"]) == count
    assert len([r for r in result["receipts"] if r["stage"] == "safety"]) == k
    assert len([r for r in result["receipts"] if r["stage"] == "interaction"]) == k
    assert {r["status"] for r in result["receipts"] if r["stage"] == "counterevidence"} == {
        "not_applicable"
    }
    assert result["reserved_tokens"] <= result["execution"]["token_cap"]
    assert all(call["status"] == "succeeded" for call in result["ledger"])
    assert "好😀" not in json.dumps(result["ledger"], ensure_ascii=False)
    repeat = client.post(BASE + f"/runs/{run['run_id']}/execute", headers=headers(a[0]))
    assert repeat.json()["mock_calls"] == result["mock_calls"]
    assert client.get(BASE + f"/runs/{run['run_id']}", headers=headers(b[0])).status_code == 404
    assert client.get("/api/v1/memory/control", headers=headers(a[0])).json() == control
    with Session(database_engine) as db:
        after = [
            [(str(r.id), r.updated_at) for r in db.scalars(select(cls))]
            for cls in (MemoryControlRow, MemoryRecordRow)
        ]
        assert after == before
    from pathlib import Path

    evidence = Path("docs/evidence/ica-b1")
    evidence.mkdir(parents=True, exist_ok=True)
    # Anonymous outputs only. Never save a credential or challenge.
    (evidence / f"signed-demo-{count}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    revoke = client.post(BASE + f"/grants/{grant['grant_id']}/revoke", headers=headers(a[0]))
    assert revoke.status_code == 200
    assert client.get(BASE + f"/runs/{run['run_id']}", headers=headers(a[0])).status_code == 409


def test_execution_confirmation_is_explicit_isolated_and_idempotent(execution_api, database_engine):
    _, client, a, b = execution_api
    dataset = imported(client, a, 10)["dataset_job_id"]
    prep = preparation(client, a, dataset, model="mock").json()
    assert (
        client.post(
            BASE + "/execution-prepare",
            headers=headers(a[0]),
            json={"grant_id": prep["preparation_id"]},
        ).status_code
        == 409
    )
    grant = confirm(client, a, prep).json()
    pending = client.post(
        BASE + "/execution-prepare", headers=headers(a[0]), json={"grant_id": grant["grant_id"]}
    ).json()
    body = confirmation(pending)
    url = BASE + f"/runs/{pending['preparation_id']}/execute"
    assert client.post(url, headers=headers(a[0])).status_code == 409
    assert (
        client.post(BASE + "/execution-confirm", headers=headers(b[0]), json=body).status_code
        == 404
    )
    for changes, status in [
        ({"confirmed": 1}, 422),
        ({"confirmed": False}, 422),
        ({"challenge": "x" * 43}, 409),
        ({"binding_hash": "f" * 64}, 409),
    ]:
        response = client.post(
            BASE + "/execution-confirm", headers=headers(a[0]), json={**body, **changes}
        )
        assert response.status_code == status, response.text
    with ThreadPoolExecutor(2) as pool:
        results = list(
            pool.map(
                lambda _: client.post(
                    BASE + "/execution-confirm", headers=headers(a[0]), json=body
                ),
                range(2),
            )
        )
    assert [r.status_code for r in results] == [200, 200]
    assert results[0].json() == results[1].json()
    with Session(database_engine) as db, db.begin():
        row = db.get(ImportedAnalysisRun, UUID(pending["preparation_id"]))
        assert row.status == "authorized" and row.request_count == 0 and row.token_hash == ""


def test_expired_execution_challenge_and_source_change_reject(execution_api, database_engine):
    _, client, a, _ = execution_api
    _, pending, body, run = authorized(client, a)
    with Session(database_engine) as db, db.begin():
        row = db.get(ImportedAnalysisRun, UUID(run["run_id"]))
        row.status, row.operation_key, row.confirmation_hash = "prepared", None, None
        row.challenge_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert (
        client.post(BASE + "/execution-confirm", headers=headers(a[0]), json=body).status_code
        == 409
    )
    with Session(database_engine) as db, db.begin():
        msg = db.scalar(
            select(RelationshipMessage).where(RelationshipMessage.owner_user_id == a[0])
        )
        msg.content = "Anonymous source modified"
    assert (
        client.get(BASE + f"/runs/{pending['preparation_id']}", headers=headers(a[0])).status_code
        == 409
    )


def test_non_mock_disabled_empty_queue_and_budget_fail_closed(execution_api, database_engine):
    app, client, a, _ = execution_api
    dataset = imported(client, a, 10)["dataset_job_id"]
    grant = confirm(client, a, preparation(client, a, dataset).json()).json()
    assert (
        client.post(
            BASE + "/execution-prepare", headers=headers(a[0]), json={"grant_id": grant["grant_id"]}
        ).status_code
        == 409
    )
    _, _, _, run = authorized(client, a)
    app.state.settings.ica_mock_execution_enabled = False
    assert (
        client.post(BASE + f"/runs/{run['run_id']}/execute", headers=headers(a[0])).status_code
        == 409
    )
    app.state.settings.ica_mock_execution_enabled = True
    app.state.ica_mock_provider_factory = MockLLMProvider
    failed = client.post(BASE + f"/runs/{run['run_id']}/execute", headers=headers(a[0])).json()
    assert failed["status"] == "failed" and failed["report"] is None
    assert failed["mock_calls"] == 1
    assert (
        client.post(BASE + f"/runs/{run['run_id']}/execute", headers=headers(a[0])).json() == failed
    )
    _, _, _, run = authorized(client, a)
    with Session(database_engine) as db, db.begin():
        row = db.get(ImportedAnalysisRun, UUID(run["run_id"]))
        row.execution_binding = {**row.execution_binding, "token_cap": 1}
    app.state.ica_mock_provider_factory = lambda: queue_empty(1)
    failed = client.post(BASE + f"/runs/{run['run_id']}/execute", headers=headers(a[0])).json()
    assert failed["status"] == "failed" and failed["mock_calls"] == 0
    assert failed["error_code"] == "execution_budget_exceeded"


def test_concurrent_execution_and_revoke_before_output(execution_api, database_engine):
    app, client, a, _ = execution_api
    grant, _, _, run = authorized(client, a)
    entered, release = Event(), Event()

    class BlockingMock(MockLLMProvider):
        async def structured_output(self, *args, **kwargs):
            entered.set()
            await asyncio.to_thread(release.wait, 10)
            return await super().structured_output(*args, **kwargs)

    provider = queue_empty(1, BlockingMock())
    factories = []

    def factory():
        factories.append(1)
        return provider

    app.state.ica_mock_provider_factory = factory
    url = BASE + f"/runs/{run['run_id']}/execute"
    with ThreadPoolExecutor(2) as pool:
        active = pool.submit(client.post, url, headers=headers(a[0]))
        try:
            assert entered.wait(10)
            repeat = client.post(url, headers=headers(a[0]))
            assert repeat.status_code == 200 and repeat.json()["status"] == "running"
            assert len(factories) == 1
            assert (
                client.post(
                    BASE + f"/grants/{grant['grant_id']}/revoke", headers=headers(a[0])
                ).status_code
                == 200
            )
        finally:
            release.set()
        assert active.result(15).status_code == 409
    with Session(database_engine) as db:
        row = db.get(ImportedAnalysisRun, UUID(run["run_id"]))
        assert row.status == "revoked" and row.report is None and not row.writer_active
        assert row.request_count == 1 and row.execution_binding == {} and row.ledger == []


def test_signed_finding_references_current_source_and_review_rejects(
    execution_api, database_engine
):
    from pathlib import Path

    from test_ica_runtime import finding_provider

    app, client, a, _ = execution_api
    rows = [json.loads(line) for line in jsonl(2).decode().splitlines()]
    rows[-2]["content"], rows[-1]["content"] = "我很难过😀", "你应该早点安排"
    dataset = imported(client, a, content="\n".join(json.dumps(r) for r in rows).encode())[
        "dataset_job_id"
    ]
    grant = confirm(client, a, preparation(client, a, dataset, model="mock").json()).json()
    pending = client.post(
        BASE + "/execution-prepare", headers=headers(a[0]), json={"grant_id": grant["grant_id"]}
    ).json()
    run = client.post(
        BASE + "/execution-confirm", headers=headers(a[0]), json=confirmation(pending)
    ).json()
    service = ImportedAnalysisService(lambda: Session(database_engine))
    actor = actor_from_verified_identity(a[0])
    with service.transaction(actor) as db:
        ctx = service.current(db, actor, db.get(ImportedAnalysisGrant, UUID(grant["grant_id"])))[0]
    app.state.ica_mock_provider_factory = lambda: finding_provider(ctx)
    result = client.post(BASE + f"/runs/{run['run_id']}/execute", headers=headers(a[0])).json()
    assert result["status"] == "completed" and result["mock_calls"] == 5, result
    assert result["report"]["outcome"] == "findings"
    aliases = result["report"]["source"]["aliases"]
    assert len(aliases) == 2
    for ref in result["report"]["findings"][0]["facts"][0]["evidence"]:
        response = client.post(
            BASE + f"/grants/{grant['grant_id']}/evidence/{ref['evidence_id']}",
            headers=headers(a[0]),
            json={k: ref[k] for k in ("start", "end", "quote")},
        )
        assert response.status_code == 200 and response.json()["quote"] == ref["quote"]
        assert response.json()["message_id"] == aliases[ref["evidence_id"]]["message_id"]
    Path("docs/evidence/ica-b1/signed-finding.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    pending = client.post(
        BASE + "/execution-prepare", headers=headers(a[0]), json={"grant_id": grant["grant_id"]}
    ).json()
    run = client.post(
        BASE + "/execution-confirm", headers=headers(a[0]), json=confirmation(pending)
    ).json()
    app.state.ica_mock_provider_factory = lambda: finding_provider(
        ctx,
        review={
            **REVIEW,
            "approved": False,
            "reason_codes": ["unsupported"],
        },
    )
    rejected = client.post(BASE + f"/runs/{run['run_id']}/execute", headers=headers(a[0])).json()
    assert rejected["status"] == "failed" and rejected["report"] is None
    assert rejected["error_code"] == "content_review_rejected"


def test_known_oversized_serialized_input_rejected_before_confirmation(execution_api):
    _, client, a, _ = execution_api
    rows = [json.loads(line) for line in jsonl(2).decode().splitlines()]
    rows[-2]["content"] = "😀" * 12000
    raw = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows).encode()
    dataset = imported(client, a, content=raw)["dataset_job_id"]
    grant = confirm(client, a, preparation(client, a, dataset, model="mock").json()).json()
    response = client.post(
        BASE + "/execution-prepare", headers=headers(a[0]), json={"grant_id": grant["grant_id"]}
    )
    assert (
        response.status_code == 409
        and response.json()["error"]["code"] == "scope_or_budget_rejected"
    )
