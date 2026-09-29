# Server — FastAPI, Agent Service and signed REST boundary

Phase 6A adds signed memory control and bounded inspection APIs over the same
durable MemoryStore used by the Agent. See [Memory API](../../docs/MEMORY_API.md).
The keyless PostgreSQL + MockLLM and local signed HTTP demos are:

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked python apps/server/memory_control_demo.py
uv --cache-dir .cache/uv --no-managed-python run --locked python apps/server/memory_control_http_demo.py
```

Phase 5D adds one-upload authenticated chat import, explicit speaker and
Relationship binding, artifact-backed finalization and bounded relationship
history. See [Import API](../../docs/IMPORT_API.md) and
[Artifact lifecycle](../../docs/IMPORT_ARTIFACTS.md). The local socket demo is:

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env python apps/server/import_api_demo.py
```

Phase 4A adds the Python-only `AgentService` for owner-scoped conversation,
message and AgentRun orchestration. It accepts a trusted typed actor and calls
the standalone runtime between two short database transactions. Phase 4B adds
one synchronous Agent HTTP endpoint at
`POST /api/v1/conversations/{conversation_id}/agent-runs`, requiring a signed
Bearer JWT. See [Agent Service](../../docs/AGENT_SERVICE.md),
[Authentication](../../docs/AUTHENTICATION.md) and
[Agent API](../../docs/AGENT_API.md).

Phase 4C adds one POST SSE endpoint at the same path with `/stream` appended.
It streams progress and one committed final answer, then completion; it does
not stream model tokens. See [Streaming API](../../docs/STREAMING_API.md).

Phase 4D adds PostgreSQL-backed operation-key idempotency shared by both
endpoints. A completed request can replay through either transport without
another Runtime execution. See [Idempotency](../../docs/IDEMPOTENCY.md) and
[Phase 4D acceptance](../../docs/PHASE_4D_ACCEPTANCE.md).

Keyless PostgreSQL + MockLLM demos for the direct service and real HTTP API:

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env python apps/server/agent_service_demo.py
uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env python apps/server/agent_rest_demo.py
uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env python apps/server/agent_stream_demo.py
```

This FastAPI service starts without a reachable PostgreSQL database or LLM key.
Phase 2B added persistence and database readiness. Phase 2C adds an internal,
keyless-testable LLM Provider boundary. Phase 2D verifies these layers together
and releases the database pool at application shutdown. The Agent endpoint is
the signed, synchronous REST route above.

## Setup and run

From the repository root:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
uv sync --locked
docker compose up -d postgres
uv run --locked --env-file .env alembic upgrade head
.\make.cmd dev
```

On this managed Windows workspace, uv's default cache and managed-Python
directories are not writable inside the sandbox. The repository verifier uses
a workspace cache and the installed Python automatically. For manual uv
commands here, use:

```powershell
uv --cache-dir .cache/uv --no-managed-python sync --locked
uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env alembic upgrade head
uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env pytest -q apps/server/tests
```

The server binds to `127.0.0.1:8000` by default. `GET /health` returns
`{"status":"ok"}`. `GET /api/v1/status` returns the service name, `running`
status and public environment name. `GET /openapi.json` exposes the same
versioned path. A status response means the HTTP process is running; it does
not assert database or model readiness. `GET /ready` returns 200 when PostgreSQL
responds to `SELECT 1`, otherwise a generic 503 error.

Run `.\make.cmd test` for inherited, LLM, database and integration tests,
`.\make.cmd lint` for Ruff, and `.\make.cmd verify` for all active Phase 0–3
and Phase 4 gates.
The database gate requires a separate `TEST_DATABASE_URL` ending in `_test`;
it creates and removes disposable databases and never uses the development DB.
The Python dependency versions are locked in the root `uv.lock`. The root
`pyproject.toml` declares runtime dependencies and a `dev` group for tests and
lint. No separate server lockfile is needed.

## Configuration

