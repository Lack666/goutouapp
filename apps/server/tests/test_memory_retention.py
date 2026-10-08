"""Phase 6C deterministic clocks, real PostgreSQL, runtime and maintenance gates."""

import asyncio
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from memory_control_demo import disposable_database, run_agent
from pydantic import ValidationError
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from test_memory_control import _app, _headers, _save, _scope

from app.agent.contracts import MemoryControl, MemoryDecision, MemoryRecord
from app.agent.memory import InMemoryMemoryStore, MemoryService
from app.core.config import Settings
from app.db.models import (
    MemoryConfirmationRow,
    MemoryMutationRow,
    MemoryOperationRow,
    MemoryRecordRow,
)
from app.db.repositories.memory import SQLAlchemyMemoryStore
from app.retention import RetentionPolicy, as_utc
from app.services.agent_service import actor_from_verified_identity
from app.services.memory_mutation import MemoryMutationError, MemoryMutationService
from app.services.memory_retention import MemoryRetentionService

NOW = datetime.now(UTC)


@pytest.mark.parametrize("offset,expected", [(-1, 1), (0, 0), (1, 0)])
def test_standalone_service_filters_expiry_without_sql(offset, expected):
    owner, record_id = uuid4(), uuid4()
    store = InMemoryMemoryStore()
    store.set_control(owner, MemoryControl(consent_enabled=True))
    store.save_record(
        MemoryRecord(
            id=record_id,
            owner_user_id=owner,
            subject_id=owner,
            type="user",
            content="Synthetic stable preference",
            source="user_explicit",
            evidence="F1",
            created_at=NOW - timedelta(days=1),
            updated_at=NOW - timedelta(days=1),
            expires_at=NOW,
        )
    )
    memory = MemoryService(store, clock=lambda: NOW + timedelta(microseconds=offset))
    assert len(memory.load_for_context(owner, None, enabled=True)) == expected
    assert record_id in store.records  # Expiration filtering has no delete side effect.


@pytest.fixture
def scope(database_engine):
    # Each test owns fresh user/scopes; drain expired synthetic leftovers first.
    MemoryRetentionService(lambda: Session(database_engine)).run(dry_run=False, max_batches=100)
    owner, outsider, person, other_person, rel, other_rel, conversation = _scope(database_engine)
    store = SQLAlchemyMemoryStore(lambda: Session(database_engine), clock=lambda: NOW)
    _save(store, owner, person, rel, "我们计划第一周见面")
    record = store.list_records(owner)[0]
    return (
        database_engine,
        store,
        owner,
        outsider,
        person,
        other_person,
        rel,
        other_rel,
        conversation,
        record,
    )


def retention(engine, now=NOW, policy=None):
    return MemoryRetentionService(lambda: Session(engine), clock=lambda: now, policy=policy)


def expire(engine, record_id, when=NOW):
    with Session(engine) as db, db.begin():
        db.get(MemoryRecordRow, record_id).expires_at = when


def test_policy_contract_and_invalid_configuration():
    policy = RetentionPolicy.from_settings(Settings(_env_file=None))
    assert policy.active_days == 180 and policy.challenge_grace_hours == 24
    assert policy.batch_size == 100 and policy.receipt_retention == "durable_owner_lifetime"
    for name in (
        "memory_retention_days",
        "memory_challenge_cleanup_grace_hours",
        "memory_cleanup_batch_size",
    ):
        for bad in (-1, 0, True, 1.5, "invalid"):
            with pytest.raises(ValidationError):
                Settings(_env_file=None, **{name: bad})
    with pytest.raises(ValueError):
        as_utc(datetime(2026, 1, 1))


def test_settings_environment_units(monkeypatch):
    monkeypatch.setenv("MEMORY_RETENTION_DAYS", "7")
    monkeypatch.setenv("MEMORY_CHALLENGE_CLEANUP_GRACE_HOURS", "2")
    monkeypatch.setenv("MEMORY_CLEANUP_BATCH_SIZE", "3")
    policy = RetentionPolicy.from_settings(Settings(_env_file=None))
    assert (policy.active_days, policy.challenge_grace_hours, policy.batch_size) == (7, 2, 3)


