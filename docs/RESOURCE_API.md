# Public resources and Agent history — Phase 8A

## Current Phase9F integration

Phase9F adds GET /api/v1/relationships/{relationship_id}/datasets with signed ownership, neutral404, limit1–100 and bound cursor. It lists canonical imported Jobs only, including nondeletable tombstones, metadata-only provenance/import receipt counts/current message count. Owner and parent are checked before paging, and the datasets cursor cannot cross owner/relationship/domain. OpenAPI40 preserves all original39 operations. See DatasetSummary/DatasetPage schemas and test_dataset_discovery.py.

## Current Phase9E boundary

Backend-only guarded Dataset/Conversation erasure is documented in [ERASURE_API](ERASURE_API.md).
OpenAPI now has39 operations; the original36 contracts are preserved. Deleted
Conversation history/Agent REST/SSE returns404; erased canonical Dataset finalize
returns409 `dataset_deleted`, including duplicate same-scope transcripts.
App History/Settings disclose the absence of self-service chat/import/account
erasure. Existing Memory controls do not erase either history domain. External
erasure requires authoritative history refresh/reopen to clear cached rows/cursors.

These ten operations close the resource prerequisites of Phase 8. Mobile is still
the local Phase 7 Demo; no client generation, session storage or network adapter
is delivered. Authority: `app/db/models/records.py`, existing Alembic revisions,
`app/db/repositories/records.py`, `resources.py`, `ResourceService`, and the actual
[OpenAPI generation input](contracts/openapi.json).

## Authentication and resource fields

Every operation uses the existing signed Bearer verifier and `AuthenticatedActor`.
The subject must exist in PostgreSQL. Request bodies and query parameters reject
extra fields, including `owner_user_id`, `user_id` and offset. The owner comes
solely from authentication. There is no token issuer or account creation route.
Missing/foreign detail IDs and foreign/missing binding targets have identical
404 `not_found` responses. No owner or internal metadata is returned.

Person has only `display_name`, owner, UUID and UTC creation/update timestamps.
Relationship has an owned `person_id`, required string `relationship_type` and
required string `status`, plus its owner/UUID/timestamps. The existing schema
does not allow null for type/status or constrain them to a product enum. Require
explicit caller labels, permit `unknown`, and infer no romantic type or state.
Conversation has an owner, nullable `relationship_id`, UUID and timestamps.
It has no Person, title or status column. Omitting or supplying null for the
relationship creates a generic Conversation; an owned relationship is optional.
Person is obtained separately through the Relationship, never guessed from text.
No FIU, demographic, inferred personality, score or structured Profile fields
are introduced. Foreign keys remain the authoritative same-owner binding guard.

## Operations and public DTOs

- `POST /api/v1/persons`: `PersonCreateRequest {id,display_name}` → HTTP 201
  `PersonResponse {id,display_name,created_at,updated_at}`.
- `GET /api/v1/persons`: `PersonPage {items,next_cursor}`.
- `GET /api/v1/persons/{person_id}`: owned `PersonResponse`.
- `POST /api/v1/relationships`: `RelationshipCreateRequest
  {id,person_id,relationship_type,status}` → HTTP 201 `RelationshipResponse
  {id,person_id,relationship_type,status,created_at,updated_at}`.
- `GET /api/v1/relationships`: `RelationshipPage {items,next_cursor}`.
- `GET /api/v1/relationships/{relationship_id}`: owned `RelationshipResponse`.
- `POST /api/v1/conversations`: `ConversationCreateRequest
  {id,relationship_id?}` → HTTP 201 `ConversationResponse
  {id,relationship_id,created_at,updated_at}`. Response relationship is required
  as a field and nullable as a value.
- `GET /api/v1/conversations`: `ConversationPage {items,next_cursor}`.
- `GET /api/v1/conversations/{conversation_id}`: owned `ConversationResponse`.
- `GET /api/v1/conversations/{conversation_id}/messages`: `AgentMessagePage
  {items,next_cursor}` containing only `AgentMessagePublicResponse
  {id,conversation_id,role,content,created_at}`, role `user` or `assistant`.

All timestamps are aware UTC instants. Responses are explicit Pydantic projections,
not ORM serialization. Message speaker/tool data, AgentRun internals, Memory
evidence, prompts, loaded references and hidden analysis are absent. There are no
resource update/delete endpoints in 8A.

## Creation and response-loss retries

All three POST bodies **require `id`: a fresh random UUID v4**, chosen for one
logical creation before the first HTTP request and retained on every retry.
It becomes the actual PostgreSQL resource primary key; a Mobile `demo-a` or
nickname is invalid. Generate a new ID only for a new explicit creation. This
policy avoids a new receipt table and does not use AgentRun idempotency storage.

The durable reservation is `(resource type, UUID)` within the existing global
primary key namespace. The owner is verified separately. Matching owner and
canonical creation fields return the original resource with HTTP 201 again,
including the same timestamps. Changed fields return 409
`resource_creation_conflict`, without altering the first row. A collision with
another owner's reserved ID returns generic 404 and exposes no foreign data.
The same UUID may identify different resource types; it cannot transfer ownership.

Canonical strings are NFC-normalized and trimmed. Display name is a strict
string of 1–120 input characters; type/status are 1–40. Blank labels, control
characters and invalid Unicode fail 422. A normalized label is the persisted
label. No identity matching or type inference occurs. Conversation omitted/null
association is the same canonical payload; changed association is a conflict.

