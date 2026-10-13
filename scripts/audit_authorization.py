"""Generate the reviewed security inventory from actual FastAPI routers/OpenAPI."""

import argparse
import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/server"))
from fastapi.routing import APIRoute  # noqa: E402

from app.api.health import router as health_router  # noqa: E402
from app.api.readiness import router as readiness_router  # noqa: E402
from app.api.v1 import agent_runs, chat_imports, erasure, memory, resources, status  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

TARGET = ROOT / "docs/AUTHORIZATION_API_INVENTORY.json"


def inventory():
    app = create_app(Settings(_env_file=None))
    schema = app.openapi()
    result = []
    routers = (
        health_router,
        readiness_router,
        status.router,
        agent_runs.router,
        chat_imports.router,
        memory.router,
        resources.router,
        erasure.router,
    )
    for route in (route for router in routers for route in router.routes):
        if not isinstance(route, APIRoute) or not route.include_in_schema:
            continue
        filename = Path(inspect.getfile(route.endpoint)).relative_to(ROOT).as_posix()
        name = Path(filename).stem
        path = route.path if name in {"health", "readiness"} else "/api/v1" + route.path
        public = name in {"health", "readiness", "status"}
        group = (
            "resources"
            if name == "resources"
            else "agent"
            if name == "agent_runs"
            else "import"
            if name == "chat_imports"
            else "memory"
            if name == "memory"
            else "erasure"
            if name == "erasure"
            else "public"
        )
        service = {
            "erasure": ["apps/server/app/services/erasure.py"],
            "resources": [
                "apps/server/app/services/resources.py",
                "apps/server/app/db/repositories/resources.py",
                "apps/server/app/db/repositories/records.py",
            ],
            "agent": [
                "apps/server/app/services/agent_service.py",
                "apps/server/app/db/repositories/records.py",
            ],
            "import": [
                "apps/server/app/services/import_jobs.py",
                "apps/server/app/services/import_workflow.py",
                "apps/server/app/services/import_merge.py",
                "apps/server/app/db/repositories/records.py",
            ],
            "memory": [
                "apps/server/app/services/memory_control.py",
                "apps/server/app/services/memory_mutation.py",
                "apps/server/app/db/repositories/memory.py",
            ],
            "public": [],
        }[group]
        parents = {
            "erasure": (
                "Signed existing owner; exact canonical Dataset/Conversation and Relationship; "
                "owner-bound snapshot/expiry challenge and durable original-key receipt"
            ),
            "resources": (
                "Relationship create validates owned Person; Conversation create validates owned "
                "Relationship; Message history validates owned Conversation; "
                "cursor binds owner/domain/parent"
            ),
            "agent": (
                "Owned Conversation before run/key lookup; expected Relationship must equal "
                "Conversation binding; optional Person must equal owned Relationship Person; "
                "run/history SQL is owner/conversation filtered"
            ),
            "import": (
                "Owned Job lock before revision/state/target validation; Person and Relationship "
                "validated by owner and matching Person; History validates owned Relationship; "
                "cursor binds owner/relationship"
            ),
            "memory": (
                "Existing actor User; owned record/Person/Relationship; exact optional scope; "
                "owned challenge snapshot/count/expiry/consumption and owned receipt/key; "
                "cursor binds exact owner/filters"
            ),
            "public": "No resource IDs or caller data",
        }[group]
        for method in sorted(route.methods):
            operation = schema["paths"][path][method.lower()]
            guarded = (
                path == "/api/v1/memory/undo"
                or ("/deletions/" in path and path.endswith("/execute"))
                or path == "/api/v1/erasures/execute"
            )
            preparation = route.path.endswith("/prepare")
            response = operation.get("responses", {}).get(
                "200", operation.get("responses", {}).get("201", {})
            )
            body_schema = next(
                iter(operation.get("requestBody", {}).get("content", {}).values()), {}
            ).get("schema", {})
            definition = schema["components"]["schemas"].get(
                body_schema.get("$ref", "").rsplit("/", 1)[-1], {}
            )
            body_ids = [
                field
                for field in definition.get("properties", {})
                if field == "id" or field.endswith("_id")
            ]
            effect = "none"
            if method != "GET":
                if group == "resources":
                    effect = (
                        "Create one owned "
                        + path.rsplit("/", 1)[-1]
                        + " row, or replay exact reserved UUID without new side effects"
                    )
                elif group == "agent":
                    effect = (
                        "Owned AgentRun/user/assistant Messages; optional explicitly consented "
                        "scoped Memory; exact owner/conversation/key replay"
                    )
                elif group == "import":
                    effect = (
                        "Private random-key artifact and owned Job/speakers"
                        if path.endswith("chat-imports")
                        else "Owned atomic RelationshipMessage merge and durable receipt; "
                        "raw artifact cleanup"
                        if path.endswith("finalize")
                        else "Owned Job cancellation and raw artifact cleanup"
                        if path.endswith("cancel")
                        else "Owned Job binding/revision/readiness only"
                    )
                elif group == "memory":
                    effect = (
                        "Owner-only confirmation metadata, no deletion"
                        if preparation
                        else "Owned guarded primary Memory/undo deletion and receipt"
                        if guarded
                        else "Owner consent/pause state only"
                    )
                elif group == "erasure":
                    effect = (
                        "Owner-bound short-lived exact-snapshot challenge"
                        if preparation
                        else "Exact target Message removal, durable tombstone and receipt; "
                        "Memory preserved"
                    )
            result.append(
                {
                    "method": method,
                    "path": path,
                    "operation_id": operation["operationId"],
                    "classification": "Public Endpoint"
                    if public
                    else "Guarded Mutation Endpoint"
                    if guarded
                    else "Owner-scoped Endpoint",
                    "authenticated": not public,
                    "jwt_requirement": "none"
                    if public
                    else (
                        "fixed HS256 / sub(UUID), exp, iss, aud; service validates existing User "
                        "or owned FK-backed resource"
                    ),
                    "owner_source": "none"
                    if public
                    else "Verified AuthenticatedActor.user_id only",
                    "resource_id": [
                        p["name"] for p in operation.get("parameters", []) if p["in"] == "path"
                    ],
                    "body_resource_ids": body_ids,
                    "parent_resource_validation": parents,
                    "foreign_resource_response": "not applicable"
                    if public
                    else (
                        "owner-neutral not-found; foreign confirmation 409 indistinguishable "
                        "from unavailable; no foreign run/receipt ID"
                    ),
                    "sensitive_fields": "none"
                    if public
                    else (
                        "Owned public DTO only; content/answer/names/labels/keys and "
                        "subject/challenge owner IDs where existing contract allows. "
                        "No ORM/raw artifact/private evidence projection."
                    ),
                    "response_contract": response.get("content", {}),
                    "mutation_side_effects": effect,
                    "router": filename + "::" + route.endpoint.__name__,
                    "service_repository_review": service,
                    "regression_tests": []
                    if public
                    else [
                        "apps/server/tests/test_authorization_security.py",
                        {
                            "resources": "apps/server/tests/test_resource_api.py",
                            "agent": "apps/server/tests/test_phase4_idempotency.py",
                            "import": "apps/server/tests/test_import_api.py",
                            "memory": "apps/server/tests/test_phase6_e2e.py",
                            "erasure": "apps/server/tests/test_erasure.py",
                        }[group],
                    ],
                    "bearer_openapi": bool(operation.get("security")),
                }
            )
    result.sort(key=lambda item: (item["path"], item["method"]))
    operations = {
        (method.upper(), path)
        for path, methods in schema["paths"].items()
        for method in methods
        if method in {"get", "post", "put", "patch", "delete", "head", "options"}
    }
    if operations != {(item["method"], item["path"]) for item in result}:
        raise RuntimeError("Router inventory does not cover actual OpenAPI")
    return {
        "phase": "9E",
        "operations": len(result),
        "public": sum(not item["authenticated"] for item in result),
        "inventory": result,
    }


def check():
    actual = inventory()
    if actual != json.loads(TARGET.read_text("utf-8")):
        raise RuntimeError("Public authorization inventory drift")
    if actual["operations"] != 39 or actual["public"] != 3:
        raise RuntimeError("Unreviewed public API change")
    for item in actual["inventory"]:
        if item["authenticated"] and (
            not item["bearer_openapi"] or not item["service_repository_review"]
        ):
            raise RuntimeError("Sensitive operation lacks authentication or service review")
        for path in item["service_repository_review"] + item["regression_tests"]:
            if not (ROOT / path).is_file():
                raise RuntimeError("Missing authorization review reference")
    return actual


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.write:
        TARGET.write_text(
            json.dumps(inventory(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    else:
        result = check()
        print(f"PASS: {result['operations']} reviewed operations; {result['public']} public")
