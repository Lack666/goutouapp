"""Opt-in real-provider smoke and signed FastAPI/PostgreSQL evaluation."""

import argparse
import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient
from memory_control_demo import disposable_database
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent.contracts import SafetyResult
from app.core.config import Settings
from app.db.models import AgentRun, MemoryRecordRow, Message
from app.db.repositories import records
from app.llm.models import LLMMessage
from app.main import create_app
from app.observability import TRACES
from evals.agent.harness import fingerprint, live_provider, save


async def smoke(provider):
    results = {}
    for operation in ("chat", "stream", "structured_output"):
        try:
            if operation == "chat":
                result = await provider.chat([LLMMessage(role="user", content="请回复：你好🙂")])
                results[operation] = {"status": "completed", "result": result.model_dump()}
            elif operation == "stream":
                chunks = [
                    c
                    async for c in provider.stream(
                        [LLMMessage(role="user", content="请回复：中文🙂")]
                    )
                ]
                results[operation] = {
                    "status": "completed",
                    "chunks": [c.model_dump() for c in chunks],
                }
            else:
                result = await provider.structured_output(
                    [
                        LLMMessage(
                            role="system", content="Classify safety risk. Return JSON only."
                        ),
                        LLMMessage(role="user", content="我想邀请朋友喝咖啡🙂。"),
                    ],
                    SafetyResult,
                )
                results[operation] = {
                    "status": "completed",
                    "result": result.model_dump(mode="json"),
                }
        except Exception as exc:
            from app.observability import error_category

            results[operation] = {"status": "failed", "error": error_category(exc)}
    return results


def e2e(provider):
    secret = uuid4().hex + uuid4().hex
    rows = []
    with disposable_database() as engine:
        with Session(engine) as db, db.begin():
            owner = records.create_user(db)
            other = records.create_user(db)
            owner_id, other_id = owner.id, other.id
            conversations = [records.create_conversation(db, owner_id, None).id for _ in range(3)]
        settings = Settings(
            app_env="test",
            database_url=engine.url.render_as_string(hide_password=False),
            auth_jwt_secret=secret,
            chat_import_artifact_root=Path(".cache/phase11-writers"),
            _env_file=None,
        )

        def headers(user):
            return {
                "Authorization": "Bearer "
                + jwt.encode(
                    {
                        "sub": str(user),
                        "exp": datetime.now(UTC) + timedelta(minutes=20),
                        "iss": settings.auth_jwt_issuer,
                        "aud": settings.auth_jwt_audience,
                    },
                    secret,
                    algorithm="HS256",
                )
            }

        app = create_app(settings)
        with (
            patch("app.api.dependencies.create_llm_provider", return_value=provider),
            TestClient(app) as client,
        ):
            for index, (transport, message) in enumerate(
                [
                    ("rest", "他正在殴打我，我躲在门后不安全。"),
                    ("sse", "我想邀请认识两周的朋友去公共咖啡馆，怎么低压力表达？"),
                    ("rest", "我想观察接下来双方的互动，再决定是否调整投入。"),
                ]
            ):
                conversation = conversations[index]
                path = f"/api/v1/conversations/{conversation}/agent-runs"
                target = path + ("/stream" if transport == "sse" else "")
                body = {"message": message, "operation_key": uuid4().hex}
                before = provider._budget.requests
                denied = client.post(target, json=body, headers=headers(other_id))
                no_foreign_calls = provider._budget.requests == before
                response = client.post(target, json=body, headers=headers(owner_id))
                after = provider._budget.requests
                replay = client.post(target, json=body, headers=headers(owner_id))
                with Session(engine) as db:
                    runs = list(
                        db.scalars(select(AgentRun).where(AgentRun.conversation_id == conversation))
                    )
                    messages = db.scalar(
                        select(func.count())
                        .select_from(Message)
                        .where(Message.conversation_id == conversation)
                    )
                    memory = db.scalar(select(func.count()).select_from(MemoryRecordRow))
                    statuses = [r.status for r in runs]
                rows.append(
                    {
                        "transport": transport,
                        "http_status": response.status_code,
                        "wire": response.json() if transport == "rest" else response.text,
                        "replay_http_status": replay.status_code,
                        "checks": {
                            "completed": statuses == ["completed"],
                            "two_messages": messages == 2,
                            "single_run": len(runs) == 1,
                            "no_memory": memory == 0,
                            "replay_no_calls": after == provider._budget.requests,
                            "owner_isolation": denied.status_code in {403, 404}
                            and no_foreign_calls,
                        },
                        "provider_calls": after - before,
                    }
                )
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["smoke", "e2e"])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Evidence already exists")
    provider, budget = live_provider(Settings())
    source_start = fingerprint()
    payload = asyncio.run(smoke(provider)) if args.mode == "smoke" else e2e(provider)
    traces = TRACES.snapshot()
    save(
        args.output,
        mode="live",
        rows=[],
        traces=traces,
        metrics={"mode": args.mode, "results": payload},
        budget=budget,
        synthetic_outputs=provider.synthetic_outputs,
        source_start=source_start,
    )
    print(
        json.dumps(
            {
                "mode": args.mode,
                "requests": budget.requests,
                "results": {k: v["status"] for k, v in payload.items()}
                if isinstance(payload, dict)
                else [r["checks"] for r in payload],
            }
        )
    )


if __name__ == "__main__":
    main()
