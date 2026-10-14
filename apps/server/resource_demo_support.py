"""Anonymous signed credentials and HTTP resource helpers for 8A tests/demo only."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.repositories import records

SECRET = "phase8a-synthetic-secret-with-more-than-32-bytes"


def settings(engine, **overrides):
    return Settings(
        app_env="test",
        database_url=engine.url.render_as_string(hide_password=False),
        auth_jwt_secret=SECRET,
        auth_jwt_issuer="phase8a-test",
        auth_jwt_audience="phase8a-api",
        llm_provider="mock",
        _env_file=None,
        **overrides,
    )


def headers(owner, **claims):
    value = {
        "sub": str(owner),
        "exp": datetime.now(UTC) + timedelta(minutes=10),
        "iss": "phase8a-test",
        "aud": "phase8a-api",
        **claims,
    }
    return {"Authorization": "Bearer " + jwt.encode(value, SECRET, algorithm="HS256")}


def create_owners(engine):
    with Session(engine) as db, db.begin():
        return records.create_user(db).id, records.create_user(db).id


class ResourceFlow:
    def __init__(self, client, owner):
        self.client, self.owner = client, owner
        self.headers = headers(owner)
        # Establish signed admission before the resource business races. Cold
        # admission deliberately has a bounded lock wait and can return 503;
        # its fail-closed behavior is tested separately. Never retry or rewrite
        # a raced mutation response to satisfy the resource assertions.
        self.call("GET", "/persons", params={"limit": 1})

    def call(self, method, path, body=None, *, status=200, auth=None, params=None):
        response = self.client.request(
            method,
            "/api/v1" + path,
            headers=self.headers if auth is None else auth,
            json=body,
            params=params,
        )
        # Do not print failed response bodies, which could contain private content.
        assert response.status_code == status, f"Unexpected HTTP status {response.status_code}"
        return response.json()

    def person(self):
        return self.call(
            "POST", "/persons", {"id": str(uuid4()), "display_name": "Synthetic A"}, status=201
        )

    def relationship(self, person=None):
        return self.call(
            "POST",
            "/relationships",
            {
                "id": str(uuid4()),
                "person_id": (person or self.person())["id"],
                "relationship_type": "unknown",
                "status": "unknown",
            },
            status=201,
        )

    def conversation(self, relationship=None):
        return self.call(
            "POST",
            "/conversations",
            {
                "id": str(uuid4()),
                "relationship_id": relationship["id"] if relationship else None,
            },
            status=201,
        )

    def body(self, domain):
        body = {"id": str(uuid4())}
        if domain == "persons":
            body["display_name"] = "Synthetic A"
        elif domain == "relationships":
            body.update(
                person_id=self.person()["id"], relationship_type="unknown", status="unknown"
            )
        else:
            body["relationship_id"] = self.relationship()["id"]
        return body

    def pages(self, path, *, limit=7, cursor=None):
        items = []
        seen = set()
        while True:
            params = {"limit": limit}
            if cursor is not None:
                assert cursor not in seen, "Cursor did not advance"
                seen.add(cursor)
                params["cursor"] = cursor
            page = self.call("GET", path, params=params)
            assert len(page["items"]) <= limit
            items.extend(page["items"])
            cursor = page["next_cursor"]
            if cursor is None:
                break
        assert len(items) == len({row["id"] for row in items}), "Duplicate page occurrence"
        return items
