# Phase 2D — Backend Foundation Integration Verification

Date: 2026-09-27. Status: **PASS**. Phase 2 Backend Foundation: **PASS**.
Phase 3 Agent and Phase 7 Mobile gates: **DEFERRED**.

## Integration and boundaries

The FastAPI transport, PostgreSQL persistence and LLM Provider abstraction
coexist in one backend without a product chat endpoint. Settings is the sole
application configuration entry point. `TEST_DATABASE_URL` is read only by
the isolated test fixture and migration gate; `POSTGRES_*` belongs to Compose.
The app builds a lazy `Database(settings)` and does not open PostgreSQL or LLM
connections at import/startup. `app/api/dependencies.py` adapts a database
Session to FastAPI requests. Repositories/services, `Database`, and both LLM
Providers have no FastAPI Request dependency. LLM Providers have no database
Session dependency. Future Python code can receive Settings, a scoped Session
or service, and `LLMProvider` explicitly, without importing `app.main`.

FastAPI lifespan disposes its database pool at shutdown. Request sessions
commit/roll back and close through `get_db`; non-HTTP callers own their
transaction. The compatible Provider closes each default HTTPX client and
leaves an injected client to its owner. No background task is created.
`/health` stays process liveness; `/ready` probes PostgreSQL only.

## Automated evidence

Commands ran from the repository root on Windows, with an ignored `.env`
containing development and separate `_test` PostgreSQL URLs. No real LLM key or
external model request was used.

- `uv --cache-dir .cache/uv --no-managed-python sync --locked --offline` — PASS;
  checked the existing root lockfile without changing dependency versions.
- `uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env pytest -q apps/server/tests/test_backend_integration.py`
  — **7 passed**: online/offline DB, keyless Mock operations, compatible fake
  transport, DB + Mock message commit, non-HTTP dependency composition, and
  combined secret boundary.
- `uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env pytest -q apps/server/tests/test_database.py`
  — **8 passed** against a disposable migrated test database. Inherited tests
  cover ownership, foreign keys, commit/rollback and readiness.
- `.\make.cmd verify` — **PASS**. It ran 13 repository/contract tests, the
  frozen upstream validator, isolated Alembic upgrade/downgrade/upgrade/check,
  32 focused LLM tests, 7 smoke tests, the full backend suite, Golden validator
  (**81 cases**), repository secret gate, Ruff check and Ruff format check.
- `git -c 'safe.directory=F:/狗头军师app化/goutouapp' diff --check` — PASS.

The migration gate creates a randomly named `_test` database, runs the real
Alembic CLI `upgrade head`, `downgrade base`, `upgrade head`, and `check`, then
removes it. `alembic check` reported `No new upgrade operations detected.`
No migration file or schema model was changed in Phase 2D.

## Actual local startup demo

1. `docker compose up -d postgres` — PASS; existing container was running.
2. `uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env alembic upgrade head`
   — PASS on the development database.
3. `.\make.cmd dev` — Uvicorn started on `127.0.0.1:8000`; it was stopped after
   the requests, and no listener remained on port 8000.
4. `Invoke-WebRequest` against that process returned:
   `/health` **200** `{"status":"ok"}`;
   `/ready` **200** `{"status":"ready"}`;
   `/api/v1/status` **200** with `status: running` and `environment: development`.

## Configuration, privacy and dependency audit

The application Settings names match `.env.example`: `APP_ENV`, `APP_DEBUG`,
`APP_HOST`, `APP_PORT`, `DATABASE_URL`, `LLM_PROVIDER`, `LLM_API_KEY`,
`LLM_BASE_URL`, `LLM_MODEL`, and `LLM_TIMEOUT_SECONDS`. DB URL, model key and
base URL are masked `SecretStr` values. Tests show no database password, LLM
key or Authorization token in status/error output or the application log.
`.gitignore` still excludes `.env`, `.env.*`, caches and local log files.
The root uv project has one settings library, one HTTP client library, one
PostgreSQL driver and one ORM. `pytest` and `ruff` remain development-only;
there was no dependency upgrade or extra lockfile.

## Cleanup and limits

Moved the HTTP-specific `get_db` dependency out of `app/db/session.py` and
added shutdown disposal. Updated Master Plan, Architecture, database and LLM
guides, server README and ADRs to match the final boundaries. No Golden case
or frozen upstream file was edited in this phase. Their pre-existing
uncommitted changes from earlier phases were preserved.

The installed FastAPI/Starlette test stack emits one HTTPX deprecation warning;
all tests pass. Vendor live compatibility remains unverified without a real
key/network, as intended. Phase 3A — Agent State and Runtime Contracts is the
recommended next stage and was not started.
