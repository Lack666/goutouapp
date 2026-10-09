# Phase 4D persistent Agent operation idempotency

Both Agent endpoints accept an optional client-generated `operation_key`. A
client that wants retry safety must generate a fresh key for one logical user
action, retain it across network retries, and use a new key for a new attempt.
An omitted key keeps the earlier non-idempotent behavior. A random UUID is a
good key; it must not contain a JWT, email, phone number or relationship text.
The key is opaque, 1–128 Unicode characters, and may not contain whitespace,
control characters, NUL or invalid UTF-8. The server does not put the key in
ordinary application logs or API responses.

## Scope and reservation

The scope is `(authenticated owner_user_id, conversation_id, operation_key)`.
The nullable PostgreSQL `agent_runs.operation_key` column has a unique
constraint over these three columns. Different owners and Conversations can
use the same textual key. A request fingerprint is SHA-256 of canonical JSON
containing owner, Conversation, NFC-normalized and trimmed message, supplied
`expected_relationship_id`, and supplied `person_id` when called directly via
the service. The normalized message is also the message executed and stored.
JWT, timestamps, generated run IDs and server metadata are excluded. The
fingerprint is not a substitute for owner authorization or the DB constraint.
Requests without an operation key retain their original message text.

Transaction A verifies the authenticated owner, takes a PostgreSQL advisory
transaction lock for the Conversation, then looks up the scoped operation
before creating any Message. A found key with a different fingerprint returns
409 `idempotency_conflict`. A matching key returns or rejects based on its
persistent status, with no new side effects. A new key then passes the existing
one-active-run check, creates one user Message and one AgentRun, and commits
both atomically. The unique constraint is the final arbitration guard even if
two server workers race. The advisory lock serializes the lookup and insert;
neither guarantee depends on an in-memory set.

## Status and replay policy

- `completed` with finalized result metadata: synchronous retry returns the
  original run ID, assistant Message, memory status and warnings from the DB.
  A streaming retry sends only versioned `final_response` then `completed`
  events. It invents no `run_started` or progress events. Both transports
  share `AgentService` lookup and can replay each other's completed run.
- `running`: return HTTP 409 `operation_in_progress` with the existing run ID
  before starting a stream. The client can retry later; V1 cannot attach to
  the live generator. A server crash between Transaction A and Runtime also
  leaves a `running` row. Because DB status alone cannot distinguish live from
  abandoned work across workers, the same 409 deliberately blocks it. The
  caller must not change the key to silently resume the same logical action.
- `failed`: never execute the same key again. Runtime failures retain the
  `agent_failure` category and run ID; answer persistence failures retain
  `persistence_failure`; `client_disconnected` returns 409
  `operation_failed`. A user-initiated new attempt requires a new key.
- A completed row missing its result snapshot returns 409
  `operation_unresolved`; no Runtime is invoked. During a normal stream this
  can occur briefly between answer commit and optional memory finalization.
  An unrecoverable metadata failure or crash can leave it unresolved until a
  future recovery process repairs it.
- A failed DB recovery update can leave the original row `running` while the
  caller observed `running_unknown`. A same-key retry therefore receives
  `operation_in_progress` and cannot duplicate the LLM execution. The generic
  reconciliation worker belongs to a future reliability phase.

The response snapshot stores only assistant Message ID, memory status and
public warning strings on `AgentRun`; it does not store HTTP blobs, SSE frames,
JWTs, prompts, internal AgentState or raw provider errors. The answer remains
in its existing Message row. Sync completion writes the snapshot with the
answer in Transaction B. Streaming commits the answer first, then finalizes
the optional memory summary. A disconnect after answer persistence preserves
the completed Run and attempts to finalize the last observed memory status.
An already committed memory write is never undone by a network disconnect.

## Retry guidance

For Mobile or another client, persist the chosen key with the pending UI
action before sending HTTP. If the connection is lost, resend the same body,
Conversation and key. A completed operation replays without charging another
Runtime execution or writing another Memory. A 409 `operation_in_progress`
means wait and retry the same key; `operation_unresolved` requires recovery.
A 409 `operation_failed` means the previous attempt ended. Show that outcome
and generate a new key only if the user chooses a new attempt. A 409
`idempotency_conflict` means the key was reused for different input; fix the
client's key handling.

No automatic age-based reset or background reconciliation is implemented.
An abandoned `running` operation also blocks a different-key Run on the same
Conversation under the Phase 4C one-active-run policy. See
[ADR 0021](adr/0021-persistent-operation-idempotency.md) and
[Phase 4D acceptance](PHASE_4D_ACCEPTANCE.md).

## Separate Phase 8A resource creation policy

Person/Relationship/Conversation creation does not use AgentRun operation keys.
Each POST requires a stable caller UUID v4 and compares canonical creation fields
under a PostgreSQL transaction lock; an existing matching row replays 201 and a
changed payload yields409. The existing resource PK is the reservation and lasts
with the row. There is no guarantee after future/internal deletion. See
[resource retry contract](RESOURCE_API.md#creation-and-response-loss-retries).
