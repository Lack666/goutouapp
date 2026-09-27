# Phase 2C — LLM Provider Abstraction acceptance

Date: 2026-09-27. Status: **PASS**. Phase 2D has not started.

## Delivered

- `LLMProvider` is a typed internal protocol for `chat`, `stream`, and
  `structured_output`. Messages, results, token usage, and stream chunks have
  strict Pydantic models with no Agent-specific fields.
- `MockLLMProvider` uses independent queues for text, stream chunks, structured
  values, and predefined errors. It requires no API key, database, or network.
- One `OpenAICompatibleProvider` sends text Chat Completions through HTTPX.
  Base URL, API key, model, and timeout come from the existing Settings and
  factory. HTTPX is a runtime dependency in the root lockfile.
- Structured results are validated against the caller's Pydantic model. Bad
  JSON or schema mismatch raises a fixed project error. Provider-level SSE
  streaming returns normalized incremental chunks and closes the response.
- Fixed error classes distinguish configuration, authentication, provider
  rejection, timeout, rate limit, unavailability, invalid response, and invalid
  structured output. Raw upstream text, Authorization, request body, and
  hidden reasoning fields are not exposed by the provider.
- FastAPI startup, `/health`, `/api/v1/status`, and the existing `/ready`
  semantics do not depend on LLM availability. No LLM endpoint was added.

See [the provider guide](LLM_PROVIDER.md) and
[ADR 0007](adr/0007-llm-provider-boundary.md) for the boundary and limits.

## Evidence

All commands ran from the repository root on Windows. The checked-in `.env`
template supplied no LLM key; the ignored local `.env` supplied only Phase 2B
development/test PostgreSQL settings for inherited database checks.

- `uv --cache-dir .cache/uv --no-managed-python lock --offline` — PASS; root
  `uv.lock` resolves the runtime HTTPX dependency.
- `uv --cache-dir .cache/uv --no-managed-python run --locked pytest -q apps/server/tests/test_llm_mock.py apps/server/tests/test_llm_openai_compatible.py`
  — **31 passed** offline using deterministic queues and HTTPX MockTransport.
- `uv --cache-dir .cache/uv --no-managed-python run --locked python -c "import asyncio,sys; sys.path.insert(0,'apps/server'); from app.llm import LLMMessage,create_llm_provider; from app.core.config import Settings; p=create_llm_provider(Settings(llm_provider='mock',llm_api_key=None,_env_file=None)); p.queue_chat('mock-demo'); print(asyncio.run(p.chat([LLMMessage(role='user',content='synthetic demo')])).content)"`
  — actual keyless Mock factory/chat call printed `mock-demo`.
- `uv --cache-dir .cache/uv --no-managed-python run --locked pytest -q apps/server/tests --ignore=apps/server/tests/test_database.py`
  — **42 passed** without a database URL.
- `uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env pytest -q apps/server/tests/test_database.py`
  — **8 passed** against the disposable PostgreSQL test namespace.
- `.\make.cmd verify` — **PASS**. It ran 13 inherited repository/contract
  tests; frozen upstream validator; isolated Alembic `upgrade head`,
  `downgrade base`, `upgrade head`; 31 focused LLM tests; 50 backend tests
  including PostgreSQL; Golden validator (**81 cases**); secret boundary check;
  Ruff check and format check. Agent and Mobile gates remained deferred.
- `git -c 'safe.directory=F:/狗头军师app化/goutouapp' diff --check` — PASS.

One preliminary direct `pytest -q apps/server/tests` command omitted
`TEST_DATABASE_URL`: 42 tests passed and 8 inherited database fixtures could
not start. The subsequent `.\make.cmd verify` loaded the ignored `.env`, ran
those 8 database tests, and passed all 50 backend tests. A direct all-backend
test command must likewise use `uv run --env-file .env` or export a disposable
`TEST_DATABASE_URL`.

## Security and scope

Tests check redacted Settings/provider repr, fixed exception messages, absent
provider log output, and a status response without a key. The fake transport
verifies request construction without external calls. URL validation rejects
remote HTTP and embedded credentials. The repository secret gate passed.

The existing Golden Dataset and frozen `knowledge/goutoujunshi` tree were not
edited in Phase 2C. They had pre-existing uncommitted changes from earlier
phases when this work began; those changes were preserved. No LangGraph,
Agent, Knowledge Router, Memory, RAG, WebSocket, React Native, or business
chat endpoint was implemented.

## Limits and next stage

- Vendor-specific live compatibility was not tested because no real key or
  external network was used. JSON object mode is not a schema guarantee;
  local validation enforces the caller's schema. Tool calling and multimodal
  content are outside this text-only provider foundation.
- The current FastAPI/Starlette test stack emits one `httpx` deprecation
  warning; tests and all gates pass.
- Next: **Phase 2D — Backend Foundation Integration Verification**. This
  phase was not started.
