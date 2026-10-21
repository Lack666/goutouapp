"""Offline schema/compatibility checks for the generation input, without DB/model keys."""

import json
from copy import deepcopy

import pytest

from scripts.export_openapi import (
    BASELINE,
    NEW_OPERATIONS,
    SNAPSHOT,
    audit,
    build_spec,
    canonical,
    operations,
)


def test_deterministic_keyless_snapshot_preserves_prior_26_operations():
    first, second = build_spec(), build_spec()
    assert canonical(first) == canonical(second) == SNAPSHOT.read_bytes()
    assert audit(first, json.loads(BASELINE.read_text(encoding="utf-8"))) == 43
    lifecycle = [
        key for key in operations(first) if key[1].startswith("/api/v1/lifecycle-erasures")
    ]
    assert len(lifecycle) == 3
    assert all(
        first["paths"][path][method]["security"] == [{"BearerCredential": []}]
        for method, path in lifecycle
    )
    assert (
        len(
            [
                key
                for key in operations(first)
                if not key[1].startswith(("/api/v1/erasures", "/api/v1/lifecycle-erasures"))
                and not key[1].endswith("/datasets")
            ]
        )
        == 36
    )


@pytest.mark.parametrize(
    "change", ["old_route", "old_schema", "security", "new_private_field", "unbounded_page"]
)
def test_contract_audit_rejects_drift_and_private_or_untyped_expansion(change):
    spec = deepcopy(build_spec())
    if change == "old_route":
        del spec["paths"]["/api/v1/chat-imports"]["post"]
    elif change == "old_schema":
        spec["components"]["schemas"]["CreateAgentRunRequest"]["properties"]["message"][
            "maxLength"
        ] = 50
    elif change == "security":
        spec["components"]["securitySchemes"] = {}
    elif change == "new_private_field":
        spec["components"]["schemas"]["AgentMessagePublicResponse"]["properties"]["evidence"] = {}
    else:
        del spec["components"]["schemas"]["AgentMessagePage"]["properties"]["items"]["maxItems"]
    with pytest.raises(RuntimeError):
        audit(spec, json.loads(BASELINE.read_text(encoding="utf-8")))


def test_new_operation_requests_success_nullable_and_page_contracts():
    spec = build_spec()
    schemas = spec["components"]["schemas"]
    names = {"persons": "Person", "relationships": "Relationship", "conversations": "Conversation"}
    for domain, name in names.items():
        path = spec["paths"][f"/api/v1/{domain}"]
        assert path["post"]["requestBody"]["content"]["application/json"]["schema"] == {
            "$ref": f"#/components/schemas/{name}CreateRequest"
        }
        assert path["post"]["responses"]["201"]["content"]["application/json"]["schema"] == {
            "$ref": f"#/components/schemas/{name}Response"
        }
        assert "id" in schemas[name + "CreateRequest"]["required"]
        assert schemas[name + "CreateRequest"]["properties"]["id"]["format"] == "uuid4"
        params = {param["name"]: param["schema"] for param in path["get"]["parameters"]}
        assert params["limit"]["minimum"] == 1 and params["limit"]["maximum"] == 100
        assert params["cursor"]["anyOf"][0]["maxLength"] == 512
    assert "relationship_id" not in schemas["ConversationCreateRequest"]["required"]
    assert schemas["ConversationCreateRequest"]["properties"]["relationship_id"]["anyOf"][1] == {
        "type": "null"
    }
    assert schemas["ConversationResponse"]["properties"]["relationship_id"]["anyOf"][1] == {
        "type": "null"
    }
    assert {"person_id", "relationship_type", "status"} <= set(
        schemas["RelationshipCreateRequest"]["required"]
    )
    assert schemas["AgentMessagePublicResponse"]["properties"]["role"]["enum"] == [
        "user",
        "assistant",
    ]
    assert (
        len(
            [
                key
                for key in NEW_OPERATIONS
                if not key[1].startswith(("/api/v1/erasures", "/api/v1/lifecycle-erasures"))
                and not key[1].endswith("/datasets")
            ]
        )
        == 10
    )
    assert len([key for key in NEW_OPERATIONS if key[1].startswith("/api/v1/erasures")]) == 3
    assert (
        len([key for key in NEW_OPERATIONS if key[1].startswith("/api/v1/lifecycle-erasures")]) == 3
    )
    assert len(NEW_OPERATIONS) == 17
    assert (
        len(
            {
                op
                for op in NEW_OPERATIONS
                if not op[1].endswith("/datasets")
                and not op[1].startswith("/api/v1/lifecycle-erasures")
            }
        )
        == 13
    )
