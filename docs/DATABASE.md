# Phase 2B database operations

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
