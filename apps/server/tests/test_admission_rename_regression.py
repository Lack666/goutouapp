"""Reproduce the pre-existing inventory/atomic upload-promotion race deterministically."""

from pathlib import Path
from unittest.mock import patch

import pytest
from test_agent_rest import settings
from test_import_api import scope

from app.db.session import Database
from app.services.resource_admission import AdmissionRejected, ResourceAdmission


@pytest.mark.parametrize("live", [True, False])
def test_vanished_inventory_entry_requires_live_fully_charged_reservation(
    database_engine, tmp_path, live
):
    owner, *_ = scope(database_engine)
    config = settings(
        database_engine,
        chat_import_artifact_root=tmp_path / "artifacts",
        admission_min_free_bytes=0,
    )
    config.chat_import_artifact_root.mkdir()
    database = Database(config)
    admission = ResourceAdmission(database, config)
    lease = admission.acquire(owner)
    path = admission.root / ((lease.artifact_key if live else "unknown") + ".part")
    path.write_bytes(b"synthetic")
    original = Path.lstat

    def promoted(candidate, *args, **kwargs):
        if candidate == path:
            raise FileNotFoundError()
        return original(candidate, *args, **kwargs)

    try:
        with database.session() as db, db.begin(), patch.object(Path, "lstat", promoted):
            if live:
                active, totals, _ = admission._inventory(db)
                assert len(active) == 1
                assert totals[owner] == admission.upload_reservation_bytes
            else:
                with pytest.raises(AdmissionRejected):
                    admission._inventory(db)
    finally:
        admission.release(lease)
        database.dispose()
