# Phase 4A Agent Service

`AgentService` is the transport-independent application boundary around the
Phase 3 runtime. A caller supplies a trusted `AuthenticatedActor`, an existing
conversation ID, current message and optional expected relationship/person IDs.
The service returns a typed `AgentServiceResult` or raises a typed
`AgentServiceError`. It imports neither FastAPI nor HTTP objects.

## Actor and ownership

The authentication adapter verifies a credential, then calls
`actor_from_verified_identity(user_id)`. The actor constructor rejects ordinary
construction. The issuer function is a trusted Python composition boundary;
Phase 4B verifies signed Bearer credentials in the FastAPI adapter before
calling this issuer. Malicious in-process Python code remains outside the
HTTP trust boundary. Request bodies must never create actors.

The service loads `Conversation` under `actor.user_id` before writing anything.
A foreign conversation is refused with `conversation_forbidden`; a missing one
with `conversation_not_found`. It compares optional expected relationship and
person IDs with the conversation's owner-scoped relationship. The bound
relationship is passed to `AgentInput`, and the runtime memory adapter resolves
the person under the same owner. The service never trusts a caller-supplied
relationship to override the conversation. A denied request writes no message
or run and never calls the runtime.

## Execution and transactions

1. Transaction A reads at most 20 prior user/assistant messages in chronological
   order; it then writes the current user message and one `AgentRun`. The run
   moves `pending → running` and A commits.
2. The service calls `AgentRuntime.run(AgentInput)` with that same run ID. No
   service database session or transaction is open during this call. The Phase 3
   memory adapter may use its own short sessions.
3. Transaction B atomically stores the validated `AgentResult.final_answer` as
   an assistant message and moves the run to `completed`. No raw model output,
   prompt, analysis tree or hidden reasoning is stored.

Repository functions flush but never commit. `AgentService` owns A and B commit
and rollback through scoped SQLAlchemy transactions. The runtime knows nothing
about them. The user message remains after runtime failure; B records `failed`
and a bounded failure code, without an assistant message. Memory write failure
does not fail a successful answer: the result remains `completed`, and memory
status/warnings are returned to the caller.

If B fails after answer generation, the entire B transaction rolls back. A
fresh transaction attempts to mark the run `failed` with `persistence_failure`.
The caller receives `persistence_failure` with the run ID and recovery status
`failed` or `running_unknown`; it never receives a false success. A run left
running is observable for future reconciliation. There is no LLM/PostgreSQL
distributed transaction or automatic answer replay in this phase.

## History, result and errors

History uses the 20 latest committed messages with role `user` or `assistant`
from the owned conversation, ordered oldest to newest. It is read before the
current user message is inserted, so `AgentInput.message` appears only once.
No tool/system, other conversation or other user's messages enter the history.
The typed public result contains run ID, conversation ID, assistant message ID,
role and text, run status, memory status and bounded warning strings. It does
not expose ORM objects. Service errors expose stable categories for invalid
actor/input, missing/forbidden conversation, invalid scope, runtime failure and
persistence failure. Internal DB/provider exception strings are discarded.

## Streaming and persistent operations

`execute()` and `stream()` accept an optional client-generated `operation_key`.
Phase 4D persists it on AgentRun with an owner/Conversation unique constraint
and a request fingerprint. Transaction A checks for a matching operation under
the Conversation advisory lock before inserting a new Message. Completed
operations replay from the persistent Assistant Message and result summary;
running, failed, conflicting and unresolved operations never re-execute.
Omitting the key remains non-idempotent. See [Idempotency](IDEMPOTENCY.md) and
[ADR 0021](adr/0021-persistent-operation-idempotency.md).

Phase 4C adds `AgentService.stream()` over exactly one `AgentRuntime.stream()`
execution. Both service methods share the same owned Conversation preflight,
history snapshot, Transaction A, assistant commit and failure recovery helpers.
The streaming preflight runs before HTTP headers, and a PostgreSQL advisory
transaction lock plus active-run query rejects a second run on the same
Conversation with 409. The network handler never calls the graph or writes
records itself.

The stream commits the validated answer and completed run before emitting
`final_response`; optional memory work follows. Before that commit, client
disconnect closes the runtime and marks the run failed with
`client_disconnected`. After commit, disconnect keeps the answer and completed
run, while unfinished memory work is canceled. See
[Streaming API](STREAMING_API.md) and
[ADR 0020](adr/0020-streaming-transport-disconnect.md).

Streaming result metadata is finalized when optional memory work ends or the
stream closes. A same-key duplicate during this short window returns 409
instead of an incomplete replay. The replay stream contains only persisted
`final_response` and `completed` events.

## Run locally

With PostgreSQL and `TEST_DATABASE_URL` configured, run the direct service
integration tests and the disposable keyless demo:

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env pytest -q apps/server/tests/test_agent_service.py
uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env python apps/server/agent_service_demo.py
```

Both operate without FastAPI, external model credentials or Mobile. The demo
creates and drops a random test database after Alembic migration.
