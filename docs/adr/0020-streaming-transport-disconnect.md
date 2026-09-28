# ADR 0020 — One SSE transport and persistence-first completion

Date: 2026-09-28. Status: accepted for Phase 4C.

## Decision

Use POST plus `text/event-stream` as the sole V1 network streaming transport.
The endpoint awaits `AgentService.stream()` preflight before returning the
response, so authentication, validation, ownership and the active-run guard
can still use normal HTTP errors. The service shares Transaction A, answer
commit and failure recovery helpers with synchronous `execute()`. It consumes
one `AgentRuntime.stream()` iterator and projects its safe events into a
versioned, narrow SSE envelope. No WebSocket or token-level model stream is
exposed.

The service persists the validated final answer and completed AgentRun in one
transaction **before** emitting `final_response`. Optional memory work then
continues. A memory failure yields a failed memory status and a successful
`completed` event because the answer is already durable. A precommit runtime
or database failure yields `failed`; `completed` is never sent for an
uncommitted answer. Once headers are sent, failure is an event, not an HTTP
status change.

Before answer persistence, disconnect closes the runtime iterator and marks
the run failed with `client_disconnected`; no assistant message is saved. A
response-level finalizer also covers disconnect before the generator's first
iteration. After answer persistence, disconnect leaves the run completed and
cancels unfinished optional memory work. Already committed memory is retained.
No `cancelled` run status or migration is needed. Database recovery failure
can leave `running_unknown`, as in Phase 4A.

Only one active run is allowed per Conversation for both synchronous and
streaming requests. Transaction A obtains a PostgreSQL transaction advisory
lock keyed by Conversation UUID, checks for an existing running run, then
commits a new run. A second request receives owner-neutral 409
`conversation_busy` before SSE begins. This works across processes without a
mutable in-memory lock. A run left running after an unrecoverable database
failure blocks a new run until future reconciliation; this is an explicit
limit, not a retry or idempotency guarantee.

V1 sends no heartbeat. It directly awaits the next runtime event and yields
one complete SSE frame at a time, without an unbounded queue. Long model calls
may therefore encounter intermediary idle timeouts; a future transport
revision can add content-free comments. Persistent operation-key deduplication
remains Phase 4D work.
