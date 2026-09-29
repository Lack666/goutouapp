"""Real signed-JWT Uvicorn demonstration of guarded undo and confirmed delete."""

import json
import socket
import threading
import time
from datetime import UTC, datetime, timedelta

import httpx
import jwt
import uvicorn
from memory_control_demo import create_scope, disposable_database
from memory_destructive_control_demo import save
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.repositories.memory import SQLAlchemyMemoryStore
from app.main import create_app

DEMO_SECRET = "phase6b-offline-demo-secret-with-more-than-32-bytes"


def main() -> None:
    with disposable_database() as engine:
        owner, person, relationship, _ = create_scope(engine)
        store = SQLAlchemyMemoryStore(lambda: Session(engine))
        save(store, owner, person, relationship, "我们计划第一周见面")
        save(store, owner, person, relationship, "我们计划第二周见面")
        settings = Settings(
            app_env="test",
            database_url=engine.url.render_as_string(hide_password=False),
            auth_jwt_secret=DEMO_SECRET,
            auth_jwt_issuer="phase6b-demo",
            auth_jwt_audience="phase6b-api",
            llm_provider="mock",
            _env_file=None,
        )
        app = create_app(settings)
        token = jwt.encode(
            {
                "sub": str(owner),
                "exp": datetime.now(UTC) + timedelta(minutes=5),
                "iss": "phase6b-demo",
                "aud": "phase6b-api",
            },
            DEMO_SECRET,
            algorithm="HS256",
        )
        listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen_socket.bind(("127.0.0.1", 0))
        listen_socket.listen(128)
        port = listen_socket.getsockname()[1]
        server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=port, log_config=None, access_log=False)
        )
        thread = threading.Thread(
            target=server.run, kwargs={"sockets": [listen_socket]}, daemon=True
        )
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started and time.monotonic() < deadline:
                if not thread.is_alive():
                    raise RuntimeError("Uvicorn exited before startup")
                time.sleep(0.05)
            if not server.started:
                raise RuntimeError("Uvicorn did not start")
            base = f"http://127.0.0.1:{port}/api/v1"
            headers = {"Authorization": f"Bearer {token}"}
            with httpx.Client(timeout=10) as client:
                preview = client.get(f"{base}/memory/undo/preview", headers=headers)
                if preview.status_code != 200:
                    raise RuntimeError("Undo preview failed")
                undo_body = {
                    "expected_operation_id": preview.json()["latest_operation_id"],
                    "operation_key": "socket-undo",
                }
                undo = client.post(f"{base}/memory/undo", headers=headers, json=undo_body)
                retry = client.post(f"{base}/memory/undo", headers=headers, json=undo_body)
                remaining = client.get(f"{base}/memories", headers=headers)
                selected = remaining.json()["items"][0]
                prepared = client.post(
                    f"{base}/memory/deletions/one/prepare",
                    headers=headers,
                    json={
                        "memory_id": selected["id"],
                        "person_id": selected["person_id"],
                        "relationship_id": selected["relationship_id"],
                    },
                )
                challenge_id = prepared.json()["confirmation_id"]
                deletion = client.post(
                    f"{base}/memory/deletions/{challenge_id}/execute",
                    headers=headers,
                    json={"operation_key": "socket-delete"},
                )
                after = client.get(f"{base}/memories", headers=headers)
            if not (
                all(
                    response.status_code == 200
                    for response in (preview, undo, retry, remaining, prepared, deletion, after)
                )
                and retry.json()["mutation_id"] == undo.json()["mutation_id"]
                and retry.json()["replayed"]
                and len(remaining.json()["items"]) == 1
                and prepared.json()["expected_count"] == 1
                and deletion.json()["affected_count"] == 1
                and after.json()["items"] == []
            ):
                raise RuntimeError("Signed HTTP destructive memory demonstration failed")
            print(
                json.dumps(
                    {
                        "preview_http_status": preview.status_code,
                        "undo_http_status": undo.status_code,
                        "undo_retry_replayed": retry.json()["replayed"],
                        "older_memory_survived_retry": len(remaining.json()["items"]) == 1,
                        "confirmation_http_status": prepared.status_code,
                        "delete_http_status": deletion.status_code,
                        "inspect_after_delete_count": len(after.json()["items"]),
                    }
                )
            )
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            listen_socket.close()


if __name__ == "__main__":
    main()
