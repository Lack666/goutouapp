# Standalone Agent Runtime streaming (Phase 3H)

`AgentRuntime.stream(agent_input)` is a transport-independent async iterator
of the discriminated Pydantic `AgentEvent` union in `app.agent.events`. It
executes the same compiled LangGraph as `AgentRuntime.run()` exactly once.
`AGENT_EVENT_ADAPTER` can validate JSON and restore any event. Every event
has a `type` and one `run_id`; a completed or failed event also validates that
its nested result/failure has the same ID.

- `run_started`: run ID.
- `status`: stable `ProgressStatus` value.
- `final_response`: complete validated answer.
- `memory_status`: typed memory decision and receipt, without stored content.
- `completed`: public `AgentResult`.
- `failed`: safe `AgentFailure`.

The product status vocabulary is `preparing`, `checking_safety`,
`understanding_request`, `loading_context`, `analyzing`, `planning`,
`composing` and `preparing_safety_response`. Internal Python node names are
not part of the public protocol. The high-risk branch announces safety/context
work and a safety response, not ordinary analysis or planning. On ordinary
success, order is `run_started → status* → final_response → memory_status? →
completed`; high risk ends after its final response, and failures end with one
`failed` event. Nothing follows a terminal event. A delete intent that needs
confirmation emits `memory_status` with `pending_confirmation`; an explicit
undo emits `undone` or `nothing_to_undo`.

The response and action nodes still use `LLMProvider.structured_output` and
project validation. **TOKEN-LEVEL GENERATION STREAMING: DEFERRED.** The runtime
emits the full validated answer in one `final_response` event. Provider-level
`LLMProvider.stream()` is a separate capability and is not forced into
structured nodes. Memory persistence happens after the answer. A store failure
becomes `memory_status(failed)` and a completed result with a generic warning,
so the answer survives.

Events contain no hidden reasoning, system prompt, loaded reference text,
full historical memory, raw provider object, SQL exception or credential.
`completed.result` is the existing public Agent result; it may include the
current turn's proposed memory candidate but never the loaded memory list.
The producer closes the LangGraph async stream on normal completion,
generator close or cancellation. Closing after `final_response` and before
`memory_status` stops work before persistence; the future network transport
must decide how to handle disconnects and retries.

The keyless standalone demo is:

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked python apps/server/agent_stream_demo.py
```

It prints only event types, stable statuses, a memory receipt status and the
single-write check. The Phase 3 E2E suite exercises ordinary, boundary,
high-risk, memory and parity paths. Phase 4 owns Agent Service composition,
FastAPI business endpoints, REST/WebSocket/SSE mapping, conversation and run
database orchestration, API idempotency and network-disconnect policy.
