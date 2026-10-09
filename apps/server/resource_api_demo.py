"""Phase 8A real Uvicorn + signed JWT + existing Agent/MockLLM + PostgreSQL demo."""

import json
import socket
import threading
import time
from unittest.mock import patch
from uuid import UUID, uuid4

import httpx
import uvicorn
from memory_control_demo import disposable_database
from memory_phase6_support import Phase6Mock
from resource_demo_support import ResourceFlow, create_owners, headers, settings
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Conversation, Message, Person, Relationship
from app.main import create_app


def run_demo(engine):
    owner, foreign = create_owners(engine)
    app = create_app(settings(engine))
    provider = Phase6Mock()
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
            with httpx.Client(
                base_url=f"http://127.0.0.1:{listen.getsockname()[1]}", timeout=10
            ) as client:
                flow = ResourceFlow(client, owner)
                person_id, relationship_id, conversation_id = (str(uuid4()) for _ in range(3))
                bodies = {
                    "persons": {"id": person_id, "display_name": "Synthetic A"},
                    "relationships": {
                        "id": relationship_id,
                        "person_id": person_id,
                        "relationship_type": "unknown",
                        "status": "unknown",
                    },
                    "conversations": {"id": conversation_id, "relationship_id": relationship_id},
                }
                output = {"real_socket": True, "signed_jwt": True, "postgresql": True}
                for domain, body in bodies.items():
                    # Discard the first response, simulating its loss after server commit.
                    first = client.post(f"/api/v1/{domain}", headers=flow.headers, json=body)
                    assert first.status_code == 201
                    replay = flow.call("POST", f"/{domain}", body, status=201)
                    assert replay == flow.call("GET", f"/{domain}/{body['id']}")
                    assert flow.pages(f"/{domain}", limit=1) == [replay]
                    assert flow.call("GET", f"/{domain}", auth=headers(foreign)) == {
                        "items": [],
                        "next_cursor": None,
                    }
                    denied = flow.call(
                        "GET", f"/{domain}/{body['id']}", auth=headers(foreign), status=404
                    )
                    missing = flow.call(
                        "GET", f"/{domain}/{uuid4()}", auth=headers(foreign), status=404
                    )
                    assert denied == missing
                output["response_loss_retries"] = 3
                output["owner_neutral_denials"] = 3
                result = flow.call(
                    "POST",
                    f"/conversations/{conversation_id}/agent-runs",
                    {
                        "message": "请分析合成背景",
                        "expected_relationship_id": relationship_id,
                        "operation_key": uuid4().hex,
                    },
                )
                history_path = f"/conversations/{conversation_id}/messages"
                history = flow.pages(history_path, limit=1)
                assert history == flow.pages(history_path, limit=1)
                assert [row["role"] for row in history] == ["user", "assistant"]
                assert history[1]["id"] == result["assistant_message"]["id"]
                assert history[1]["content"] == result["assistant_message"]["content"]
                flow.call("GET", history_path, auth=headers(foreign), status=404)
                with Session(engine) as db:
                    counts = {
                        model.__tablename__: db.scalar(
                            select(func.count()).select_from(model).where(model.user_id == owner)
                        )
                        for model in (Person, Relationship, Conversation)
                    }
                    assert list(counts.values()) == [1, 1, 1]
                    stored = db.scalars(
                        select(Message).where(Message.conversation_id == UUID(conversation_id))
                    ).all()
                    assert {str(row.id) for row in stored} == {row["id"] for row in history}
                output.update(
                    owned_resource_counts=counts,
                    agent_status=result["status"],
                    persisted_history_roles=[row["role"] for row in history],
                    history_pages_repeat_without_loss=True,
                )
                return output
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            listen.close()
            assert not thread.is_alive(), "Uvicorn did not stop"


def main():
    with disposable_database() as engine:
        print(json.dumps(run_demo(engine), sort_keys=True))


if __name__ == "__main__":
    main()
