"""Actual pg_dump/pg_restore: frozen primary authority, never deletion inference."""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_agent_rest import headers, settings
from test_backup_restore import backup_snapshot
from test_erasure import erasure_api as legacy_erasure_api  # noqa: F401
from test_full_erasure_9h import (
    BASE,  # noqa: F401
    execution,
    full_erasure_api,  # noqa: F401
    preparation,
)

from app.chat_import.artifacts import LocalFilesystemImportArtifactStore
from app.db.models import (
    AgentRun,
    LifecycleConfirmation,
    LifecycleReceipt,
    MemoryRecordRow,
    Person,
    Relationship,
    User,
)
from app.main import create_app
from app.schemas.lifecycle import LifecycleExecute, LifecycleTarget
from app.services.agent_service import actor_from_verified_identity
from app.services.agent_writer import AgentWriterRegistry
from app.services.backup_restore import RecoveryError, dump_synthetic, restore_synthetic
from app.services.lifecycle_erasure import LifecycleErasure


@pytest.fixture(name="database_engine")
def isolated_recovery_engine(recovery_database_engine):
    return recovery_database_engine


@pytest.mark.parametrize("domain", ["person", "relationship", "owner"])
@pytest.mark.parametrize("timing", ["before", "after", "concurrent_snapshot"])
def test_real_archives_preserve_full_erasure_terminal_identity_and_receipts(
    full_erasure_api,  # noqa: F811
    domain,
    timing,
):
    engine, client, a, b, _, temp, config = full_erasure_api
    actor = actor_from_verified_identity(a[0])
    service = LifecycleErasure(
        lambda: Session(engine),
        LocalFilesystemImportArtifactStore(config.chat_import_artifact_root),
        AgentWriterRegistry(config.chat_import_artifact_root),
    )
    if domain == "owner":
        target = LifecycleTarget(domain=domain, target_id=a[0])
        confirmation = service.prepare(actor, target)
        body = LifecycleExecute(
            **target.model_dump(),
            confirmation_id=confirmation.confirmation_id,
            operation_key=uuid4().hex,
        ).model_dump(mode="json")
    else:
        body = preparation(full_erasure_api, domain)

    def erase():
        if domain == "owner":
            return service.execute(actor, LifecycleExecute(**body)).model_dump(mode="json")
        response = execution(full_erasure_api, body)
        assert response.status_code == 200, response.text
        return response.json()

    archive = temp / "full-synthetic.dump"
    if timing == "before":
        receipt = erase()
        dump_synthetic(engine, archive)
    elif timing == "after":
        dump_synthetic(engine, archive)
        receipt = erase()
    else:
        with backup_snapshot(engine) as snapshot:
            receipt = erase()
            dump_synthetic(engine, archive, snapshot=snapshot)
    root = temp / "restored-empty"
    root.mkdir()
    try:
        with restore_synthetic(engine, archive, root) as quarantine:
            assert not quarantine.released
            restored = quarantine.reconcile()
            with Session(restored) as db:
                assert db.get(Relationship, a[2]).deleted_at
                assert db.get(Relationship, b[2]).deleted_at is None
                assert bool(db.get(Person, a[1]).deleted_at) == (domain != "relationship")
                assert bool(db.get(User, a[0]).deleted_at) == (domain == "owner")
                assert db.get(LifecycleReceipt, UUID(receipt["receipt_id"])) is not None
                assert db.scalar(select(func.count()).select_from(LifecycleConfirmation)) == 0
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(MemoryRecordRow)
                        .where(MemoryRecordRow.relationship_id == a[2])
                    )
                    == 0
                )
            restored_service = LifecycleErasure(
                lambda: Session(restored),
                LocalFilesystemImportArtifactStore(root),
                AgentWriterRegistry(root),
            )
            assert (
                restored_service.execute(actor, LifecycleExecute(**body)).model_dump(mode="json")
                == receipt
            )
            with TestClient(create_app(settings(restored, chat_import_artifact_root=root))) as api:
                assert api.get("/api/v1/persons", headers=headers(b[0])).status_code == 200
                if domain == "owner":
                    assert api.get("/api/v1/persons", headers=headers(a[0])).status_code == 401
                else:
                    assert (
                        api.post(BASE + "/execute", headers=headers(a[0]), json=body).json()
                        == receipt
                    )
            assert quarantine.reconcile() == restored
    finally:
        archive.unlink(missing_ok=True)


def test_bare_recovered_flag_without_receipt_never_releases_backup_or_erasure(full_erasure_api):  # noqa: F811
    from datetime import UTC, datetime

    engine, client, a, _, _, temp, config = full_erasure_api
    archive = temp / "proof-missing.dump"
    dump_synthetic(engine, archive)
    with Session(engine) as db, db.begin():
        run = db.scalar(select(AgentRun).where(AgentRun.conversation_id == a[3]))
        run.status, run.failure_code = "failed", "writer_stopped"
        run.recovered_at = datetime.now(UTC)
        run.writer_token = uuid4()
        run.writer_scope = AgentWriterRegistry(config.chat_import_artifact_root).scope
    response = client.post(
        BASE + "/prepare",
        headers=headers(a[0]),
        json={"domain": "relationship", "target_id": str(a[2])},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "writer_proof_unavailable"
    root = temp / "flag-quarantine"
    root.mkdir()
    try:
        with restore_synthetic(engine, archive, root) as quarantine:
            with pytest.raises(RecoveryError):
                quarantine.reconcile()
            assert not quarantine.released
    finally:
        archive.unlink(missing_ok=True)
