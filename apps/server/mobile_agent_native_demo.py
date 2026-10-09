"""Interactive native smoke backend; private CLI configuration is never reported."""

import json
import os
import socket
import sys
import threading
import time
from pathlib import Path

import uvicorn
from memory_control_demo import disposable_database
from mobile_connected_fixture import ChatDemoMock
from resource_demo_support import create_owners

from app.agent.dependencies import RuntimeDependencies
from app.agent.memory import MemoryService
from app.agent.runtime import AgentRuntime
from app.core.config import Settings
from app.db.repositories.memory import SQLAlchemyMemoryStore
from app.main import create_app
from app.services.agent_service import AgentService


def main():
    root = Path(__file__).resolve().parents[2]
    private_config = root / ".cache/phase8c-native-server.env"
    private_config.parent.mkdir(exist_ok=True)
    if private_config.exists():
        raise RuntimeError(
            "Native fixture configuration already exists; stop the prior runner first"
        )
    with disposable_database() as engine:
        owner, other = create_owners(engine)
        settings = Settings(
            _env_file=None,
            app_env="development",
            database_url=engine.url.render_as_string(hide_password=False),
            auth_jwt_secret=os.urandom(48).hex(),
            llm_provider="mock",
        )
        app = create_app(settings)
        app.state.agent_service = AgentService(
            app.state.database.session,
            AgentRuntime(
                dependencies=RuntimeDependencies(
                    llm_provider=ChatDemoMock(),
                    memory_service=MemoryService(SQLAlchemyMemoryStore(app.state.database.session)),
                )
            ),
        )
        listen = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen.bind(("127.0.0.1", 8019))
        listen.listen(128)
        server = uvicorn.Server(uvicorn.Config(app, log_config=None, access_log=False))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listen]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started and time.monotonic() < deadline:
                if not thread.is_alive():
                    raise RuntimeError("Native smoke backend failed to start")
                time.sleep(0.05)
            if not server.started:
                raise RuntimeError("Native smoke backend startup timed out")
            fields = {
                "APP_ENV": "development",
                "DATABASE_URL": settings.database_url.get_secret_value(),
                "AUTH_JWT_SECRET": settings.auth_jwt_secret.get_secret_value(),
                "AUTH_JWT_ISSUER": settings.auth_jwt_issuer,
                "AUTH_JWT_AUDIENCE": settings.auth_jwt_audience,
            }
            private_config.write_text(
                "\n".join(f"{key}={json.dumps(value)}" for key, value in fields.items()) + "\n",
                encoding="utf-8",
            )
            print(f"native_mock_ready port=8019 owner_a={owner} owner_b={other}", flush=True)
            print(
                "CLI config: .cache/phase8c-native-server.env; enter stop to clean up", flush=True
            )
            for command in sys.stdin:
                if command.strip() == "stop":
                    break
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            listen.close()
            private_config.unlink(missing_ok=True)
            if thread.is_alive():
                raise RuntimeError("Native smoke backend did not stop")


if __name__ == "__main__":
    main()