@pytest.mark.parametrize("case_id", ["memory_retention_active_01", "memory_retention_expired_01"])
def test_golden_retention_actual_agent_recall(scope, case_id):
    from evals.validate import load_cases

    case = next(item for item in load_cases() if item["id"] == case_id)
    fixture = case["retention_fixture"]
    engine, store, owner, _, person, _, rel, _, conv, record = scope
    expire(engine, record.id, NOW + timedelta(seconds=fixture["expires_in_seconds"]))
    assert (
        asyncio.run(run_agent(engine, owner, person, rel, conv, store, save=False))[1]
        == fixture["expected_recall_count"]
    )


def test_process_interruption_rolls_back_uncommitted_cleanup(scope):
    engine, store, owner, _, _, _, _, _, _, record = scope
    expire(engine, record.id)
    env = os.environ.copy()
    env["RETENTION_TEST_URL"] = engine.url.render_as_string(hide_password=False)
    env["RETENTION_TEST_ID"] = str(record.id)
    code = (
        "import os; from sqlalchemy import create_engine, text; "
        "db=create_engine(os.environ['RETENTION_TEST_URL']).connect(); "
        "tx=db.begin(); db.execute(text('DELETE FROM memory_records WHERE id=:id'), "
        "{'id':os.environ['RETENTION_TEST_ID']}); os._exit(17)"
    )
    exited = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True)
    assert exited.returncode == 17
    assert store.get_record(owner, record.id) is not None
    assert retention(engine).run(dry_run=False).counts.memory_records == 1


def test_cleanup_concurrent_save_control_and_user_delete(scope):
    engine, store, owner, _, person, _, rel, _, _, expired = scope
    expire(engine, expired.id)
    actor = actor_from_verified_identity(owner)
    mutations = MemoryMutationService(lambda: Session(engine), clock=lambda: NOW)
    challenge = mutations.prepare_delete_all(actor, revoke_consent_after_delete=False)

    def delete():
        try:
            return mutations.execute_delete(
                actor,
                confirmation_id=challenge.confirmation_id,
                operation_key="cleanup-race-delete",
            )
        except MemoryMutationError as error:
            return error.code.value

    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = [
            pool.submit(retention(engine).run, dry_run=False),
            pool.submit(_save, store, owner, person, rel, "我们计划第四周见面"),
            pool.submit(store.change_control, owner, "revoke"),
            pool.submit(delete),
        ]
        outcomes = [job.result() for job in jobs]
    assert outcomes[0].status == "ok"
    assert store.get_record(owner, expired.id) is None
    assert outcomes[1].status.value in {"saved", "skipped_no_consent", "skipped_paused"}
    assert outcomes[3] == "confirmation_stale" or outcomes[3].status == "deleted"
    assert store.get_control(owner).paused  # Revoke completes; cleanup never resumes it.


@pytest.mark.parametrize("offset,expected", [(-1, 1), (0, 0), (1, 0)])
def test_query_expiration_before_at_after(scope, offset, expected):
    engine, _, owner, _, _, _, rel, _, _, record = scope
    expire(engine, record.id)

    def clock():
        return NOW + timedelta(microseconds=offset)

    store = SQLAlchemyMemoryStore(lambda: Session(engine), clock=clock)
    assert len(store.list_records(owner)) == expected
    assert len(MemoryService(store).load_for_context(owner, rel, enabled=True)) == expected
    assert store.get_record(owner, record.id) is not None  # No cleanup required.


def test_configuration_is_prospective_and_recall_does_not_extend(scope):
    engine, store, owner, _, person, _, rel, _, _, record = scope
    changed = SQLAlchemyMemoryStore(
        lambda: Session(engine), policy=RetentionPolicy(active_days=7), clock=lambda: NOW
    )
    _save(changed, owner, person, rel, "我们计划第二周见面")
    assert next(
        r for r in changed.list_records(owner) if r.content == "我们计划第二周见面"
    ).expires_at == NOW + timedelta(days=7)
    MemoryService(store).load_for_context(owner, rel, enabled=True)
    assert store.get_record(owner, record.id).expires_at == record.expires_at


