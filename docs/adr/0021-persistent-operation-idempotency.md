# ADR 0021 — One durable operation key across REST and SSE

Date: 2026-09-28. Status: accepted for Phase 4D.

## Decision

Store the optional client `operation_key` and deterministic request
fingerprint on `AgentRun`, with PostgreSQL uniqueness over owner, Conversation
and key. The key is nullable so requests without it preserve earlier behavior.
Transaction A locks the Conversation, checks for a matching operation before
creating a user Message, then applies the one-active-run guard. This order
gives first-writer-wins across server workers and prevents duplicate side
effects. The unique constraint remains the final database arbiter.

`AgentService.execute()` and `AgentService.stream()` call the same preflight
and replay logic. A completed operation is reconstructed from its persistent
Assistant Message and bounded result metadata. SSE replay emits only
`final_response` and `completed`; no prior progress log is stored or faked.
The protocol version stays `1` with no new event type. A matching running
operation returns 409 with its run ID. A failed operation never automatically
re-executes; a new user attempt needs a new key. A changed fingerprint returns
409 even if the old operation completed.

The Phase 4C stream commits its validated answer before optional memory work.
The result summary is finalized when memory work ends or the stream closes.
During that window a duplicate gets 409 instead of an incomplete replay. If
the summary cannot be finalized, `operation_unresolved` blocks replay rather
than re-running the Agent. If failure recovery leaves a row `running`,
`operation_in_progress` similarly fails closed: PostgreSQL status does not
prove whether a worker is still alive. Reconciliation is deferred.

The schema adds only operation key/fingerprint, Message references, memory
status and public warnings. It stores neither transport response blobs nor
private Runtime state. No Redis, distributed queue, WebSocket attach or
background worker is introduced.
