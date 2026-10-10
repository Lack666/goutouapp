"""Interactive native smoke backend; private CLI configuration is never reported."""

import argparse
import asyncio
import json
import os
import socket
import sys
import threading
import time
from pathlib import Path

import uvicorn
from agent_demo import queue_run
from memory_control_demo import disposable_database
from mobile_connected_fixture import ChatDemoMock
from resource_demo_support import create_owners

from app.agent.dependencies import RuntimeDependencies
from app.agent.memory import MemoryService
from app.agent.runtime import AgentRuntime
from app.core.config import Settings
from app.db.repositories.memory import SQLAlchemyMemoryStore
from app.llm.mock import MockLLMProvider
from app.main import create_app
from app.services.agent_service import AgentService


class ChineseDemoMock(MockLLMProvider):
    """Existing standalone synthetic outputs, including a validated Chinese answer."""

    def __init__(self):
        super().__init__()
        for _ in range(100):
            queue_run(self, first=False, person_id=None)

    async def structured_output(self, messages, schema, **kwargs):
        await asyncio.sleep(0.1)
        return await super().structured_output(messages, schema, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8019)
    parser.add_argument("--scenario", choices=("safety", "chinese"), default="safety")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("--port must be between 1024 and 65535")
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
                    llm_provider=ChineseDemoMock()
                    if args.scenario == "chinese"
                    else ChatDemoMock(),
                    memory_service=MemoryService(SQLAlchemyMemoryStore(app.state.database.session)),
                )
            ),
        )
        listen = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen.bind(("127.0.0.1", args.port))
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
            print(
                f"native_mock_ready port={args.port} scenario={args.scenario} "
                f"owner_a={owner} owner_b={other}",
                flush=True,
            )
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
