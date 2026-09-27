# Phase 2B acceptance — PostgreSQL Foundation

Date: 2026-09-27. Status: **PASS**. Phase 2 remains pending Phase 2C.

## Implemented

- PostgreSQL 18.6 development service in Compose, with configuration through
  environment variables and no production credentials in code.
- SQLAlchemy 2.1 models for User, Person, Relationship, Conversation, Message
  and AgentRun; UUID identifiers, UTC timestamps, owner fields and composite
  same-owner foreign keys. The narrow Conversation service and repository
  functions cover create/get/list/delete and message create/list.
- Lazy engine/session factory, request commit/rollback/close dependency,
  Alembic migration, `/ready` database probe and generic 503 response.
- A disposable `_test` database per pytest run, an outer rollback per test,
  and a separate disposable database for the Alembic CLI cycle.

## Real validation

| Command or probe | Result |
| --- | --- |
| `docker compose up -d postgres` | PASS; PostgreSQL 18.6 container created |
| `docker compose ps postgres` and `pg_isready` | PASS; healthy, localhost:5433 |
| `uv ... python scripts/check_db_migrations.py` | PASS; actual `alembic upgrade head`, `downgrade base`, `upgrade head` on empty temporary DB, table sets checked after each |
| `uv ... alembic upgrade head` on development DB | PASS |
| `uv ... alembic current` | `20260927_01 (head)` |
| `uv ... alembic check` | PASS; no new upgrade operations detected |
| `uv ... pytest -q apps/server/tests`, twice consecutively | PASS; 18/18 both times against PostgreSQL, including owner isolation, FK/delete semantics, transaction rollback and readiness |
| Live Uvicorn HTTP with DB up | `/health` 200, `/ready` 200, `/api/v1/status` 200 |
| Live Uvicorn HTTP after `docker compose stop postgres` | `/health` 200, `/ready` 503; container restarted afterward |
| `.\make.cmd verify` | PASS; 13 inherited tests, upstream validator, Alembic gate, 18 backend tests, 81-case Golden validator, secret boundary, Ruff |
| `git diff --check` | PASS |

The first database test attempt found that a no-database test still inherited
`DATABASE_URL` from the local `.env`; the test now clears that variable and the
full suite passes. A prior portable PostgreSQL run was used while Docker Desktop
was being recovered. The final gate above was executed against the Compose
service. Docker Desktop on this machine initially failed to update its profile
settings; starting it with an isolated ignored profile made the engine usable.
This is a local environment issue, not a repository dependency.

## Boundary and known issues

The root `.env` is ignored by Git; this run used a development-only copy of the
template. No Phase 1B Golden case or frozen upstream file was changed in this
phase. FastAPI TestClient currently emits one upstream Starlette deprecation
warning about `httpx`; tests and runtime behavior pass.

No authentication, Agent Runtime, LLM provider, memory, knowledge router,
RAG, WebSocket, mobile feature or full REST CRUD endpoint was implemented.
Next authorized stage: Phase 2C — LLM Provider Abstraction.
