"""Signed JWT + real Uvicorn socket + multipart + PostgreSQL import demo."""

import json
import os
import socket
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import httpx
import jwt
import uvicorn
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.models import RelationshipMessage
from app.db.repositories import records
from app.main import create_app

SECRET = "phase5d-synthetic-demo-secret-with-more-than-32-bytes"
SOURCE = (
    "## 2023-11-09 07:51:23 我\n\nsynthetic hello\n## 2023-11-09 07:51:24 A\n\nsynthetic reply\n"
).encode()


def main() -> None:
    raw_url = os.environ.get("TEST_DATABASE_URL")
    if not raw_url:
        raise RuntimeError("TEST_DATABASE_URL is required")
    url = make_url(raw_url)
    if url.drivername != "postgresql+psycopg" or not (url.database or "").endswith("_test"):
        raise RuntimeError("A separate psycopg _test database namespace is required")
    name = f"{url.database}_{uuid4().hex[:12]}"
    isolated_url = url.set(database=name)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    engine = None
    server = None
    thread = None
    listen = None
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
        config = Config("alembic.ini")
        config.attributes["database_url"] = isolated_url.render_as_string(hide_password=False)
        command.upgrade(config, "head")
        engine = create_engine(isolated_url, hide_parameters=True)
        with sessionmaker(bind=engine)() as db, db.begin():
            user = records.create_user(db)
            person = records.create_person(db, user.id, "A")
            relationship = records.create_relationship(db, user.id, person.id, "dating", "active")
            user_id, person_id, relationship_id = user.id, person.id, relationship.id
        with TemporaryDirectory(prefix="phase5d-artifacts-") as temporary:
            root = Path(temporary)
            app = create_app(
                Settings(
                    app_env="test",
                    database_url=isolated_url.render_as_string(hide_password=False),
                    auth_jwt_secret=SECRET,
                    auth_jwt_issuer="phase5d-demo",
                    auth_jwt_audience="phase5d-api",
                    chat_import_artifact_root=root,
                    _env_file=None,
                )
            )
            token = jwt.encode(
                {
                    "sub": str(user_id),
                    "exp": datetime.now(UTC) + timedelta(minutes=5),
                    "iss": "phase5d-demo",
                    "aud": "phase5d-api",
                },
                SECRET,
                algorithm="HS256",
            )
            listen = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listen.bind(("127.0.0.1", 0))
            listen.listen(128)
            port = listen.getsockname()[1]
            server = uvicorn.Server(
                uvicorn.Config(app, host="127.0.0.1", port=port, log_config=None, access_log=False)
            )
            thread = threading.Thread(target=server.run, kwargs={"sockets": [listen]}, daemon=True)
            thread.start()
            deadline = time.monotonic() + 10
            while not server.started and time.monotonic() < deadline:
                time.sleep(0.05)
            if not server.started:
                raise RuntimeError("Uvicorn did not start")
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=30) as client:
                auth = {"Authorization": f"Bearer {token}"}
                response = client.post(
                    "/api/v1/chat-imports",
                    headers=auth,
                    data={"source_timezone": "Asia/Shanghai"},
                    files={"file": ("synthetic.md", SOURCE, "application/octet-stream")},
                )
                if response.status_code != 201:
                    raise RuntimeError(f"Upload failed: HTTP {response.status_code}")
                job = response.json()
                if {speaker["raw_speaker_label"] for speaker in job["speakers"]} != {"我", "A"}:
                    raise RuntimeError("Unexpected speaker inventory")
                path = f"/api/v1/chat-imports/{job['id']}"
                revision = job["binding_revision"]
                for label, kind, bound_person in (("我", "self", None), ("A", "person", person_id)):
                    response = client.put(
                        path + "/speakers",
                        headers=auth,
                        json={
                            "raw_speaker_label": label,
                            "binding_kind": kind,
                            "person_id": str(bound_person) if bound_person else None,
                            "expected_revision": revision,
                        },
                    )
                    if response.status_code != 200:
                        raise RuntimeError("Speaker binding failed")
                    revision = response.json()["binding_revision"]
                response = client.put(
                    path + "/relationship",
                    headers=auth,
                    json={
                        "relationship_id": str(relationship_id),
                        "expected_revision": revision,
                    },
                )
                if response.status_code != 200:
                    raise RuntimeError("Relationship binding failed")
                ready = client.post(path + "/ready", headers=auth)
                if ready.status_code != 200:
                    raise RuntimeError("Readiness transition failed")
                receipt = client.post(
                    path + "/finalize",
                    headers=auth,
                    json={
                        "expected_revision": ready.json()["binding_revision"],
                    },
                )
                if receipt.status_code != 200 or receipt.json()["new_message_count"] != 2:
                    raise RuntimeError("Finalize failed")
                page = client.get(
                    f"/api/v1/relationships/{relationship_id}/messages",
                    headers=auth,
                    params={"limit": 1},
                )
                if page.status_code != 200 or not page.json()["next_cursor"]:
                    raise RuntimeError("Paginated relationship history failed")
                with sessionmaker(bind=engine)() as db:
                    stored = db.scalar(
                        select(func.count())
                        .select_from(RelationshipMessage)
                        .where(RelationshipMessage.relationship_id == relationship_id)
                    )
                if stored != 2 or list(root.glob("*.bin")):
                    raise RuntimeError("Persistence or artifact cleanup failed")
                print(
                    json.dumps(
                        {
                            "upload_status": 201,
                            "speaker_count": len(job["speakers"]),
                            "ready_status": ready.json()["status"],
                            "imported_message_count": stored,
                            "paginated_first_page_count": len(page.json()["items"]),
                            "raw_artifacts_remaining": 0,
                            "result": "PASS",
                        }
                    )
                )
    finally:
        if server is not None:
            server.should_exit = True
        if thread is not None:
            thread.join(timeout=10)
        if listen is not None:
            listen.close()
        if engine is not None:
            engine.dispose()
        with admin.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :name AND pid <> pg_backend_pid()"
                ),
                {"name": name},
            )
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        admin.dispose()


if __name__ == "__main__":
    main()
