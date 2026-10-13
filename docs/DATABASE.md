# Phase 2B database operations

Phase9C revision20261013_01 adds resource_admission_states and upload_reservations;
17 application tables are checked through the existing disposable migration cycle.
Neither new table stores transcript/filename/token. Request-window/issuance/recovery
uses bounded advisory transactions; private OS fences prevent unsafe recycling
after DB backend loss. Default per-process pool5+10 now waits at most1s for checkout;
these are configurable and must be aligned with workers/DB capacity. Existing
deployment databases require the normal authorized Alembic upgrade before this
code receives data traffic; acceptance migrates only disposable synthetic DBs.

The root `compose.yaml` runs PostgreSQL 18.6 for local development. Set
`POSTGRES_*`, `DATABASE_URL` and `TEST_DATABASE_URL` through an ignored `.env`
or the shell. The committed `.env.example` contains **development-only** values.

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up -d postgres
uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env alembic upgrade head
.\make.cmd verify
```

`/health` is 200 when the process runs; `/ready` is 200 only when `SELECT 1`
against PostgreSQL succeeds, otherwise 503 with the generic error envelope.
App import and startup do not contact PostgreSQL. FastAPI lifespan disposes its
lazy database pool at shutdown. The database URL is masked in Settings repr and
never included in HTTP errors or app log messages.

Migrations live in `apps/server/alembic/versions`. To roll back the initial
schema **in a disposable database only**, set `DATABASE_URL` to that database
and run `alembic downgrade base`. Do not use `Base.metadata.create_all()` as a
deployment path. The verification gate runs a real CLI
`upgrade head` → `downgrade base` → `upgrade head` → `alembic check` against a
temporary test database and checks the expected tables after each migration step.
Phase 3G extends the expected schema with `memory_controls` and
`memory_records`; the same disposable migration cycle now checks all eight
tables. The memory adapter opens a fresh SQLAlchemy session per operation.
Same-owner composite foreign keys constrain person/relationship scope, and
owner/subject/type/content hash deduplicates writes. See [Memory](MEMORY.md).
Phase 3H adds `memory_operations`, making nine tables total. Its composite
owner/record foreign key cascades on hard deletion. Save and undo run in
separate, atomic per-operation transactions; history is capped at 20 entries
per owner. The migration gate checks the full nine-table upgrade/downgrade
cycle and `alembic check`.

Phase 6B revision `20260929_01` adds `memory_confirmations` and
`memory_mutations`. The first binds a short-lived destructive confirmation to
the owner, action, target, scope and record snapshot; the second stores a
durable receipt with a unique `(owner_user_id, operation_key)` retry key.
Neither table stores memory content. Active memory deletion and undo use the
same owner row lock as Agent writes, then change `memory_records`, cascading
`memory_operations`, and persist the receipt in one transaction. The migration
gate checks the expanded schema through the same cycle. See
[Memory Deletion](MEMORY_DELETION.md).

`TEST_DATABASE_URL` is a PostgreSQL connection template whose database name
must end in `_test` and differ from `DATABASE_URL`'s database name. Tests create
a random database from that template, apply Alembic, roll back each test's
outer transaction, and remove the database after pytest. The test role needs
`CREATEDB`. Database tests fail when the test URL is missing; they never fall
back to the development database. The verifier loads `.env` for uv commands
when it exists.

Schema relationships and delete semantics are specified in
[ADR 0006](adr/0006-postgresql-foundation.md). The six Phase 2B tables have UUID IDs,
`created_at` and `updated_at`. `Person`, `Relationship`, `Conversation` and
`AgentRun` have explicit owners; `Message` inherits ownership from its
conversation. The ORM connection uses UTC. Sensitive message content belongs
in the database, never in normal logs.

## Phase 4A AgentRun lifecycle

Alembic revision `20260928_01` adds nullable `started_at`, `completed_at` and
`failure_code` to the existing AgentRun table. Existing records remain valid.
The service creates `pending`, flushes `running` with a start time, and commits
with the user message before invoking the runtime. A separate transaction
stores the validated assistant message and `completed`, or only `failed` plus a
short failure code. The database row ID equals the runtime run ID. On answer
commit failure, the service rolls back the assistant and attempts a separate
failed-run update. An unrecoverable update leaves an observable running row and
returns a typed error. See [Agent Service](AGENT_SERVICE.md).

## Phase 4D AgentRun operation key

Alembic revision `20260928_02` adds a nullable operation key, SHA-256 request
fingerprint, user/assistant Message references, final memory status and public
warning list to AgentRun. A unique constraint on owner, Conversation and
operation key is the durable duplicate arbiter. Null keys remain allowed, so
legacy and deliberately non-idempotent runs are unaffected. A check constraint
requires key and fingerprint to be present together. Message IDs are foreign
keys; the result is reconstructed from the existing assistant Message, not a
saved HTTP response. See [Idempotency](IDEMPOTENCY.md) and
[ADR 0021](adr/0021-persistent-operation-idempotency.md).

## Phase 5B import workflow tables

Alembic revision `20260928_03` adds `chat_import_jobs` and
`chat_import_speakers`. They hold parser metadata, exact raw speaker labels,
counts and explicit bindings only. Composite foreign keys bind a job's
Relationship and a speaker's Person to the same owner; a speaker's owner and
job must also match. No final imported Message row is created. The migration
gate checks all eleven tables through upgrade/downgrade/upgrade and Alembic
check. See [Import Jobs](IMPORT_JOBS.md).

## Phase 5C relationship message history

Alembic revision `20260928_04` adds `relationship_messages`, separate from
Agent `messages`. It adds imported status/receipt fields to Jobs, a partial
unique index for imported owner/Relationship/transcript scopes, and composite
foreign keys for owner/Job/Relationship, Person compatibility and source
speaker provenance. `(import_job_id, source_index)` is the occurrence key.
The migration gate now checks twelve tables and the full reversible cycle.
See [Imported Messages](IMPORTED_MESSAGES.md).

## Phase 5D temporary source metadata

Alembic revision `20260928_05` adds `chat_import_artifacts` and a nullable,
unique Job artifact ID. A composite `(owner_user_id, artifact_id)` foreign key
prevents a Job from referencing another owner's source. The table stores only
metadata and an opaque key; bytes remain in private artifact storage. The
migration gate checks thirteen tables and the reversible cycle. Expiration
cleanup is an explicit service operation; it cannot delete formal
RelationshipMessages. See [Import Artifacts](IMPORT_ARTIFACTS.md).

## Phase 6B–6C memory mutation and expiry schema

Revision `20260929_01` added owner/key-unique `memory_mutations` durable receipts
and owner-bound `memory_confirmations`. Receipt confirmation IDs intentionally
have no FK requiring challenge retention. They store IDs/fingerprints/counts,
never saved content. Revision `20261008_01` adds non-null timestamptz `expires_at`
to `memory_records`, indexed for expiry cleanup, and indexes challenge expiry.
It backfills all existing rows to migration transaction time + 180 days, leaving
creation/update/control fields intact; no old row expires immediately. Subsequent
service writes supply configured creation-based expiry explicitly.

The migration gate checks all fifteen tables through upgrade/downgrade/upgrade/check.
Legacy-row regression separately migrates an old record forward. SQL recall/default
inspection require expiry > UTC now; direct owner inspection can see expired rows.
Cleanup locks owners before children, rechecks bounded IDs, deletes records and
cascades only their `memory_operations`, and removes challenges after expiry+grace.
Receipts and controls have no time cleanup. See [retention policy](MEMORY_RETENTION.md).

## Phase 8A public resource acquisition

No migration is added; the same fifteen tables, UUID primary keys and composite
owner bindings remain. Repository creation helpers accept an optional stable UUID
for the public service while preserving prior caller defaults. Required UUID v4
creation IDs become actual resource PKs; a transaction advisory lock serializes
same type/ID lookup, payload comparison and insert across workers. Existing PKs
and FKs remain final arbitration. Replay lasts with the row, without a new receipt
table or AgentRun reservation. New owner-scoped queries use bounded ascending
created_at/UUID keysets over existing resources and Agent Messages only.
See [resource contract](RESOURCE_API.md) and [ADR0031](adr/0031-public-resource-acquisition-and-retries.md).