A PostgreSQL transaction advisory lock derived from type/ID serializes duplicate
lookup and creation across workers and owners. Existing PK and composite FKs
remain the final database constraints. The service validates bindings, flushes
and projects the row, and commits before returning. Commit/flush failures roll
back, return a generic 503, and leave the same uncommitted ID available to retry.
Repository functions never commit. Resource calls invoke no Agent or provider.

Reservation lasts while the resource row remains, with no retry TTL or receipt
cleanup. Internal/future deletion removes this reservation; 8A makes no promise
of replay after deletion or of account-wide erasure. Phase 9 must define deletion
and retry tombstones before exposing those mutations. Existing resources can be
read, but clients must not reuse their IDs for a new creation.

## Bounded keyset pagination and concurrent reads

Each of the four new lists accepts `limit` 1–100 (default 30) and an optional
opaque `cursor` of 1–512 characters. Every response supplies `items` and nullable
`next_cursor`; there is no offset or unbounded variant. Resource and message lists
order by `created_at ASC, id ASC`. Queries fetch at most limit+1 rows; equal
timestamps use UUID ordering, preserving duplicate text as distinct occurrences.
The next page starts strictly after the last returned row.

Versioned opaque cursors carry position and a digest of owner/domain/parent scope,
with no raw owner field. Treat them as opaque, retain only for that scope and
clear on logout/scope/reset. Malformed, naive-time or cross-scope cursors fail
422 `invalid_cursor`. They are navigation values, not signed authorization;
every query still enforces the verified owner and owned parent. A forged position
can only change where the caller's own authorized list starts.

Each page observes committed rows in its own short transaction; no long-lived
snapshot or server cursor is held. Normal later appends appear after the previous
position. A running Agent's committed user input can be visible before its later
assistant commit. An exhausted page is exhausted at that read instant: refresh
from the first page to see new data. Concurrent late commits with earlier creation
timestamps, backfills or future deletions require a refresh; the API does not
promise a fixed multi-request snapshot. Existing committed equal-time rows exhaust
without loss/duplication, and tests verify reads hide uncommitted writes and then
continue through newly committed appends.

## Agent integration and separate domains

A Conversation created here immediately works with the existing Agent REST/POST
SSE endpoints. `expected_relationship_id` remains an assertion checked by
AgentService, not a binding or authorization override. These endpoints retain
their original request, response, progress, persistence and retry semantics.
History reads all bounded pages of the original Message table, independently of
AgentService's latest-20 execution input. Tool roles are excluded.

Imported `RelationshipMessage` remains on the separate
`GET /api/v1/relationships/{relationship_id}/messages` API with its original
historical timestamp/provenance ordering and 1–200 limit. Its self/person/system
senders never become Agent roles. Finalize only persists external chat and returns
a receipt; it does not create an Agent answer. AgentService does not read imported
rows. Imported-data analysis and public FIU/Profile DTOs remain absent. An eventual
analysis API requires explicit owned-source selection, size/provenance contracts,
user authorization and behavioral evaluation.

## Errors, generation and local development

Errors use `{"error":{"code":"...","message":"..."}}` without SQL, content
or credentials. Missing/invalid/expired/unknown-subject JWT: 401
`invalid_credential` with Bearer challenge. Missing verifier: generic 503
`authentication_unavailable`. Owned-resource failure: 404 `not_found`. Changed
creation: 409 `resource_creation_conflict`. Input/extra fields: 422
`validation_error`; cursor decoding/scope: 422 `invalid_cursor`. Storage: generic
503 `persistence_failure` or existing `database_unavailable`. All responses are
declared through the existing ErrorResponse schema, including generic 500.

`docs/contracts/openapi.json` is the **formal 8B generation input**. Export and
check do not need a database, real model key, signing key or ignored `.env`:

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked python scripts/export_openapi.py --write
uv --cache-dir .cache/uv --no-managed-python run --locked python scripts/export_openapi.py --check
```

Sorted UTF-8 JSON with a final newline is deterministic. The committed
`phase7d-openapi-baseline.json` stores canonical hashes of the actual pre-edit
26 operations, all their schemas and Bearer security at `ccabc98`. Audit requires
each old contract unchanged and exactly ten additions. Tests check deterministic
bytes, stable named DTOs, nullable fields, strict projections, bound limits and
uniform errors. No TypeScript output is generated here. SSE still requires its
separate V1 event contract; a generated text body is not a stream parser.

Development identity acquisition continues through `dev_auth_cli.py bootstrap`
and `token --user-id <UUID>` in **APP_ENV=development** only; the existing-user
token lasts 15 minutes. Keep the server signing secret private in ignored config.
A developer can manually supply that short-lived Bearer credential to the future
8B session setup; no Mobile signer, bundled JWT or public dev login endpoint is
added. Session entry/storage/expiry/logout are 8B; production account issuance,
registration, refresh/revocation and OAuth still need separate scope.

With TEST_DATABASE_URL targeting a separate psycopg `_test` namespace:

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked pytest -q apps/server/tests/test_resource_api.py apps/server/tests/test_resource_contract.py
uv --cache-dir .cache/uv --no-managed-python run --locked python apps/server/resource_api_demo.py
.\make.cmd verify
```

The demo creates a disposable migrated database, synthetic A/B users and a real
Uvicorn socket. Resources are created through signed HTTP, first responses are
discarded and matching retries return one row each. Owned lists/details, B's
owner-neutral denials, MockLLM Agent execution and repeated public history pages
are verified against committed PostgreSQL. Only the LLM is replaced; authentication
is not overridden. Output contains counts/status/roles, never tokens or chat text.