def test_inspect_http_expired_state_owner_and_default_list(scope):
    engine, store, owner, outsider, _, _, _, _, _, record = scope
    expire(engine, record.id, NOW - timedelta(seconds=1))
    with TestClient(_app(engine)) as client:
        active = client.get("/api/v1/memories", headers=_headers(owner)).json()
        assert active["items"] == [] and "180 days" in active["retention_policy_summary"]
        view = client.get(f"/api/v1/memories/{record.id}", headers=_headers(owner)).json()
        assert view["state"] == "expired" and view["expires_at"] and view["created_at"]
        assert (
            client.get(f"/api/v1/memories/{record.id}", headers=_headers(outsider)).status_code
            == 404
        )
        assert (
            client.post("/api/v1/memory/retention/cleanup", headers=_headers(owner)).status_code
            == 404
        )
    assert store.get_record(owner, record.id) is not None


def test_runtime_scope_pause_revoke_and_expiry(scope):
    engine, store, owner, outsider, person, other_person, rel, other_rel, conv, record = scope
    _save(store, owner, person, rel, "我们计划第二周见面")
    _save(store, owner, other_person, other_rel, "我们计划第三周见面")
    expire(engine, record.id)
    assert asyncio.run(run_agent(engine, owner, person, rel, conv, store, save=False))[1] == 1
    memory = MemoryService(store)
    assert memory.load_for_context(outsider, rel, enabled=True) == []
    assert len(memory.load_for_context(owner, other_rel, enabled=True)) == 1
    for decision in (MemoryDecision.PAUSE, MemoryDecision.REVOKE_KEEP):
        memory.apply_control(owner, decision)
        assert asyncio.run(run_agent(engine, owner, person, rel, conv, store, save=False))[1] == 0
        memory.grant_consent(owner, confirmed=True)
        memory.apply_control(owner, MemoryDecision.RESUME)
        assert len(memory.load_for_context(owner, rel, enabled=True)) == 1
    retention(engine).run(dry_run=False)
    assert store.get_record(owner, record.id) is None


def test_dry_run_bounded_batches_idempotency_and_controls(scope):
    engine, store, owner, _, person, _, rel, _, _, record = scope
    _save(store, owner, person, rel, "我们计划第二周见面")
    ids = [r.id for r in store.list_records(owner)]
    for record_id in ids:
        expire(engine, record_id)
    control = store.get_control(owner)
    before = retention(engine).run()
    assert before.counts.memory_records == before.counts.undo_operations == 2
    assert all(store.get_record(owner, r) is not None for r in ids)
    first = retention(engine).run(dry_run=False, batch_size=1)
    assert first.counts.memory_records == first.counts.undo_operations == 1
    second = retention(engine).run(dry_run=False, batch_size=1, max_batches=3)
    assert second.counts.memory_records == 1
    assert retention(engine).run(dry_run=False).counts.memory_records == 0
    assert store.get_control(owner) == control


def test_transaction_rollback_and_partial_batch_recovery(scope, monkeypatch):
    engine, store, owner, _, person, _, rel, _, _, record = scope
    _save(store, owner, person, rel, "我们计划第二周见面")
    ids = [r.id for r in store.list_records(owner)]
    for item in ids:
        expire(engine, item)
    service = retention(engine)
    original = service._delete_batch
    calls = 0

    def failing(db, now, size):
        nonlocal calls
        counts = original(db, now, size)
        calls += 1
        if calls == 2:
            # Actual PostgreSQL error aborts this transaction after deletes.
            db.execute(text("SELECT 1 / 0"))
        return counts

    monkeypatch.setattr(service, "_delete_batch", failing)
    result = service.run(dry_run=False, batch_size=1, max_batches=3)
    assert result.status == "failed" and result.batches_committed == 1
    assert result.counts.memory_records == 1 and result.error == "retention_cleanup_failed"
    assert sum(store.get_record(owner, r) is not None for r in ids) == 1
    retry = retention(engine).run(dry_run=False)
    assert retry.counts.memory_records == retry.counts.undo_operations == 1


def test_concurrent_cleanup_exactly_one_removal(scope):
    engine, store, owner, _, _, _, _, _, _, record = scope
    expire(engine, record.id)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: retention(engine).run(dry_run=False), range(2)))
    assert all(r.status == "ok" for r in results)
    assert sum(r.counts.memory_records for r in results) == 1
    assert sum(r.counts.undo_operations for r in results) == 1


