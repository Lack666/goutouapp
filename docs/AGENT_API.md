# Phase 4B Agent REST API

Phase 6A adds signed memory control and inspection endpoints alongside this
Agent endpoint. See [Memory API](MEMORY_API.md). Their changes affect later
Agent recall and writes through the same PostgreSQL MemoryStore.

Phase 5D also exposes a separate authenticated import workflow at
`/api/v1/chat-imports` and paginated RelationshipMessage history. It uses the
same Bearer verifier but does not add imported history to Agent inputs or
invoke the Agent during upload/finalize. See [Import API](IMPORT_API.md).

Phase 4C also exposes a versioned POST SSE endpoint at
`/api/v1/conversations/{conversation_id}/agent-runs/stream`. It reuses the
same request schema and Bearer verifier while keeping this synchronous route
unchanged. See [Streaming API](STREAMING_API.md) for frames, preflight HTTP
errors, disconnect and persistence ordering.

`POST /api/v1/conversations/{conversation_id}/agent-runs` performs one
non-streaming `AgentService.execute()` call. It returns **200** when execution
and persistence finish. The URL treats a run as the resource being executed;
the response is a completed operation rather than an asynchronous creation
receipt. The endpoint contains no ownership query, history builder, memory
logic, database write or direct runtime call. The dependency layer lazily
builds one runtime and service per FastAPI app, then reuses that compiled graph.

The request is JSON with `message` (1–20,000 Unicode characters; whitespace
only, NUL and invalid Unicode are rejected). Optional
`expected_relationship_id` asserts the Conversation relationship; it cannot
override it. Optional `operation_key` is a client-generated, opaque 1–128
character retry key without whitespace or control characters. It is scoped to
the authenticated user and Conversation; the same key requires the same
logical request. Extra fields, including `user_id`, `person_id`, provider choice and
API keys, return the uniform validation envelope. The authenticated user ID
comes solely from the signed Bearer credential.

Success returns `run_id`, `conversation_id`, `status=completed`, an assistant
message `{id, role, content}`, `memory_status` and `warnings`. It contains
only the validated answer and public metadata, never AgentState, prompt,
history, references, analysis internals or hidden reasoning. Memory persistence
failure remains HTTP 200 with `memory_status=failed` and a warning.

All business and validation errors use `{"error":{"code":"...","message":"..."}}`.
Missing/invalid/expired credentials and unknown signed subjects return 401
with a Bearer challenge. Missing and foreign conversations return the same
404. Invalid request data returns 400 or 422. Agent runtime failure maps to
502; answer persistence failure maps to 503. Those 5xx envelopes may include
`run_id` and `recovery_status` (`failed` or `running_unknown`) for future
inspection. They never include provider, SQLAlchemy or secret details.

Phase 4D makes `operation_key` persistent across both endpoints. A completed
same-key request returns the original response without another Runtime call,
Message or Memory write. A changed payload returns 409
`idempotency_conflict`; a running operation returns 409
`operation_in_progress`; an unfinalized result returns 409
`operation_unresolved`. A failed operation remains failed; a new user attempt
requires a new key. Omit the key only when retry safety is unnecessary. See
[Idempotency](IDEMPOTENCY.md) for scope, normalization, replay and recovery.
The existing health, readiness and status endpoints remain public.

## Local development request

After `docker compose up -d postgres` and `alembic upgrade head`, configure
the JWT settings in ignored `.env`. Run `dev_auth_cli.py bootstrap`, then
`dev_auth_cli.py token --user-id <UUID>` as described in
[authentication](AUTHENTICATION.md). Start the server with `.\make.cmd dev`.
With the printed IDs and token in PowerShell variables:

```powershell
$body = @{ message = '有人正在伤害我' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/conversations/$conversationId/agent-runs" -Headers @{ Authorization = "Bearer $token" } -ContentType 'application/json' -Body $body
```

The default Mock provider has no queued answer for arbitrary manual calls.
Configure a real provider for manual conversational execution, or run the
offline demo below for a deterministic keyless success path.

## Offline REST demo

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env python apps/server/agent_rest_demo.py
```

The demo creates a disposable migrated PostgreSQL database, starts a real
local Uvicorn socket with a queued MockLLM, signs a short-lived synthetic JWT,
sends an HTTP request through the production verifier and Agent endpoint,
then reopens a database session to verify the user message, completed run and
assistant answer. It prints only IDs, status and persistence evidence, then
stops the server and removes the disposable database.
