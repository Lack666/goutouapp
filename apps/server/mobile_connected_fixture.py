"""Disposable real HTTP/PostgreSQL fixture; credentials travel only over a private pipe.

Invoked by Playwright, never emits credentials into test reporters or files.
The development CLI is the actual issuer. No authentication override or Agent run.
"""

import json
import os
import socket
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime, timedelta

import jwt
import uvicorn
from memory_control_demo import disposable_database
from resource_demo_support import create_owners
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import Conversation, Person, Relationship
from app.main import create_app


def main():
    with disposable_database() as engine:
        owner, other = create_owners(engine)
        secret = os.urandom(48).hex()
        settings = Settings(
            _env_file=None,
            app_env="development",
            database_url=engine.url.render_as_string(hide_password=False),
            auth_jwt_secret=secret,
            dev_cors_origins=["http://localhost:8088"],
        )
        env = {
            **os.environ,
            "APP_ENV": "development",
            "DATABASE_URL": engine.url.render_as_string(hide_password=False),
            "AUTH_JWT_SECRET": secret,
            "AUTH_JWT_ISSUER": settings.auth_jwt_issuer,
            "AUTH_JWT_AUDIENCE": settings.auth_jwt_audience,
        }
        tokens = [
            subprocess.check_output(
                [sys.executable, "apps/server/dev_auth_cli.py", "token", "--user-id", str(user)],
                env=env,
                text=True,
            ).strip()
            for user in (owner, other)
        ]
        expired = jwt.encode(
            {
                "sub": str(owner),
                "exp": datetime.now(UTC) - timedelta(seconds=1),
                "iss": settings.auth_jwt_issuer,
                "aud": settings.auth_jwt_audience,
            },
            secret,
            algorithm="HS256",
        )
        app = create_app(settings)
        listen = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen.bind(("127.0.0.1", 8018))
        listen.listen(128)
        server = uvicorn.Server(uvicorn.Config(app, log_config=None, access_log=False))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listen]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started and time.monotonic() < deadline:
                if not thread.is_alive():
                    raise RuntimeError("Fixture server did not start")
                time.sleep(0.05)
            if not server.started:
                raise RuntimeError("Fixture startup timed out")
            # The caller captures this line; it must never be echoed or persisted.
            print(
                json.dumps(
                    {
                        "baseURL": "http://127.0.0.1:8018",
                        "a": tokens[0],
                        "b": tokens[1],
                        "expired": expired,
                    }
                ),
                flush=True,
            )
            for command in sys.stdin:
                if command.strip() == "stop":
                    break
                if command.strip() == "counts":
                    with Session(engine) as db:
                        counts = {
                            model.__tablename__: db.scalar(
                                select(func.count())
                                .select_from(model)
                                .where(model.user_id == owner)
                            )
                            for model in (Person, Relationship, Conversation)
                        }
                        print(json.dumps(counts), flush=True)
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            listen.close()
            if thread.is_alive():
                raise RuntimeError("Fixture did not stop")


if __name__ == "__main__":
    main()
