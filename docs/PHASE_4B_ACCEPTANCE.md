# Phase 4B acceptance — REST API and Authentication Boundary

Date: 2026-09-28. **Status: PASS.** Scope stops at Phase 4B. The test server
used an isolated PostgreSQL 16 cluster in the ignored workspace `.cache` on
`127.0.0.1:15433`, since Docker Desktop's local daemon was unavailable.
`TEST_DATABASE_URL` pointed to a separate `_test` namespace; the fixtures and
demo created and dropped random disposable databases. No production service,
account or model credential was used.

## Authentication model and actor issuance

The business endpoint requires `Authorization: Bearer <JWT>`. FastAPI's HTTP
Bearer dependency extracts one credential; `JWTBearerVerifier` verifies its
HS256 signature against a fixed algorithm allowlist and requires `sub`, `exp`,
`iss` and `aud`. The configured issuer and audience must match, and `sub` must
parse as a UUID. The verifier returns `VerifiedIdentity`; the trusted adapter
issues `AuthenticatedActor`. The `AgentService` then checks that the User exists
before any Conversation work. An unknown signed subject returns a generic 401
and is never auto-created. Missing, malformed, expired, incorrectly signed or
invalid-claim credentials return 401 with `WWW-Authenticate: Bearer`; the
service has zero calls for rejected credentials.

The secret is server-only `SecretStr`, at least 32 UTF-8 bytes. Missing or short
configuration makes the business endpoint unavailable with a generic 503;
startup, `/health`, `/ready` and `/api/v1/status` stay outside JWT auth. There
is no trusted identity header, production token issuer, account creation or
OAuth bypass. The development-only CLI creates a local User/Conversation and
signs a 15-minute token only for an existing User under `APP_ENV=development`.

## REST contract and error mapping

`POST /api/v1/conversations/{conversation_id}/agent-runs` synchronously calls
`AgentService.execute()` once and returns HTTP 200 on completion. The endpoint
contains no ownership query, history assembly, database write, memory scope
logic or runtime call. The dependency layer lazily composes one runtime and
service per FastAPI app; the graph is not compiled per request.

The request accepts `message` (1–20,000 Unicode codepoints, nonblank, no NUL or
invalid Unicode), optional `expected_relationship_id` and optional
`operation_key` (1–128 characters). Extra fields such as `user_id`, `person_id`,
provider selection and arbitrary memory scope are rejected. Identity comes
only from the verified credential. Success returns run ID, conversation ID,
status, assistant message ID/role/content, memory status and warnings. It does
not expose ORM models, AgentState, prompts, references, analysis internals,
history or hidden reasoning.

The established `{"error":{"code":"...","message":"..."}}` envelope covers
validation and business failures. Missing and foreign Conversation IDs produce
the same owner-neutral 404, with no run, message or runtime side effect. A
runtime failure maps to 502; answer persistence failure maps to 503 and keeps
the run ID and `failed` or `running_unknown` recovery status when available.
Raw provider and database errors are omitted. Memory persistence failure still
returns HTTP 200 with a warning and a completed run. OpenAPI shows the Bearer
scheme on the Agent route; health, readiness and status routes are public.

`operation_key` passes through to the service, but **persistent idempotency is
deferred to Phase 4D**. A repeated HTTP request can create a second run.
Network streaming, SSE, WebSocket and disconnect policy are deferred to Phase
4C. The existing transport-independent runtime streaming tests still run.

## Commands and results

The following used process-local `DATABASE_URL` and `TEST_DATABASE_URL` pointing
to the isolated cluster. The checked-in `.env.example` retains an empty JWT
secret placeholder; no signed token or private key was committed.

- `uv --cache-dir .cache/uv --no-managed-python run --locked pytest -q apps/server/tests/test_auth_jwt.py apps/server/tests/test_agent_rest_contract.py` — **22 passed**. Real PyJWT signing and the production verifier exercised signature, expiration, claims, subject, spoofing, validation, Bearer challenge, OpenAPI and public health without a database.
- `uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env pytest -q apps/server/tests/test_agent_rest.py` — **25 passed** against real PostgreSQL. A valid signed token went through FastAPI, AgentService and MockLLM; a fresh session read persisted User Message, completed AgentRun and Assistant Message. Cross-user, unknown subject, runtime/persistence/memory failures and logging privacy were exercised.
- `uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env python apps/server/agent_rest_demo.py` — **PASS** over a real local Uvicorn HTTP socket: valid signature 200, incorrect signature 401, persisted roles `user` and `assistant`, completed run and matching answer in a new session.
- `dev_auth_cli.py bootstrap` and `dev_auth_cli.py token --user-id <local UUID>` — **PASS** on the isolated development database. The printed token was captured without logging and independently verified by `JWTBearerVerifier` for the created User.
- `uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env pytest -q apps/server/tests` — **295 passed**.
- `.\make.cmd verify` — **PASS**. This ran the Phase 0 static tests (**13 passed**), frozen upstream validation, Alembic upgrade/downgrade/upgrade/check, Phase 2 LLM and database tests, Phase 3 contracts/runtime/semantic/knowledge/analysis/action/memory/streaming/E2E replay gates, Phase 4A tests and demo, Phase 4B tests (**47 passed**) and socket demo, the full backend suite (**295 passed**), Golden validation (**81 cases**), repository secret boundary, Ruff check and format check. It ended with `PASS: all active Phase 0..3, Phase 4A and Phase 4B gates`.
- `git diff --check` — **PASS** after final edits; only Windows LF/CRLF conversion notices appeared.

## Architecture decision and limits

[ADR 0019](adr/0019-rest-authentication-boundary.md) records the fixed HS256
Bearer policy, HTTP 200 synchronous execution, per-app lazy composition,
owner-neutral 404 and deferred retry/streaming semantics. The signed-token
HTTP integration uses MockLLM and proves wiring and persistence, not live
model advice quality. Docker Desktop's local daemon was unavailable during
acceptance; the isolated portable PostgreSQL 16 server provided the real
PostgreSQL gate instead. No Phase 4C feature was implemented.
