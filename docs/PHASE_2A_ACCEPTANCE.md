# Phase 2A acceptance — FastAPI Backend Foundation

Date: 2026-09-26.

PHASE: Phase 2A — FastAPI Backend Foundation

STATUS: PASS

## Implemented

- Built `apps/server/app` with an application factory, unversioned
  `GET /health`, versioned `GET /api/v1/status`, v1 router, response schemas,
  shared error handlers, Pydantic Settings and minimal logging.
- Added `APP_ENV`, `APP_DEBUG`, `APP_HOST`, `APP_PORT`, `DATABASE_URL`,
  `LLM_PROVIDER` and `LLM_API_KEY` to the environment-backed settings and root
  `.env.example`. Database URL and API key are optional masked secrets. No
  database or model connection occurs at startup.
- Added a Uvicorn launcher and integrated backend pytest and Ruff into
  `.\make.cmd verify`. The root uv project now has a generated `uv.lock`.
  `completed_phase` remains 1 because the full Phase 2 database gate is not
  built; only `completed_subphase` is `2A`.
- Preserved all uncommitted Phase 1B work that existed at the start of this
  phase. No Golden Case or frozen upstream file was changed by Phase 2A.

## Tests

- `uv --cache-dir .cache/uv --no-managed-python run --locked pytest -q apps/server/tests`:
  **9 passed**. Covered both routes, API versioning/OpenAPI, defaults and
  environment override, secret masking, invalid config, 404/400/422/500
  envelopes, auth header preservation, log redaction and idempotent logging.
- `.\make.cmd lint`: **PASS**. Ruff `check` and `format --check` covered the
  server and updated verifier; 21 Python files formatted.
- Tests used FastAPI's in-process `TestClient`. They required no PostgreSQL,
  external network or real LLM key.

## Validation and real demo

- `uv --cache-dir .cache/uv --no-managed-python lock`: resolved **26** packages.
  `uv --cache-dir .cache/uv --no-managed-python sync --locked`: installed the
  locked packages. Network access for these uv operations was approved after
  the sandbox blocked PyPI; no package was installed into the frozen upstream.
- `.\make.cmd dev` with `APP_PORT=8766`: Uvicorn reported startup complete and
  listened on `127.0.0.1:8766`. A real localhost request returned HTTP 200 and
  `{"status":"ok"}` for `/health`; `/api/v1/status` returned HTTP 200 and
  `{"service":"goutoujunshi-server","status":"running","environment":"development"}`.
  `/openapi.json` returned HTTP 200. The process was stopped after the demo.
- `.\make.cmd verify`: **PASS** — 13 inherited Phase 0/1 unit tests, frozen
  upstream validator, 81-case Golden validator, backend pytest, Ruff and the
  repository secret check. PostgreSQL, Agent and Mobile gates were explicitly
  deferred and not counted as passed.
- `git check-ignore -v .env .env.local`: both matched `.gitignore`.
  `git diff --name-only -- knowledge/goutoujunshi`: empty. The upstream
  inventory/hash test passed. `git diff --check`: PASS (exit code 0).

## Architecture decisions

The root uv project owns one lockfile; the server is a transport layer that can
start without later services. Tests inject settings into `create_app`, while
Uvicorn imports the module-level app. `/health` is liveness only; status does
not claim DB or LLM readiness. `APP_DEBUG` does not enable traceback responses.
The error envelope is `{"error":{"code":"...","message":"..."}}` and is
documented in OpenAPI. Request input and exception details are not echoed or
logged; Uvicorn access logging is disabled. See
[ADR 0005](adr/0005-fastapi-foundation.md).

## Files changed for Phase 2A

`.env.example`, `Makefile`, `project-phase.json`, `pyproject.toml`, `uv.lock`,
`scripts/verify.py`, `apps/server/README.md`, `apps/server/run.py`,
`apps/server/app/__init__.py`, `apps/server/app/main.py`,
`apps/server/app/api/__init__.py`, `apps/server/app/api/health.py`,
`apps/server/app/api/errors.py`, `apps/server/app/api/v1/__init__.py`,
`apps/server/app/api/v1/router.py`, `apps/server/app/api/v1/status.py`,
`apps/server/app/core/__init__.py`, `apps/server/app/core/config.py`,
`apps/server/app/core/logging.py`, `apps/server/app/schemas/__init__.py`,
`apps/server/app/schemas/error.py`, `apps/server/app/schemas/status.py`,
`apps/server/app/services/__init__.py`, `apps/server/tests/test_api.py`,
`apps/server/tests/test_config.py`, `apps/server/tests/test_errors.py`,
`docs/MASTER_PLAN.md`, `docs/ARCHITECTURE.md`,
`docs/adr/0005-fastapi-foundation.md`, and this report.

## Known issues

- The current FastAPI/Starlette `TestClient` emits one deprecation warning
  about HTTPX versus HTTPX2; all tests pass. The test transport choice can be
  revisited when the official FastAPI testing guidance changes.
- Uvicorn startup is verified, but PostgreSQL readiness and Agent availability
  are outside Phase 2A. There are no models, migrations, business endpoints,
  WebSockets or Mobile features.
- This managed Windows sandbox denied uv's default external cache and network
  locations. A workspace cache, installed Python and approved PyPI access
  allowed lock/sync. The documented `uv sync --locked` remains the ordinary
  command outside that sandbox.

NEXT: Phase 2B — PostgreSQL Foundation, under a separate instruction. Stop
after Phase 2A.