@pytest.mark.parametrize("concurrent", [False, True])
def test_expired_undo_never_falls_back_to_older_target(scope, concurrent):
    engine, store, owner, _, person, _, rel, _, _, older = scope
    store.clock = lambda: NOW + timedelta(microseconds=1)
    _save(store, owner, person, rel, "我们计划第二周见面")
    actor = actor_from_verified_identity(owner)
    mutations = MemoryMutationService(lambda: Session(engine), clock=lambda: NOW)
    preview = mutations.preview_undo(actor)
    expire(engine, preview.memory_id)

    def undo():
        try:
            return mutations.undo(
                actor,
                expected_operation_id=preview.latest_operation_id,
                operation_key="expiry-undo",
            )
        except MemoryMutationError as error:
            return error.code.value

    if concurrent:
        with ThreadPoolExecutor(max_workers=2) as pool:
            cleanup_future, undo_future = (
                pool.submit(retention(engine).run, dry_run=False),
                pool.submit(undo),
            )
            assert cleanup_future.result().status == "ok"
            result = undo_future.result()
    else:
        retention(engine).run(dry_run=False)
        result = undo()
    assert result in ("stale_undo", "undo_unavailable")
    assert store.get_record(owner, older.id) is not None
    with Session(engine) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(MemoryMutationRow)
                .where(MemoryMutationRow.owner_user_id == owner)
            )
            == 0
        )
        assert (
            db.scalar(
                select(MemoryOperationRow.id).where(
                    MemoryOperationRow.record_id == preview.memory_id
                )
            )
            is None
        )


def test_challenge_grace_boundary_and_receipt_replay(scope):
    engine, store, owner, _, _, _, _, _, _, record = scope
    actor = actor_from_verified_identity(owner)
    service = MemoryMutationService(lambda: Session(engine), clock=lambda: NOW)
    consumed = service.prepare_delete_all(actor, revoke_consent_after_delete=False)
    receipt = service.execute_delete(
        actor, confirmation_id=consumed.confirmation_id, operation_key="durable-delete"
    )
    pending = service.prepare_delete_all(actor, revoke_consent_after_delete=False)
    cutoff = consumed.expires_at + timedelta(hours=24)
    before = retention(engine, cutoff - timedelta(microseconds=1)).run(dry_run=False)
    assert before.counts.confirmation_challenges == 0
    at = retention(engine, cutoff).run(dry_run=False)
    assert at.counts.confirmation_challenges >= 2
    with Session(engine) as db:
        assert db.get(MemoryConfirmationRow, consumed.confirmation_id) is None
        assert db.get(MemoryConfirmationRow, pending.confirmation_id) is None
    retry = service.execute_delete(
        actor, confirmation_id=consumed.confirmation_id, operation_key="durable-delete"
    )
    assert retry.replayed and retry.mutation_id == receipt.mutation_id
    with pytest.raises(MemoryMutationError, match="mutation_conflict"):
        service.execute_delete(
            actor, confirmation_id=pending.confirmation_id, operation_key="durable-delete"
        )
    with pytest.raises(MemoryMutationError, match="confirmation_required"):
        service.execute_delete(
            actor, confirmation_id=consumed.confirmation_id, operation_key="new-key"
        )
    far_future = retention(engine, NOW + timedelta(days=3650)).run(dry_run=False)
    assert far_future.counts.mutation_receipts_removed == 0
    assert service.inspect_receipt(actor, receipt.mutation_id).mutation_id == receipt.mutation_id


def test_valid_challenge_preserved_and_expiration_boundary(scope):
    engine, _, owner, *_ = scope
    actor = actor_from_verified_identity(owner)
    service = MemoryMutationService(lambda: Session(engine), clock=lambda: NOW)
    challenge = service.prepare_delete_all(actor, revoke_consent_after_delete=False)
    retention(engine, challenge.expires_at - timedelta(microseconds=1)).run(dry_run=False)
    with Session(engine) as db:
        assert db.get(MemoryConfirmationRow, challenge.confirmation_id) is not None
    expired = MemoryMutationService(lambda: Session(engine), clock=lambda: challenge.expires_at)
    with pytest.raises(MemoryMutationError, match="confirmation_expired"):
        expired.execute_delete(
            actor, confirmation_id=challenge.confirmation_id, operation_key="expired-key"
        )


