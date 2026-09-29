# Phase 6A memory control API

Phase 3 owns the Agent's consent-gated memory runtime. Phase 6A adds a user
control plane: `AuthenticatedActor → MemoryControlService → SQLAlchemyMemoryStore
→ memory_controls / memory_records`. The Agent and API use the same store and
tables. Control requests never invoke the Agent, LLM or knowledge router.

All routes require the Phase 4 signed Bearer JWT. The owner is the verified
subject; request bodies cannot override it. Unknown signed users receive 401.
Foreign or missing Person/Relationship scopes receive the same 404 for each
resource type. A valid owned Person paired with a different owned Relationship
receives `invalid_scope` (400). Errors use the standard
`{"error":{"code":"...","message":"..."}}` envelope. Database failures
return `persistence_failure` (503) without SQL detail.

| Method | Path | Request | Response |
| --- | --- | --- | --- |
| GET | `/api/v1/memory/control` | none | `MemoryControlView` |
| POST | `/api/v1/memory/consent` | `{"enabled":true/false}` | `MemoryControlView` |
| POST | `/api/v1/memory/pause` | none | `MemoryControlView` |
| POST | `/api/v1/memory/resume` | none | `MemoryControlView` |
| GET | `/api/v1/memories` | optional `person_id`, `relationship_id`, `limit`, `cursor` | `MemoryListResult` |
| GET | `/api/v1/memories/{memory_id}` | owned memory UUID | `MemoryRecordView` or owner-neutral `memory_not_found` |

`MemoryControlView` includes `consent_enabled`, `paused`,
`effective_read_enabled`, `effective_write_enabled`, and nullable `updated_at`
(null until a control row exists). Effective fields are the durable control
gate; a particular Agent run must also have its `memory_enabled` feature flag.
Grant enables consent and preserves pause. Revoke disables consent, sets pause,
blocks future recall/write, and keeps records inspectable. Pause blocks recall
and write. Resume clears pause only while consent is enabled; it cannot grant
consent. These operations are safe to repeat. PostgreSQL locks the owner row
while changing controls so concurrent calls leave one valid durable row.
The final memory insertion takes the same owner lock and rereads durable
consent/pause state; a control change completed before that insertion blocks
it even when an Agent run began earlier.
The Agent's explicit save-consent phrase can itself grant consent under the
existing Phase 3 contract; API revoke blocks runs without a new explicit grant.

The list defaults to 20 and accepts 1–50 records. It orders by `created_at
DESC, id DESC`; an opaque cursor encodes those two keys. The next page starts
strictly after the last returned record, including equal timestamps. An absent
filter lists all owned memories. A Person filter lists records for that Person;
a Relationship filter lists records for that exact Relationship. Both filters
together must match. Inspections are read-only and work while paused or
revoked. `MemoryRecordView` returns ID, type, saved content, scope, source,
provenance summary and timestamps, without hash, operation history, raw
evidence, ORM metadata or hidden reasoning. The response warns that
historical saved information may no longer be accurate. Content is returned
only to its owner and is not
logged by these endpoints.

Undo and destructive deletion remain Phase 6B. Production retention duration,
backup handling and expiry remain Phase 6C. No mobile client is part of 6A.

Run the keyless demos with a disposable PostgreSQL test namespace:

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked python apps/server/memory_control_demo.py
uv --cache-dir .cache/uv --no-managed-python run --locked python apps/server/memory_control_http_demo.py
```

Set `TEST_DATABASE_URL` to a `postgresql+psycopg` URL whose database ends in
`_test`. The demos create and remove a separate migrated database. The HTTP
demo starts a local Uvicorn socket and signs a short-lived development JWT;
neither demo prints token or saved content.
