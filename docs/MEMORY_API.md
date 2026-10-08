# Phase 6A–6B memory control API

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

## Phase 6B guarded mutations

The same signed Bearer JWT and owner-scoped error envelope apply. Mutation
requests never invoke an Agent, LLM or knowledge loader. See
[Memory Deletion](MEMORY_DELETION.md) for the full safety and retry contract.
The AgentRun sync and streaming routes return `pending_confirmation` for
conversational undo without mutating memory. Safety routing runs first. Public
undo uses the guarded route.

| Method | Path | Request | Response |
| --- | --- | --- | --- |
| GET | `/api/v1/memory/undo/preview` | none | `UndoPreview` |
| POST | `/api/v1/memory/undo` | `expected_operation_id`, `operation_key` | `MemoryMutationReceipt` |
| POST | `/api/v1/memory/deletions/one/prepare` | `memory_id`, `person_id`, `relationship_id` | `MemoryConfirmationChallenge` |
| POST | `/api/v1/memory/deletions/person/prepare` | `person_id` | `MemoryConfirmationChallenge` |
| POST | `/api/v1/memory/deletions/all/prepare` | required `revoke_consent_after_delete` boolean | `MemoryConfirmationChallenge` |
| POST | `/api/v1/memory/deletions/{confirmation_id}/execute` | `operation_key` | `MemoryMutationReceipt` |
| GET | `/api/v1/memory/mutations/{mutation_id}` | none | owned receipt |

Undo preview gives the current latest reversible new-record insertion ID and
scope, without changing history. Undo must name that expected operation and
provide a valid operation key. A changed latest operation yields `stale_undo`;
no operation yields `undo_unavailable`. The same key and request replay the
durable receipt, including after the memory disappears. A new request with a
reused key yields `mutation_conflict`.

A prepare call writes only an owner-bound confirmation challenge. It gives
action, target/scope, expected affected count and a five-minute expiry; it
never returns saved content. A successful execute atomically consumes the
challenge, deletes the confirmed primary-store records, clears affected undo
history and writes a receipt. A changed record snapshot yields
`confirmation_stale`; an expired challenge yields `confirmation_expired`;
missing or foreign challenge yields `confirmation_required`. The challenge
cannot be reused for a new mutation. The same operation key and challenge
replay the first receipt. These errors use HTTP 409; missing owner-scoped
records/persons/receipts use 404, invalid operation keys use 400, and masked
storage errors use 503. Pydantic validation errors use 422.

`MemoryMutationReceipt` reports mutation ID, key, action, status, count, target
scope, timestamp and `replayed`. `primary_store_only=true` states the deletion
boundary. It contains no saved content. Delete-all leaves consent as it was
when `revoke_consent_after_delete=false`; `true` also revokes consent and
pauses memory access in the same transaction. Revocation alone keeps records.
Phase 6C adds fixed expiration and a documented backup policy; see below.
The mobile client remains Phase 7.

Run the keyless demos with a disposable PostgreSQL test namespace:

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked python apps/server/memory_control_demo.py
uv --cache-dir .cache/uv --no-managed-python run --locked python apps/server/memory_control_http_demo.py
uv --cache-dir .cache/uv --no-managed-python run --locked python apps/server/memory_destructive_control_demo.py
uv --cache-dir .cache/uv --no-managed-python run --locked python apps/server/memory_destructive_http_demo.py
```

Set `TEST_DATABASE_URL` to a `postgresql+psycopg` URL whose database ends in
`_test`. The demos create and remove a separate migrated database. The HTTP
demo starts a local Uvicorn socket and signs a short-lived development JWT;
neither demo prints token or saved content.

## Phase 6C additive public retention fields

`MemoryRecordView` additionally returns UTC `expires_at`, `state` (`active` or
`expired`) and `retention_policy_summary`. `MemoryListResult` includes the summary
even when empty. Existing fields and routes remain intact. Default lists exclude
expired records; owned GET-by-ID shows their expired state until physical cleanup.
Pause/revoke still allow inspection. Expired records are never recallable.
An expired latest undo preview is unavailable; an expected undo target that expires
fails `undo_unavailable`, or `stale_undo` after cleanup exposes an older operation.
It never falls back to deleting the older target. Deletes still cover selected
primary records including expired rows awaiting maintenance.

The default new-record policy is 180 days from creation, without recall renewal;
legacy records get 180 days from migration. Changing Settings affects new saves
only. There is no user retention Settings UI or maintenance HTTP endpoint.
Receipts replay after their challenge is physically cleaned, with no retry cutoff
while owner and metadata remain intact. See [retention policy](MEMORY_RETENTION.md)
and [backup/deletion policy](MEMORY_BACKUP_DELETION_POLICY.md). Primary deletion does
not promise immediate backup/provider erasure.