def test_same_key_undo_retry_concurrent_maintenance(scope):
    engine, store, owner, _, _, _, _, _, _, older = scope
    actor = actor_from_verified_identity(owner)
    mutations = MemoryMutationService(lambda: Session(engine), clock=lambda: NOW)
    preview = mutations.preview_undo(actor)
    receipt = mutations.undo(
        actor, expected_operation_id=preview.latest_operation_id, operation_key="durable-undo"
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        maintenance = pool.submit(retention(engine, NOW + timedelta(days=3650)).run, dry_run=False)
        retry = pool.submit(
            mutations.undo,
            actor,
            expected_operation_id=preview.latest_operation_id,
            operation_key="durable-undo",
        )
        assert maintenance.result().status == "ok"
        assert retry.result().mutation_id == receipt.mutation_id
    with pytest.raises(MemoryMutationError, match="mutation_conflict"):
        mutations.undo(actor, expected_operation_id=uuid4(), operation_key="durable-undo")


def test_existing_records_migration_receives_full_legacy_grace():
    with disposable_database() as engine:
        config = Config("alembic.ini")
        config.attributes["database_url"] = engine.url.render_as_string(hide_password=False)
        command.downgrade(config, "20260929_01")
        owner, record = uuid4(), uuid4()
        with engine.begin() as db:
            db.execute(text("INSERT INTO users (id) VALUES (:id)"), {"id": owner})
            db.execute(
                text(
                    "INSERT INTO memory_records (id, owner_user_id, subject_id, type, content, "
                    "content_hash, source, evidence, first_run_id, created_at, updated_at) "
                    "VALUES (:id, :owner, :owner, 'user', 'Synthetic legacy preference', "
                    ":hash, 'user_explicit', 'F1', :run, '2000-01-01 UTC', '2000-01-01 UTC')"
                ),
                {"id": record, "owner": owner, "hash": "1" * 64, "run": uuid4()},
            )
        start = datetime.now(UTC)
        command.upgrade(config, "head")
        with Session(engine) as db:
            legacy = db.get(MemoryRecordRow, record)
            assert (
                start + timedelta(days=180)
                <= legacy.expires_at
                <= datetime.now(UTC) + timedelta(days=180)
            )
            assert legacy.created_at.year == 2000
        assert retention(engine).run().counts.memory_records == 0


def test_cli_dry_execute_privacy_and_generic_error(scope):
    engine, store, owner, _, _, _, _, _, _, record = scope
    expire(engine, record.id, NOW - timedelta(seconds=1))
    env = os.environ.copy()
    env["DATABASE_URL"] = engine.url.render_as_string(hide_password=False)
    for mode in ("--dry-run", "--execute"):
        completed = subprocess.run(
            [sys.executable, "apps/server/cleanup_memory_retention.py", mode, "--batch-size", "1"],
            env=env,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0
        result = json.loads(completed.stdout)
        assert result["status"] == "ok" and result["counts"]["memory_records"] == 1
        assert record.content not in completed.stdout + completed.stderr
        assert env["DATABASE_URL"] not in completed.stdout + completed.stderr
    invalid = subprocess.run(
        [
            sys.executable,
            "apps/server/cleanup_memory_retention.py",
            "--execute",
            "--batch-size",
            "0",
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    assert (
        invalid.returncode == 1
        and json.loads(invalid.stdout)["error"] == "retention_cleanup_failed"
    )


def test_policy_backup_documentation_consistency():
    root = Path(__file__).resolve().parents[3]
    policy = (root / "docs/MEMORY_RETENTION.md").read_text(encoding="utf-8")
    backup = (root / "docs/MEMORY_BACKUP_DELETION_POLICY.md").read_text(encoding="utf-8")
    assert (
        "180" in policy and "durable" in policy and "AUTOMATIC SCHEDULING: NOT DEPLOYED" in policy
    )
    assert "NOT DEPLOYED" in backup and "restore" in backup and "35 days" in backup
