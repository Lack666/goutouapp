"""Phase 6 real socket, signed JWT, AgentService/LangGraph and PostgreSQL demo."""

import json
import socket
import threading
import time
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import UUID, uuid4

import httpx
import jwt
import uvicorn
from memory_control_demo import create_scope, disposable_database
from memory_phase6_support import FACTS, Phase6Mock, agent_request
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import MemoryRecordRow
from app.main import create_app
from app.services.memory_retention import MemoryRetentionService

SECRET = "phase6d-socket-demo-secret-with-more-than-32-bytes"


def main():
    with disposable_database() as engine:
        owner, person, relationship, conversation = create_scope(engine)
        provider = Phase6Mock()
        app = create_app(
            Settings(
                app_env="test",
                database_url=engine.url.render_as_string(hide_password=False),
                auth_jwt_secret=SECRET,
                auth_jwt_issuer="phase6d-demo",
                auth_jwt_audience="phase6d-api",
                llm_provider="mock",
                _env_file=None,
            )
        )
        token = jwt.encode(
            {
                "sub": str(owner),
                "exp": datetime.now(UTC) + timedelta(minutes=5),
                "iss": "phase6d-demo",
                "aud": "phase6d-api",
            },
            SECRET,
            algorithm="HS256",
        )
        headers = {"Authorization": "Bearer " + token}
        listen = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen.bind(("127.0.0.1", 0))
        listen.listen(128)
        server = uvicorn.Server(uvicorn.Config(app, log_config=None, access_log=False))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listen]}, daemon=True)
        with patch("app.api.dependencies.create_llm_provider", return_value=provider):
            thread.start()
            try:
                deadline = time.monotonic() + 10
                while not server.started and time.monotonic() < deadline:
                    assert thread.is_alive(), "Uvicorn startup failed"
                    time.sleep(0.05)
                assert server.started, "Uvicorn startup timeout"
                output = {"real_socket": True, "real_signed_jwt": True, "real_postgresql": True}
                with httpx.Client(
                    base_url=f"http://127.0.0.1:{listen.getsockname()[1]}", timeout=10
                ) as client:

                    def call(method, path, body=None):
                        response = client.request(
                            method, "/api/v1" + path, headers=headers, json=body
                        )
                        assert response.status_code == 200, "HTTP memory operation failed"
                        return response.json()

                    def run(fact=None, stream=False):
                        return agent_request(
                            client, headers, conversation, fact=fact, stream=stream
                        )[0]

                    def inspect():
                        return call("GET", "/memories")["items"]

                    def execute(challenge, key):
                        return call(
                            "POST",
                            f"/memory/deletions/{challenge['confirmation_id']}/execute",
                            {"operation_key": key},
                        )

                    assert not call("GET", "/memory/control")["consent_enabled"]
                    assert call("POST", "/memory/consent", {"enabled": True})[
                        "effective_write_enabled"
                    ]
                    assert run(FACTS[0]) == "saved" and run(FACTS[1], stream=True) == "saved"
                    output["saved_via_rest_and_sse_count"] = len(inspect())
                    call("POST", "/memory/pause")
                    assert run(FACTS[2]) == "skipped_paused"
                    assert provider.analysis_payloads[-1]["historical_memory"] == []
                    output["pause_blocks_recall_and_write"] = True
                    call("POST", "/memory/resume")
                    run()
                    assert len(provider.analysis_payloads[-1]["historical_memory"]) == 2
                    preview = call("GET", "/memory/undo/preview")
                    body = {
                        "expected_operation_id": preview["latest_operation_id"],
                        "operation_key": "demo-undo",
                    }
                    receipt = call("POST", "/memory/undo", body)
                    replay = call("POST", "/memory/undo", body)
                    assert replay["mutation_id"] == receipt["mutation_id"] and replay["replayed"]
                    assert len(inspect()) == 1
                    output["undo_replay_preserves_older_record"] = True
                    assert run(FACTS[2]) == "saved"
                    selected = inspect()[0]
                    challenge = call(
                        "POST",
                        "/memory/deletions/one/prepare",
                        {
                            "memory_id": selected["id"],
                            "person_id": str(person),
                            "relationship_id": str(relationship),
                        },
                    )
                    assert len(inspect()) == 2
                    deletion = execute(challenge, "demo-delete")
                    assert deletion["affected_count"] == 1
                    assert execute(challenge, "demo-delete")["replayed"]
                    assert call("GET", f"/memory/mutations/{deletion['mutation_id']}")[
                        "primary_store_only"
                    ]
                    output["delete_receipt_id"] = deletion["mutation_id"]
                    assert run(FACTS[3]) == "saved"
                    expiring = inspect()[0]
                    with Session(engine) as db, db.begin():
                        db.get(MemoryRecordRow, UUID(expiring["id"])).expires_at = datetime.now(
                            UTC
                        ) - timedelta(seconds=1)
                    assert call("GET", f"/memories/{expiring['id']}")["state"] == "expired"
                    run()
                    assert len(provider.analysis_payloads[-1]["historical_memory"]) == 1
                    output["expired_excluded_before_cleanup"] = True
                    maintenance = MemoryRetentionService(lambda: Session(engine))
                    assert maintenance.run().counts.memory_records == 1
                    cleaned = maintenance.run(dry_run=False, batch_size=1)
                    assert cleaned.status == "ok" and cleaned.counts.memory_records == 1
                    assert maintenance.run(dry_run=False).counts.memory_records == 0
                    output["cleanup_record_count"] = cleaned.counts.memory_records
                    output["cleanup_undo_count"] = cleaned.counts.undo_operations
                    assert len(inspect()) == 1
                    remaining = inspect()[0]
                    with Session(engine) as db, db.begin():
                        db.get(MemoryRecordRow, UUID(remaining["id"])).expires_at = datetime.now(
                            UTC
                        ) - timedelta(seconds=1)
                    assert run(FACTS[0]) == "saved"
                    assert inspect()[0]["id"] != remaining["id"]
                    output["expired_duplicate_resave_new_id"] = True
                    all_challenge = call(
                        "POST",
                        "/memory/deletions/all/prepare",
                        {"revoke_consent_after_delete": True},
                    )
                    assert execute(all_challenge, uuid4().hex)["affected_count"] == 1
                    assert inspect() == [] and not call("GET", "/memory/control")["consent_enabled"]
                    output["final_inspect_count"] = 0
                    output["status"] = "PASS"
                # No content, prompts, private chats or tokens are printed.
                print(json.dumps(output))
            finally:
                server.should_exit = True
                thread.join(timeout=10)
                listen.close()
                assert not thread.is_alive(), "Uvicorn did not stop"


if __name__ == "__main__":
    main()