Copy root `.env.example` to root `.env` for local overrides. `.env` and
`.env.*` are ignored by Git; only `.env.example` is committed. Settings also
read process environment variables, which take precedence over `.env`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_ENV` | `development` | Public environment label (`development`, `test`, `staging`, `production`) |
| `APP_DEBUG` | `false` | Local debug logging and Uvicorn reload; traceback responses remain disabled |
| `APP_HOST` | `127.0.0.1` | Bind address |
| `APP_PORT` | `8000` | Bind port, validated to 1–65535 |
| `DATABASE_URL` | unset | psycopg PostgreSQL URL; connection is lazy |
| `TEST_DATABASE_URL` | unset | Test-only database namespace; never used by the app |
| `LLM_PROVIDER` | `mock` | `mock` or `openai_compatible`; selected only when the factory is called |
| `LLM_API_KEY` | unset | Required for `openai_compatible` calls, never for mock or startup |
| `LLM_BASE_URL` | unset | Compatible API prefix before `/chat/completions` |
| `LLM_MODEL` | unset | Model name required for `openai_compatible` calls |
| `LLM_TIMEOUT_SECONDS` | `30` | Per-operation timeout, validated to (0, 300] seconds |
| `AUTH_JWT_SECRET` | unset | Server-only HS256 signing key, at least 32 UTF-8 bytes for Agent REST |
| `AUTH_JWT_ISSUER` | `goutouapp` | Required JWT issuer claim |
| `AUTH_JWT_AUDIENCE` | `goutouapp-api` | Required JWT audience claim |
| `CHAT_IMPORT_ARTIFACT_ROOT` | `.cache/import-artifacts` | Private temporary raw source directory |
| `MAX_CHAT_IMPORT_BYTES` | `104857600` | Maximum uploaded file bytes, default 100 MiB |
| `CHAT_IMPORT_RETENTION_HOURS` | `72` | Expiration of unfinished upload artifacts |

`DATABASE_URL`, `LLM_API_KEY` and `LLM_BASE_URL` use Pydantic `SecretStr` and are never returned
by status endpoints. The app does not log request headers, query strings or
bodies. Uvicorn access logging is disabled. Unknown errors log a generic event
without exception text or traceback.

`TEST_DATABASE_URL` is read by the test fixture and migration verifier, not by
application Settings. `POSTGRES_*` variables belong to Compose. Runtime
settings use one Pydantic Settings class and have no duplicate names or config
library. An explicitly passed Settings instance can replace environment
values in tests.

The LLM layer never makes a request at server startup. To test it offline,
use `MockLLMProvider` queues or inject an `httpx.MockTransport` client into
`OpenAICompatibleProvider`. `structured_output` validates against a
caller-supplied Pydantic schema. `stream` yields provider-level async chunks;
there is no WebSocket. Run the focused suite with:

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked pytest -q apps/server/tests/test_llm_mock.py apps/server/tests/test_llm_openai_compatible.py
```

See [LLM Provider architecture](../../docs/LLM_PROVIDER.md) for the interface,
configuration, error taxonomy, JSON mode limits and secret handling.

## Dependency and lifecycle boundary

The HTTP application holds `Database(settings)` without connecting at import or
startup. `/ready` alone probes PostgreSQL. On shutdown, FastAPI lifespan
disposes the pool; request sessions commit or roll back and close. Outside HTTP,
code can pass `Database.session()` to `ConversationService` or repository
functions and own the transaction explicitly. `create_llm_provider(settings)`
returns the typed `LLMProvider` independently of FastAPI and database Sessions.
Its default HTTPX client closes per operation; an injected client is
caller-owned. Phase 2D smoke tests exercise these pieces together without an
Agent. See [ADR 0008](../../docs/adr/0008-backend-composition-lifecycle.md).

## Error contract

Basic HTTP errors use `{"error":{"code":"...","message":"..."}}`. A missing
route yields `not_found`/404, invalid request input yields
`validation_error`/422, and an unexpected failure yields
`internal_error`/500. Validation error input and custom exception detail are
not echoed. HTTP exception headers, including authentication challenges, are
preserved. Domain-specific error codes are deferred to their feature phases.

## Layout

- `app/main.py`: application factory and route assembly.
- `app/api/`: `/health`, `/ready`, `/api/v1/status`, and shared error handlers.
- `app/core/`: environment settings and minimal logging.
- `app/schemas/`: response models.
- `app/db/`: models, lazy session management and owner-scoped repositories.
- `app/llm/`: typed protocol, mock, compatible adapter, factory and errors.
- `app/services/`: narrow conversation service around repositories.
- `alembic/`: versioned schema migrations.
- `tests/`: endpoint, configuration, database and offline LLM boundary tests.
- `run.py`: Uvicorn launcher using `APP_HOST` and `APP_PORT`.

The app follows the official [FastAPI router](https://fastapi.tiangolo.com/tutorial/bigger-applications/),
[error handler](https://fastapi.tiangolo.com/tutorial/handling-errors/) and
[TestClient](https://fastapi.tiangolo.com/tutorial/testing/) patterns, and
[Pydantic Settings](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/)
for environment-backed configuration. [uv's project guidance](https://docs.astral.sh/uv/concepts/projects/sync/)
recommends keeping the generated lockfile with the project.

See [database operations](../../docs/DATABASE.md) and
[ADR 0006](../../docs/adr/0006-postgresql-foundation.md) for the schema,
ownership, delete behavior, migration commands and test isolation strategy.
