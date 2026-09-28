# Phase 4D acceptance — persistent idempotency and Phase 4 final gate

Date: 2026-09-28. **Status: PASS.** Phase 4 is accepted as an engineering API
gate. This stage stops before Phase 5. Validation used a disposable
PostgreSQL 16 cluster on localhost port 15433 because the Docker Desktop
daemon was unavailable. The cluster lives in ignored workspace `.cache`,
and was stopped after verification. No real model key or external account
was used.

## CODE

- Alembic revision `20260928_02` adds nullable operation key and request
  fingerprint, Message references, memory status and public warning snapshot
  to AgentRun. PostgreSQL enforces a unique owner/Conversation/key tuple and
  paired key/fingerprint presence. Null keys retain the Phase 4A–4C behavior.
- `AgentService.execute()` and `stream()` share one owner-scoped operation
  lookup. Transaction A takes a PostgreSQL advisory transaction lock, compares
  the canonical fingerprint before any Message insert, then creates the user
  Message and AgentRun atomically only for a new key. The database constraint
  arbitrates concurrent workers.
- A completed sync retry reconstructs the same typed result from the
  persistent Assistant Message and bounded AgentRun summary. A completed SSE
  retry emits only version 1 `final_response` and `completed` using the
  original run and assistant IDs. There is no saved HTTP blob, SSE event log,
  second Runtime call, or second Memory pipeline.
- Different payloads return 409 `idempotency_conflict`. A matching running
  row returns 409 `operation_in_progress`; a failed row retains its failure
  category or returns 409 `operation_failed` after client disconnect. A
  completed row lacking finalized summary returns 409
  `operation_unresolved`. All include the original run ID and stay before
  SSE headers. No key auto-reexecutes after an uncertain outcome.

## TEST and Phase 4 E2E

The new signed API/PostgreSQL E2E suite covers:

1. Signed JWT → synchronous REST → Service → Runtime → durable answer.
2. Signed JWT → SSE progress → durable final answer → completion, with the
   inherited Phase 4C socket/integration tests.
3. Sync → sync same-key replay with identical response.
4. Stream → stream replay with only persisted final/completed events.
5. Sync → stream and stream → sync cross-transport replay.
6. Same key with changed message or relationship expectation → 409 and no
   new side effect.
7. Eight simultaneous same-key requests against real PostgreSQL → one
   execution, user Message, assistant Message and AgentRun; another key
   respects the one-active-run 409 guard.
8. Real Uvicorn socket precommit disconnect → failed
   `client_disconnected`; same-key retry returns the old failure.
9. Memory save failure → completed answer; cross-transport replay remains
   completed. A successful Memory write also stays at one record after HTTP
   retry.
10. Foreign user → owner-neutral 404; same textual key works independently
    for different users and Conversations.

Further checks cover the database unique constraint, normalized fingerprint,
opaque key validation, keyless message-text regression, a live running
duplicate and SSE reconnect, operation-key log privacy, failed replay, an
unresolved result, and simulated
`running_unknown` recovery failure that blocks same-key re-execution.

## DOC and DEMO

[Idempotency](IDEMPOTENCY.md) defines key scope, fingerprint, retry guidance,
all terminal states and recovery limits. [ADR 0021](adr/0021-persistent-operation-idempotency.md)
records the database arbitration and cross-transport choice. Agent Service,
REST, streaming, architecture, database, master plan and server README were
updated.

`apps/server/agent_stream_demo.py` starts a real Uvicorn socket, signs a
synthetic JWT, streams events frame by frame with MockLLM, and checks
PostgreSQL as `completed` arrives. It then demonstrates stream → sync,
stream → stream, sync → sync and sync → stream replay. Its observed output
reported one Run per operation, the same sync response, and replay event
sequences `final_response, completed`.

## REGRESSION and observed commands

Process-local `DATABASE_URL` and `TEST_DATABASE_URL` pointed at separate
development and `_test` namespaces on the isolated cluster. Tests and demos
created and removed additional disposable databases.

- `uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env pytest -q apps/server/tests/test_phase4_idempotency.py` — **17 passed**.
- Phase 4C protocol/API/socket suite — **16 passed**.
- Full `apps/server/tests` suite — **328 passed**.
- `apps/server/agent_stream_demo.py` — **PASS**, including local sync retry
  and stream replay over the real network socket.
- `.\make.cmd verify` — **PASS**: migration
  upgrade/downgrade/upgrade/check; Phase 0–3 frozen source, Golden and Mock
  replays; Phase 4A Service, 4B signed REST, 4C SSE/disconnect and 4D
  idempotency gates; full backend; repository secret boundary; Ruff
  check/format. Final line: `PASS: all active Phase 0..4 gates`.
- `git diff --check` and staged-file secret boundary check — **PASS**.

## Architecture limits

A crash after Transaction A can leave `running`; a same-key request remains
blocked with 409 because database status cannot prove liveness across
workers. A crash or DB failure after the answer commit but before the optional
memory summary is finalized can leave a completed operation returning 409
`operation_unresolved`. Repair requires future reconciliation; this phase
never risks a second Runtime execution to guess the outcome. V1 SSE has no
heartbeat, live-generator attachment or token-level model streaming. Phase 4
does not include Mobile, Chat Import, OAuth, RAG or production reliability.

The Phase 4D instruction names Phase 5 as Chat Import and Relationship Data
Pipeline. The master plan records that future ordering, moving the earlier
memory-control deliverable to Phase 6. No Phase 5 implementation began.
