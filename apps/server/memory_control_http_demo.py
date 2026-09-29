"""Real local Uvicorn and signed JWT demonstration of Phase 6A routes."""

import json
import socket
import threading
import time
from datetime import UTC, datetime, timedelta

import httpx
import jwt
import uvicorn
from memory_control_demo import create_scope, disposable_database

from app.core.config import Settings
from app.main import create_app

DEMO_SECRET = "phase6a-offline-demo-secret-with-more-than-32-bytes"


def main() -> None:
    with disposable_database() as engine:
        user, _, _, _ = create_scope(engine)
        settings = Settings(
            app_env="test",
            database_url=engine.url.render_as_string(hide_password=False),
            auth_jwt_secret=DEMO_SECRET,
            auth_jwt_issuer="phase6a-demo",
            auth_jwt_audience="phase6a-api",
            llm_provider="mock",
            _env_file=None,
        )
        app = create_app(settings)
        token = jwt.encode(
            {
                "sub": str(user),
                "exp": datetime.now(UTC) + timedelta(minutes=5),
                "iss": "phase6a-demo",
                "aud": "phase6a-api",
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
                initial = client.get(f"{base}/memory/control", headers=headers)
                granted = client.post(
                    f"{base}/memory/consent", headers=headers, json={"enabled": True}
                )
                paused = client.post(f"{base}/memory/pause", headers=headers)
                resumed = client.post(f"{base}/memory/resume", headers=headers)
                memories = client.get(f"{base}/memories", headers=headers)
            if not (
                all(
                    response.status_code == 200
                    for response in (initial, granted, paused, resumed, memories)
                )
                and not initial.json()["consent_enabled"]
                and granted.json()["effective_write_enabled"]
                and paused.json()["paused"]
                and resumed.json()["effective_read_enabled"]
                and memories.json()["items"] == []
            ):
                raise RuntimeError("Signed HTTP memory control demonstration failed")
            print(
                json.dumps(
                    {
                        "initial_http_status": initial.status_code,
                        "grant_effective": granted.json()["effective_write_enabled"],
                        "pause_blocks_recall": not paused.json()["effective_read_enabled"],
                        "resume_restores_recall": resumed.json()["effective_read_enabled"],
                        "inspect_http_status": memories.status_code,
                        "inspect_count": len(memories.json()["items"]),
                    }
                )
            )
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            listen_socket.close()


if __name__ == "__main__":
    main()
