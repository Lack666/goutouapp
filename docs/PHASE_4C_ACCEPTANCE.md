# Phase 4C acceptance — Streaming Transport and Disconnect Policy

Date: 2026-09-28. **Status: PASS.** Phase 4C stops at one POST SSE transport;
Phase 4D persistent idempotency has not begun. Validation used an isolated
PostgreSQL 16 cluster in the ignored workspace `.cache` on localhost port
15433 because Docker Desktop's daemon was unavailable. The server was stopped
after verification.

## Protocol and application boundary

- `POST /api/v1/conversations/{conversation_id}/agent-runs/stream` uses the
  same signed Bearer dependency and request model as Phase 4B. Authentication,
  ownership and the one-active-run check finish before HTTP 200 headers, so
  invalid JWTs produce 401 with Bearer challenge, foreign/missing Conversation
  IDs share 404, and a busy Conversation produces 409. The synchronous REST
  endpoint remains available.
- `AgentService.stream()` shares the owned Conversation preflight, bounded
  history, Transaction A, answer commit and failure recovery helpers with
  `execute()`. It consumes exactly one `AgentRuntime.stream()` execution and
  creates exactly one persistent AgentRun. PostgreSQL advisory transaction
  locking and an active-run query guard the Conversation across independent
  service instances; no process-local set is used.
- Network frames are UTF-8 `text/event-stream` with `event:` and one `data:`
  JSON object, separated by a blank line. Every object has
  `schema_version="1"`, `event`, `run_id`, `data`. Typed public events are
  `run_started`, `status`, `final_response`, `memory_status`,
  `pending_confirmation`, `completed` and `failed`. The mapper excludes raw
  runtime state, prompts, references, history, memory contents, provider
  errors, DB URLs and credentials. All frames use the database run ID.
- The normal order is start, stable progress, validated answer, optional
  memory status, completion. The service commits Assistant Message and the
  completed AgentRun **before** sending `final_response`; therefore a client
  seeing `completed` can read both in a fresh database session. A failure
  after stream headers uses a typed terminal `failed` frame, not an impossible
  HTTP status change.

## Disconnect and failure decision

Before final persistence, closing the socket or generator cancels the runtime
and attempts to move the run from `running` to `failed` with
`failure_code=client_disconnected`. The user message remains; no assistant
message or memory write is made. A response-level finalizer covers a disconnect
after preflight and before the first frame. A failed DB update can leave the
existing `running_unknown` recovery condition.

After final persistence, disconnect leaves the completed run and assistant
message in place and cancels unfinished optional memory work. Already
committed memory remains committed. A memory failure while connected emits
`memory_status(failed)` followed by `completed`; it does not turn the answer
into a failure. The status vocabulary stays unchanged, so no migration is
required. These decisions are fixed in [ADR 0020](adr/0020-streaming-transport-disconnect.md).

## Commands and observed results

The test-only `DATABASE_URL` and `TEST_DATABASE_URL` were process-local values
pointing at separate development and `_test` namespaces on the isolated
cluster. The test fixture and demos created and dropped disposable databases.
No real LLM key was used.

- `uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env pytest -q apps/server/tests/test_agent_stream_contract.py apps/server/tests/test_agent_stream_api.py apps/server/tests/test_agent_stream_disconnect.py` — **15 passed**. This includes protocol round trips and arbitrary UTF-8 byte chunks; auth and foreign Conversation preflight; success, safety, runtime failure, persistence failure and memory failure; one-active-run 409; concurrent user/conversation and memory-scope isolation; cancellation before the first frame; and two real Uvicorn socket disconnect timings.
- `uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env python apps/server/agent_stream_demo.py` — **PASS**. A real HTTP client parsed each frame as it arrived: `run_started`, four `status` frames, `final_response`, `completed`. A fresh DB session queried at the moment `completed` arrived and found the completed AgentRun plus user and assistant messages.
- `uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env pytest -q apps/server/tests` — **310 passed** after the added cancellation and concurrent memory tests.
- `.\make.cmd verify` — **PASS** after final edits. It includes Alembic upgrade/downgrade/upgrade/check, frozen upstream and static Golden validation, Phase 2/3 regression, Phase 4A service and demo, Phase 4B signed REST tests and socket demo, Phase 4C tests and socket demo, full backend tests, repository secret boundary and Ruff check/format. The final gate says `PASS: all active Phase 0..3 and Phase 4A..4C gates`.
- `git diff --check` — **PASS** after final edits.

## Limits and deferrals

The stream reports runtime progress, **not LLM tokens**. The complete answer
appears in one validated final frame. V1 has no heartbeat; long silent model
calls may encounter intermediary idle timeouts. The serializer directly
iterates service events without an unbounded queue. A run left `running` after
an unrecoverable database failure blocks another run on its Conversation until
future reconciliation. Reconnection does not reuse an operation: **persistent
idempotency is deferred to Phase 4D**. WebSocket, Mobile, OAuth and RAG are not
implemented in Phase 4C.
