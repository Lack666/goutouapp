"""Signed real PostgreSQL discovery, canonical identity, scope and pagination."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_erasure import erasure_api as _erasure_api
from test_erasure import execute, prepare
from test_upload_security import bind, finalize, headers, transcript, upload

from app.main import create_app

erasure_api = _erasure_api


def test_discovery_survives_new_client_and_never_lists_ready_duplicate(erasure_api):
    _engine, client, a, b, job, *_ = erasure_api
    path = f"/api/v1/relationships/{a[2]}/datasets"
    duplicate = bind(client, a[0], upload(client, a[0], content=transcript(4)).json(), a[1], a[2])
    receipt = finalize(client, a[0], duplicate).json()
    assert receipt["dataset_job_id"] == job["id"]
    with TestClient(create_app(client.app.state.settings)) as reconnected:
        page = reconnected.get(path, headers=headers(a[0])).json()
    assert len(page["items"]) == 1 and page["next_cursor"] is None
    row = page["items"][0]
    assert row["dataset_job_id"] == job["id"] != duplicate["id"]
    assert row["relationship_id"] == str(a[2])
    assert row["imported_message_count"] == row["current_message_count"] == 4
    assert row["deletable"] and row["deleted_at"] is None
    assert row["source_format"] == "wechat_markdown_v1" and row["imported_at"]
    assert not {"content", "raw_speaker_label", "owner_user_id", "storage_key"} & row.keys()
    assert client.get(path, headers=headers(b[0])).status_code == 404
    assert (
        client.get(path.replace(str(a[2]), str(uuid4())), headers=headers(b[0])).status_code == 404
    )
    assert client.get(path).status_code == 401
    execute(erasure_api, prepare(erasure_api, "dataset"))
    # Discovery retains a truthful historical receipt, never an executable live target.
    row = client.get(path, headers=headers(a[0])).json()["items"][0]
    assert row["dataset_job_id"] == job["id"]
    assert row["current_message_count"] == 0 and row["imported_message_count"] == 4
    assert row["deletable"] is False and row["deleted_at"] is not None


def test_discovery_keysets_are_bound_to_owner_relationship_and_domain(erasure_api):
    _engine, client, a, b, job, *_ = erasure_api
    for n in (2, 3):
        ready = bind(client, a[0], upload(client, a[0], content=transcript(n)).json(), a[1], a[2])
        assert finalize(client, a[0], ready).status_code == 200
    path = f"/api/v1/relationships/{a[2]}/datasets"
    other_relationship = str(uuid4())
    assert (
        client.post(
            "/api/v1/relationships",
            headers=headers(a[0]),
            json={
                "id": other_relationship,
                "person_id": str(a[1]),
                "relationship_type": "unknown",
                "status": "unknown",
            },
        ).status_code
        == 201
    )
    cursor, ids = None, []
    for _ in range(3):
        response = client.get(
            path,
            params={"limit": 1, **({"cursor": cursor} if cursor else {})},
            headers=headers(a[0]),
        )
        assert response.status_code == 200
        page = response.json()
        ids += [row["dataset_job_id"] for row in page["items"]]
        if cursor:
            assert (
                client.get(
                    f"/api/v1/relationships/{other_relationship}/datasets",
                    params={"cursor": cursor},
                    headers=headers(a[0]),
                ).status_code
                == 422
            )
            assert (
                client.get(
                    f"/api/v1/relationships/{b[2]}/datasets",
                    params={"cursor": cursor},
                    headers=headers(b[0]),
                ).status_code
                == 422
            )
            assert (
                client.get(
                    "/api/v1/persons", params={"cursor": cursor}, headers=headers(a[0])
                ).status_code
                == 422
            )
        cursor = page["next_cursor"]
    assert len(set(ids)) == 3 and job["id"] in ids and cursor is None


@pytest.mark.parametrize("query", [{"limit": 0}, {"limit": 101}, {"cursor": "bad"}])
def test_discovery_rejects_invalid_page(erasure_api, query):
    _, client, a, *_ = erasure_api
    assert (
        client.get(
            f"/api/v1/relationships/{a[2]}/datasets", params=query, headers=headers(a[0])
        ).status_code
        == 422
    )
