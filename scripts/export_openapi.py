"""Offline deterministic generation and compatibility gate for the Phase 8B input."""

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/server"))

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

BASELINE = ROOT / "docs/contracts/phase7d-openapi-baseline.json"
SNAPSHOT = ROOT / "docs/contracts/openapi.json"
METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}
NEW_OPERATIONS = {
    (method, path)
    for domain in ("persons", "relationships", "conversations")
    for method, path in (
        ("post", f"/api/v1/{domain}"),
        ("get", f"/api/v1/{domain}"),
        ("get", f"/api/v1/{domain}/{{{domain[:-1] if domain != 'persons' else 'person'}_id}}"),
    )
} | {("get", "/api/v1/conversations/{conversation_id}/messages")}
NEW_OPERATIONS |= {
    ("get", "/api/v1/relationships/{relationship_id}/datasets"),
    ("post", "/api/v1/erasures/prepare"),
    ("post", "/api/v1/erasures/execute"),
    ("get", "/api/v1/erasures/receipts/{receipt_id}"),
}
DTO_FIELDS = {
    "DatasetSummary": {
        "dataset_job_id",
        "relationship_id",
        "source_format",
        "parser_version",
        "source_timezone",
        "first_timestamp_utc",
        "last_timestamp_utc",
        "imported_message_count",
        "current_message_count",
        "ignored_message_count",
        "system_message_count",
        "imported_at",
        "deleted_at",
        "deletable",
    },
    "DatasetPage": {"items", "next_cursor"},
    "PersonCreateRequest": {"id", "display_name"},
    "RelationshipCreateRequest": {"id", "person_id", "relationship_type", "status"},
    "ConversationCreateRequest": {"id", "relationship_id"},
    "PersonResponse": {"id", "display_name", "created_at", "updated_at"},
    "RelationshipResponse": {
        "id",
        "person_id",
        "relationship_type",
        "status",
        "created_at",
        "updated_at",
    },
    "ConversationResponse": {"id", "relationship_id", "created_at", "updated_at"},
    "AgentMessagePublicResponse": {"id", "conversation_id", "role", "content", "created_at"},
    **{
        name: {"items", "next_cursor"}
        for name in ("PersonPage", "RelationshipPage", "ConversationPage", "AgentMessagePage")
    },
}


def canonical(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def operations(spec):
    return {
        (method, path): operation
        for path, methods in spec["paths"].items()
        for method, operation in methods.items()
        if method in METHODS
    }


def fingerprints(spec):
    return {
        "operations": {
            f"{method.upper()} {path}": sha256(canonical(value)).hexdigest()
            for (method, path), value in operations(spec).items()
        },
        "schemas": {
            name: sha256(canonical(value)).hexdigest()
            for name, value in spec["components"]["schemas"].items()
        },
        "security_schemes": sha256(canonical(spec["components"]["securitySchemes"])).hexdigest(),
    }


def build_spec():
    # Explicit nulls override environment values; no production config/key/DB is needed.
    app = create_app(
        Settings(
            _env_file=None,
            app_env="test",
            database_url=None,
            auth_jwt_secret=None,
            llm_provider="mock",
            llm_api_key=None,
        )
    )
    spec = app.openapi()
    if app.state.database._engine is not None or app.state.agent_service is not None:
        raise RuntimeError("OpenAPI generation initialized a database or Agent")
    return spec


def audit(spec, baseline):
    actual = fingerprints(spec)
    for category in ("operations", "schemas"):
        for key, value in baseline[category].items():
            if actual[category].get(key) != value:
                raise RuntimeError(f"Phase 7D compatibility changed: {category} {key}")
    if actual["security_schemes"] != baseline["security_schemes"]:
        raise RuntimeError("Phase 7D Bearer security changed")
    expected_additions = {f"{method.upper()} {path}" for method, path in NEW_OPERATIONS}
    if set(actual["operations"]) - set(baseline["operations"]) != expected_additions:
        raise RuntimeError("Unexpected resource operation inventory")
    if len(baseline["operations"]) != 26 or len(actual["operations"]) != 40:
        raise RuntimeError(
            "Expected 26 preserved, ten resource, three erasure and one Dataset discovery operation"
        )
    schemas = spec["components"]["schemas"]
    for name, fields in DTO_FIELDS.items():
        schema = schemas[name]
        if set(schema["properties"]) != fields or schema.get("additionalProperties") is not False:
            raise RuntimeError(f"Unexpected public resource fields: {name}")
        for prop in schema["properties"].values():
            if not any(key in prop for key in ("type", "$ref", "anyOf", "enum", "const")):
                raise RuntimeError(f"Untyped public resource property: {name}")
        if name.endswith("Page"):
            if schema["properties"]["items"].get("maxItems") != 100:
                raise RuntimeError(f"Unbounded resource page: {name}")
    for method, path in NEW_OPERATIONS:
        operation = spec["paths"][path][method]
        if operation.get("security") != [{"BearerCredential": []}]:
            raise RuntimeError(f"Unsigned resource operation: {method} {path}")
        for code in ("401", "404", "409", "422", "503", "500"):
            schema = operation["responses"][code]["content"]["application/json"]["schema"]
            if schema != {"$ref": "#/components/schemas/ErrorResponse"}:
                raise RuntimeError("Missing uniform resource error contract")
    return len(actual["operations"])


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=SNAPSHOT)
    args = parser.parse_args()
    spec = build_spec()
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    count = audit(spec, baseline)
    output = canonical(spec)
    if args.check:
        if not args.output.is_file() or args.output.read_bytes() != output:
            raise RuntimeError(
                "OpenAPI snapshot is stale; review then run export_openapi.py --write"
            )
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(output)
    print(f"PASS: deterministic OpenAPI, {count} operations, all 26 Phase 7D contracts preserved")


if __name__ == "__main__":
    main()
