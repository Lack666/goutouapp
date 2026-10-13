"""Independent keyless synthetic PostgreSQL maintenance and restore demonstration."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient
from memory_control_demo import create_scope, disposable_database, run_agent
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import ChatImportArtifact, MemoryRecordRow, RelationshipMessage
from app.db.repositories.memory import SQLAlchemyMemoryStore
from app.main import create_app
from app.services.agent_service import actor_from_verified_identity
from app.services.backup_restore import dump_synthetic, restore_synthetic
from app.services.maintenance import MaintenanceLoop, MaintenanceService
from app.services.memory_control import MemoryControlService
from app.services.memory_mutation import MemoryMutationService


def demonstration():
    cache = Path(".cache").resolve()
    cache.mkdir(exist_ok=True)
    with disposable_database() as source, TemporaryDirectory(prefix="phase9d-", dir=cache) as temp:
        temporary = Path(temp)
        a, b = create_scope(source), create_scope(source)
        store = SQLAlchemyMemoryStore(lambda: Session(source))
        for scope in (a, b):
            MemoryControlService(store).grant_consent(actor_from_verified_identity(scope[0]))
            assert asyncio.run(run_agent(source, *scope, store, save=True))[0] == "saved"
        record_a, record_b = store.list_records(a[0])[0], store.list_records(b[0])[0]
        config = Settings(
            app_env="test",
            database_url=source.url.render_as_string(hide_password=False),
            auth_jwt_secret="phase9d-synthetic-demo-secret-at-least32bytes",
            auth_jwt_issuer="phase9d-demo",
            auth_jwt_audience="phase9d-api",
            llm_provider="mock",
            chat_import_artifact_root=temporary / "source-files",
            admission_min_free_bytes=0,
            _env_file=None,
        )
        app = create_app(config)
        token = jwt.encode(
            {
                "sub": str(a[0]),
                "exp": datetime.now(UTC) + timedelta(minutes=5),
                "iss": config.auth_jwt_issuer,
                "aud": config.auth_jwt_audience,
            },
            config.auth_jwt_secret.get_secret_value(),
            algorithm="HS256",
        )
        auth = {"Authorization": "Bearer " + token}
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/chat-imports",
                headers=auth,
                data={"source_timezone": "Asia/Shanghai"},
                files={
                    "file": (
                        "synthetic.md",
                        "## 2023-11-09 07:51:23 我\n\nsynthetic hello\n"
                        "## 2023-11-09 07:51:24 A\n\nsynthetic reply\n".encode(),
                        "application/octet-stream",
                    )
                },
            )
            assert response.status_code == 201
            job = response.json()
            path = "/api/v1/chat-imports/" + job["id"]
            revision = job["binding_revision"]
            for label, kind, person in (("我", "self", None), ("A", "person", a[1])):
                response = client.put(
                    path + "/speakers",
                    headers=auth,
                    json={
                        "raw_speaker_label": label,
                        "binding_kind": kind,
                        "person_id": str(person) if person else None,
                        "expected_revision": revision,
                    },
                )
                assert response.status_code == 200
                revision = response.json()["binding_revision"]
            assert (
                client.put(
                    path + "/relationship",
                    headers=auth,
                    json={"relationship_id": str(a[2]), "expected_revision": revision},
                ).status_code
                == 200
            )
            ready = client.post(path + "/ready", headers=auth).json()
            assert (
                client.post(
                    path + "/finalize",
                    headers=auth,
                    json={"expected_revision": ready["binding_revision"]},
                ).status_code
                == 200
            )
            archive = temporary / "synthetic.dump"
            dump_synthetic(source, archive)
            mutations = MemoryMutationService(lambda: Session(source))
            actor = actor_from_verified_identity(a[0])
            challenge = mutations.prepare_delete_all(actor, revoke_consent_after_delete=True)
            receipt = mutations.execute_delete(
                actor, confirmation_id=challenge.confirmation_id, operation_key=uuid4().hex
            )
            maintenance = MaintenanceService(
                app.state.resource_admission, app.state.import_workflow
            )
            reports = []
            loop = MaintenanceLoop(maintenance, interval_seconds=0.02)
            loop.run(Event(), iterations=3, report=reports.append)
            assert all(r.status == "ok" for r in reports)
            root = temporary / "restore-files"
            root.mkdir()
            with restore_synthetic(source, archive, root) as recovery:
                with Session(recovery._target) as db:
                    assert db.get(MemoryRecordRow, record_a.id) is not None
                restored = recovery.reconcile()
                target_store = SQLAlchemyMemoryStore(lambda: Session(restored))
                assert target_store.get_record(a[0], record_a.id) is None
                assert target_store.get_record(b[0], record_b.id) is not None
                assert asyncio.run(run_agent(restored, *a, target_store, save=False))[1] == 0
                assert asyncio.run(run_agent(restored, *b, target_store, save=False))[1] == 1
                replay = MemoryMutationService(lambda: Session(restored)).execute_delete(
                    actor,
                    confirmation_id=challenge.confirmation_id,
                    operation_key=receipt.operation_key,
                )
                assert replay.replayed and replay.mutation_id == receipt.mutation_id
                with Session(restored) as db:
                    assert db.scalar(select(func.count()).select_from(RelationshipMessage)) == 2
                    assert (
                        db.scalar(
                            select(func.count())
                            .select_from(ChatImportArtifact)
                            .where(ChatImportArtifact.state == "active")
                        )
                        == 0
                    )
                print(
                    json.dumps(
                        {
                            "postgresql": True,
                            "native_dump_restore": True,
                            "owners": 2,
                            "imported_occurrences": 2,
                            "maintenance_iterations": loop.executions,
                            "maintenance_failures": loop.failures,
                            "deleted_memory_recalled": 0,
                            "retained_owner_recalled": 1,
                            "original_receipt_replayed": True,
                            "restored_artifact_files": len(list(root.iterdir())),
                            "production_deployed": False,
                            **recovery.counts,
                        }
                    )
                )


if __name__ == "__main__":
    try:
        demonstration()
    except Exception:
        print('{"status":"failed","error":"synthetic_recovery_failed"}')
        raise SystemExit(1) from None
