# Phase 4C Agent streaming API

`POST /api/v1/conversations/{conversation_id}/agent-runs/stream` accepts the
same JSON request and signed Bearer JWT as the synchronous Agent run endpoint.
It returns one `text/event-stream` response over HTTP. A fetch-compatible
client can POST and parse the response incrementally; browser `EventSource`
cannot issue this POST. The synchronous endpoint remains available.

## Version 1 wire contract

Each event is one UTF-8 SSE frame with `event: <name>`, `data: <one JSON
object>` and a blank line. The JSON object always has `schema_version: "1"`,
`event`, `run_id` and `data`. JSON escapes embedded newlines, so answer text
cannot split a frame. Each frame can be split into arbitrary network chunks;
clients must parse complete SSE frames, not treat a transport chunk as an
event. All frames in a request have the same run ID, matching the persistent
AgentRun ID.

Supported event names and `data` fields:

- `run_started`: empty object. The user message and running AgentRun are
  already committed.
- `status`: `status`, one stable product progress value from Phase 3H. Internal
  LangGraph node names are never sent.
- `final_response`: `assistant_message_id` and the fully validated `answer`.
  Both the assistant message and completed AgentRun are already committed
  before this frame is sent.
- `memory_status`: `status`, a bounded memory receipt status. It contains no
  stored memory collection or candidate text.
- `pending_confirmation`: `status: "pending_confirmation"` when the memory
  receipt requires confirmation; no write is implied.
- `completed`: `status: "completed"`, `assistant_message_id` and
  `memory_status`. This is sent only after the answer commit.
- `failed`: generic `code` (`agent_failure` or `persistence_failure`) and
  `recovery_status` (`failed` or `running_unknown`). It has no provider, SQL,
  prompt or credential detail.

The ordinary success order is `run_started`, one or more `status`,
`final_response`, optional `memory_status` or `pending_confirmation`, then
`completed`. A failure before final persistence ends with `failed` and no
`completed`. High-risk runs use only safety progress statuses; ordinary
analysis/planning/composing statuses are absent.

A completed same-key retry is a persisted replay. It sends only
`final_response` then `completed`, with the original run and assistant Message
IDs. It does not invent progress events or invoke the Runtime again. The
envelope remains protocol version `1`; this short event sequence identifies a
replay without a new flag. See [Idempotency](IDEMPOTENCY.md).

This is **runtime progress streaming**, not token-level LLM generation
streaming. The complete answer appears in one `final_response` frame after
validation and database commit. Version negotiation and heartbeat frames are
not supported in V1. The server iterates events directly without an unbounded
queue, so a slow consumer applies backpressure to generation at yield points.

## HTTP errors and ownership

Authentication, request validation, User existence, Conversation ownership,
relationship scope and active-run checks happen before HTTP 200/SSE headers.
The same Phase 4B verifier issues the actor; there are no query token or
trusted user headers. Missing, invalid and expired JWTs return the ordinary
401 JSON error with `WWW-Authenticate: Bearer`. Missing and foreign
conversations share the same 404 JSON envelope. One Conversation permits only
one active run across server workers; a second synchronous or streaming run
gets 409 `conversation_busy`. The guard uses a PostgreSQL transaction advisory
lock followed by an active-run query, never a process-local set.

For a supplied operation key, a matching running operation returns 409
`operation_in_progress` with its existing run ID before SSE starts; a changed
payload returns 409 `idempotency_conflict`. A failed or unresolved operation
also uses a normal pre-stream HTTP error. V1 cannot attach to another live
generator.

After HTTP 200 headers, runtime or answer-persistence failures are terminal
`failed` events. The status code cannot change. If the answer commit fails,
the service rolls it back and attempts to mark the run failed; an unrecoverable
database failure reports `running_unknown` with the run ID. The service never
emits `final_response` or `completed` for an uncommitted answer.

## Disconnect and memory policy

Before final answer persistence, a client disconnect or consumer cancellation
closes the Agent runtime iterator, cancels pending model work, and attempts to
mark the run `failed` with `failure_code=client_disconnected`. The user message
stays committed; no assistant message is written. The response wrapper also
handles disconnects between the preflight commit and the first frame.

The service commits the validated answer immediately when the runtime emits
its final-answer candidate, before optional memory work begins. After that
commit, disconnect does **not** undo the completed run or assistant message.
It cancels any unfinished optional memory work; a memory write that already
committed is retained. If memory work fails while the client remains connected,
the stream emits `memory_status(failed)` followed by `completed`. Optional
memory failure does not turn a committed answer into a failed run.

The status vocabulary remains `pending`, `running`, `completed`, `failed`;
`client_disconnected` is a failure code, so no schema migration is needed. A
rare database failure while marking a disconnected run may leave its status
unknown; no reconciliation endpoint is added here. Such an active row blocks
a new same-Conversation run until it is reconciled in a later reliability
phase.

After a precommit disconnect, the same key refers to the original failed run
and does not start another execution. After a postcommit disconnect, replay
uses the committed result once its memory summary has been finalized. A new
user attempt requires a new key. There is no WebSocket transport in Phase 4.

## Local run

With PostgreSQL and an ignored `.env` configured, the keyless demo starts a
real Uvicorn socket, signs a synthetic development JWT, reads each SSE frame
as it arrives, and queries PostgreSQL immediately on `completed`:

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env python apps/server/agent_stream_demo.py
```

The demo creates and drops a separate disposable `_test` database. The same
real-socket demo also performs a sync retry, a stream replay, and both
cross-transport replays with the original run IDs. The integration and
disconnect tests use signed credentials and real PostgreSQL:

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env pytest -q apps/server/tests/test_agent_stream_contract.py apps/server/tests/test_agent_stream_api.py apps/server/tests/test_agent_stream_disconnect.py
```
