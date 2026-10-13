"""Independent signed synthetic erasure and native PostgreSQL recovery demo."""

import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from uuid import uuid4

from fastapi.testclient import TestClient
from memory_control_demo import create_scope, disposable_database, run_agent
from resource_demo_support import headers, settings
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Message, RelationshipMessage
from app.db.repositories.memory import SQLAlchemyMemoryStore
from app.main import create_app
from app.services.agent_service import actor_from_verified_identity
from app.services.backup_restore import dump_synthetic, restore_synthetic
from app.services.maintenance import MaintenanceLoop, MaintenanceService
from app.services.memory_control import MemoryControlService


def demonstration():
    with (
        disposable_database() as source,
        TemporaryDirectory(prefix="phase9e-", dir=".cache") as temp,
    ):
        root = Path(temp)
        a, b = create_scope(source), create_scope(source)
        store = SQLAlchemyMemoryStore(lambda: Session(source))
        for scope in (a, b):
            MemoryControlService(store).grant_consent(actor_from_verified_identity(scope[0]))
            assert asyncio.run(run_agent(source, *scope, store, save=True))[0] == "saved"
        config = settings(
            source, chat_import_artifact_root=root / "artifacts", admission_min_free_bytes=0
        )
        app = create_app(config)
        with TestClient(app) as client:
            auth = headers(a[0])

            def call(method, path, body=None, expected=200):
                response = client.request(method, "/api/v1" + path, headers=auth, json=body)
                assert response.status_code == expected
                return response.json()

            uploaded = client.post(
                "/api/v1/chat-imports",
                headers=auth,
                data={"source_timezone": "Asia/Shanghai"},
                files={
                    "file": (
                        "synthetic.md",
                        (
                            "## 2023-11-09 07:51:23 我\n\nsynthetic one\n"
                            "## 2023-11-09 07:51:24 A\n\nsynthetic two\n"
                        ).encode(),
                        "application/octet-stream",
                    )
                },
            )
            assert uploaded.status_code == 201
            job = uploaded.json()
            path = "/chat-imports/" + job["id"]
            revision = job["binding_revision"]
            for label, kind, person in (("我", "self", None), ("A", "person", a[1])):
                job = call(
                    "PUT",
                    path + "/speakers",
                    {
                        "raw_speaker_label": label,
                        "binding_kind": kind,
                        "person_id": str(person) if person else None,
                        "expected_revision": revision,
                    },
                )
                revision = job["binding_revision"]
            call(
                "PUT",
                path + "/relationship",
                {"relationship_id": str(a[2]), "expected_revision": revision},
            )
            ready = call("POST", path + "/ready")
            call("POST", path + "/finalize", {"expected_revision": ready["binding_revision"]})
            archive = root / "synthetic.dump"
            dump_synthetic(source, archive)
            operations, receipts = [], []
            for domain, target in (("dataset", job["id"]), ("conversation", str(a[3]))):
                body = {"domain": domain, "target_id": target, "relationship_id": str(a[2])}
                challenge = call("POST", "/erasures/prepare", body)
                assert challenge["message_count"] == 2
                operation = {
                    **body,
                    "confirmation_id": challenge["confirmation_id"],
                    "operation_key": uuid4().hex,
                }
                receipt = call("POST", "/erasures/execute", operation)
                assert call("POST", "/erasures/execute", operation) == receipt
                operations.append(operation)
                receipts.append(receipt)
            call(
                "POST",
                path + "/finalize",
                {"expected_revision": ready["binding_revision"]},
                expected=409,
            )
            reports = []
            loop = MaintenanceLoop(
                MaintenanceService(app.state.resource_admission, app.state.import_workflow),
                interval_seconds=0.02,
            )
            loop.run(Event(), iterations=3, report=reports.append)
            assert all(report.status == "ok" for report in reports)
            restored_root = root / "restored-artifacts"
            restored_root.mkdir()
            with restore_synthetic(source, archive, restored_root) as recovery:
                with Session(recovery._target) as db:
                    assert db.scalar(select(func.count()).select_from(RelationshipMessage)) == 2
                restored = recovery.reconcile()
                assert recovery.counts["dataset_messages_removed"] == 2
                assert recovery.counts["agent_messages_removed"] == 2
                restored_config = settings(restored, chat_import_artifact_root=restored_root)
                with TestClient(create_app(restored_config)) as recovered:
                    for operation, receipt in zip(operations, receipts, strict=True):
                        response = recovered.post(
                            "/api/v1/erasures/execute", headers=auth, json=operation
                        )
                        assert response.status_code == 200 and response.json() == receipt
                with Session(restored) as db:
                    assert db.scalar(select(func.count()).select_from(RelationshipMessage)) == 0
                    assert (
                        db.scalar(
                            select(func.count())
                            .select_from(Message)
                            .where(Message.conversation_id == a[3])
                        )
                        == 0
                    )
                    assert (
                        db.scalar(
                            select(func.count())
                            .select_from(Message)
                            .where(Message.conversation_id == b[3])
                        )
                        == 2
                    )
                target_store = SQLAlchemyMemoryStore(lambda: Session(restored))
                assert (
                    len(target_store.list_records(a[0]))
                    == len(target_store.list_records(b[0]))
                    == 1
                )
            return {
                "postgresql": True,
                "signed_http": True,
                "dataset_deleted": True,
                "conversation_deleted": True,
                "original_receipts_replayed": True,
                "native_dump_restore": True,
                "memory_preserved": True,
                "owner_b_preserved": True,
                "maintenance_iterations": loop.executions,
                "backend_only": True,
                "production_deployed": False,
            }


if __name__ == "__main__":
    try:
        print(json.dumps(demonstration(), sort_keys=True))
    except Exception:
        raise SystemExit("synthetic_erasure_demo_failed") from None
