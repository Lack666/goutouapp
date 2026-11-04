"""Signed lifecycle and native restore of synthetic ICA execution privacy canaries."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
import test_ica_signed as ica_fixtures
from sqlalchemy import delete
from sqlalchemy.orm import Session
from test_agent_rest import headers
from test_ica_signed import BASE, confirm, imported, preparation

from app.db.models import ImportedAnalysisGrant, ImportedAnalysisRun
from app.schemas.lifecycle import LifecycleExecute, LifecycleTarget
from app.services.agent_service import actor_from_verified_identity
from app.services.agent_writer import AgentWriterRegistry
from app.services.backup_restore import RecoveryError, dump_synthetic, restore_synthetic
from app.services.erasure import ErasureError
from app.services.imported_analysis import ImportedAnalysisService
from app.services.lifecycle_erasure import LifecycleErasure

api = ica_fixtures.api


@pytest.fixture(name="database_engine")
def isolated_recovery_engine(recovery_database_engine):
    return recovery_database_engine


def seeded_run(api, engine, who, *, dataset=None, active=False):
    """Seed derived private canaries; actual execution is tested in the service suite."""
    _, client, _, _ = api
    dataset = dataset or imported(client, who, 10)["dataset_job_id"]
    grant = confirm(client, who, preparation(client, who, dataset).json()).json()
    with Session(engine) as db, db.begin():
        authority = db.get(ImportedAnalysisGrant, UUID(grant["grant_id"]))
        run = ImportedAnalysisRun(
            owner_user_id=who[0],
            person_id=who[1],
            relationship_id=who[2],
            dataset_id=UUID(dataset),
            grant_id=authority.id,
            status="running" if active else "completed",
            operation_key=uuid4().hex,
            confirmation_hash="c" * 64,
            token_hash="t" * 64,
            binding_hash="b" * 64,
            expires_at=authority.expires_at,
            challenge_expires_at=datetime.now(UTC) + timedelta(minutes=5),
            execution_binding={"private_canary": "synthetic execution context"},
            report={"private_canary": "synthetic derived relationship observation"},
            receipts=[{"private_canary": "synthetic extracted interaction"}],
            ledger=[{"input_hash": "a" * 64, "status": "sent"}],
            request_count=1,
            reserved_tokens=100,
            writer_token="w" * 64 if active else None,
            writer_active=active,
        )
        db.add(run)
        db.flush()
        return run.id, run.grant_id, dataset, run.operation_key


def owner_erasure(api):
    app = api[0]
    return LifecycleErasure(
        app.state.database.session,
        app.state.import_artifact_store,
        AgentWriterRegistry(app.state.settings.chat_import_artifact_root),
    )


def erase(api, who, dataset, domain, *, busy=False):
    _, client, _, _ = api
    if domain == "owner":
        service = owner_erasure(api)
        actor = actor_from_verified_identity(who[0])
        target = LifecycleTarget(domain="owner", target_id=who[0])
        if busy:
            with pytest.raises(ErasureError, match="target_busy"):
                service.prepare(actor, target)
            return
        challenge = service.prepare(actor, target)
        body = LifecycleExecute(
            **target.model_dump(),
            confirmation_id=challenge.confirmation_id,
            operation_key=uuid4().hex,
        )
        receipt = service.execute(actor, body)
        assert service.execute(actor, body) == receipt
        return
    if domain == "dataset":
        route = "/api/v1/erasures"
        target = {"domain": domain, "target_id": dataset, "relationship_id": str(who[2])}
    else:
        route = "/api/v1/lifecycle-erasures"
        target = {"domain": domain, "target_id": str(who[1] if domain == "person" else who[2])}
    challenge = client.post(route + "/prepare", headers=headers(who[0]), json=target)
    if busy:
        assert challenge.status_code == 409 and "target_busy" in challenge.text
        return
    assert challenge.status_code == 200, challenge.text
    body = {
        **target,
        "confirmation_id": challenge.json()["confirmation_id"],
        "operation_key": uuid4().hex,
    }
    response = client.post(route + "/execute", headers=headers(who[0]), json=body)
    assert response.status_code == 200, response.text
    assert (
        client.post(route + "/execute", headers=headers(who[0]), json=body).json()
        == response.json()
    )


def assert_cleared(engine, record, status, *, active=False):
    rid, gid, _, key = record
    with Session(engine) as db:
        run = db.get(ImportedAnalysisRun, rid)
        assert run.status == status
        assert run.report is None and run.receipts == [] and run.execution_binding == {}
        assert run.ledger == []
        assert run.token_hash == "" and run.writer_token is None
        assert run.writer_active is active
        assert run.operation_key == key and run.confirmation_hash == "c" * 64
        assert run.request_count == 1 and run.reserved_tokens == 100
        assert db.get(ImportedAnalysisGrant, gid).payload == {}


@pytest.mark.parametrize("domain", ["dataset", "person", "relationship", "owner"])
def test_deletion_clears_derived_data_and_keeps_other_owner(api, database_engine, domain):
    _, client, a, b = api
    record = seeded_run(api, database_engine, a)
    other = seeded_run(api, database_engine, b)
    erase(api, a, record[2], domain)
    assert_cleared(database_engine, record, "deleted")
    with Session(database_engine) as db:
        assert db.get(ImportedAnalysisRun, other[0]).report is not None
    assert client.get(BASE + f"/grants/{record[1]}", headers=headers(a[0])).status_code in (
        401,
        409,
    )


@pytest.mark.parametrize("domain", ["dataset", "person", "relationship", "owner"])
def test_revoked_live_writer_still_blocks_deletion_until_settled(api, database_engine, domain):
    _, client, a, _ = api
    record = seeded_run(api, database_engine, a, active=True)
    erase(api, a, record[2], domain, busy=True)
    assert (
        client.post(BASE + f"/grants/{record[1]}/revoke", headers=headers(a[0])).status_code == 200
    )
    assert_cleared(database_engine, record, "revoked", active=True)
    erase(api, a, record[2], domain, busy=True)
    # The real executor's finally block performs this settlement; a cleared token does not.
    with Session(database_engine) as db, db.begin():
        db.get(ImportedAnalysisRun, record[0]).writer_active = False
    erase(api, a, record[2], domain)
    assert_cleared(database_engine, record, "deleted")


def test_expiry_cleanup_concurrent_idempotent_and_preserves_writer_proof(api, database_engine):
    _, client, a, _ = api
    record = seeded_run(api, database_engine, a, active=True)
    with Session(database_engine) as db, db.begin():
        expired = datetime.now(UTC) - timedelta(seconds=1)
        db.get(ImportedAnalysisGrant, record[1]).expires_at = expired
        db.get(ImportedAnalysisRun, record[0]).expires_at = expired
    service = ImportedAnalysisService(lambda: Session(database_engine))
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: service.cleanup(), range(2)))
    assert_cleared(database_engine, record, "expired", active=True)
    assert client.get(BASE + f"/grants/{record[1]}", headers=headers(a[0])).status_code == 409


@pytest.mark.parametrize("domain", ["dataset", "person"])
def test_writer_start_after_delete_preview_blocks_execution(api, database_engine, domain):
    _, client, a, _ = api
    record = seeded_run(api, database_engine, a)
    if domain == "dataset":
        route = "/api/v1/erasures"
        target = {"domain": domain, "target_id": record[2], "relationship_id": str(a[2])}
    else:
        route = "/api/v1/lifecycle-erasures"
        target = {"domain": domain, "target_id": str(a[1])}
    challenge = client.post(route + "/prepare", headers=headers(a[0]), json=target)
    assert challenge.status_code == 200, challenge.text
    with Session(database_engine) as db, db.begin():
        row = db.get(ImportedAnalysisRun, record[0])
        row.writer_active, row.writer_token = True, "w" * 64
    response = client.post(
        route + "/execute",
        headers=headers(a[0]),
        json={
            **target,
            "confirmation_id": challenge.json()["confirmation_id"],
            "operation_key": uuid4().hex,
        },
    )
    assert response.status_code == 409 and "target_busy" in response.text
    with Session(database_engine) as db:
        assert db.get(ImportedAnalysisRun, record[0]).report is not None
        assert db.get(ImportedAnalysisGrant, record[1]).payload != {}


def test_native_restore_clears_reports_and_preserves_post_archive_operation_keys(
    api, database_engine, tmp_path
):
    _, client, a, _ = api
    before = seeded_run(api, database_engine, a)
    archive = tmp_path / "ica-execution.dump"
    dump_synthetic(database_engine, archive)
    after = seeded_run(api, database_engine, a, dataset=before[2])
    assert (
        client.post(BASE + f"/grants/{before[1]}/revoke", headers=headers(a[0])).status_code == 200
    )
    root = tmp_path / "restored"
    root.mkdir()
    with restore_synthetic(database_engine, archive, root) as quarantine:
        assert not quarantine.released
        restored = quarantine.reconcile()
        for record in (before, after):
            assert_cleared(restored, record, "restore_invalid")


@pytest.mark.parametrize("revoked", [False, True])
def test_restore_refuses_current_active_executor_even_after_revocation(
    api, database_engine, tmp_path, revoked
):
    _, client, a, _ = api
    record = seeded_run(api, database_engine, a, active=True)
    archive = tmp_path / "ica-live.dump"
    dump_synthetic(database_engine, archive)
    if revoked:
        assert (
            client.post(BASE + f"/grants/{record[1]}/revoke", headers=headers(a[0])).status_code
            == 200
        )
    root = tmp_path / "restored"
    root.mkdir()
    with restore_synthetic(database_engine, archive, root) as quarantine:
        with pytest.raises(RecoveryError):
            quarantine.reconcile()
        assert not quarantine.released


def test_restore_refuses_missing_current_operation_fence(api, database_engine, tmp_path):
    _, _, a, _ = api
    record = seeded_run(api, database_engine, a)
    archive = tmp_path / "ica-missing-fence.dump"
    dump_synthetic(database_engine, archive)
    with Session(database_engine) as db, db.begin():
        db.execute(delete(ImportedAnalysisRun).where(ImportedAnalysisRun.id == record[0]))
    root = tmp_path / "restored"
    root.mkdir()
    with restore_synthetic(database_engine, archive, root) as quarantine:
        with pytest.raises(RecoveryError):
            quarantine.reconcile()
        assert not quarantine.released
