# ADR 0017: Typed progress stream over the single Agent graph

Status: accepted for Phase 3H (2026-09-27)

## Decision

`AgentRuntime.stream()` iterates the same compiled LangGraph used by `run()`
with LangGraph update events. It executes the graph once and publishes a small
typed public event vocabulary: start, product-level progress status, validated
final response, optional memory receipt, and one terminal completed or failed
event. The runtime maps internal node names to stable status values; no node
payload, prompt, reference text or historical memory is streamed. The final
answer is emitted only after the response node's structured-output validation.
High-risk runs use the dedicated safety response and never announce ordinary
analysis, planning or composing.

## Rationale and limits

Maintaining structured Safety, FIU, Analysis, Action and Response validation is
more important than token-by-token display. Token-level generation streaming
is deferred; `final_response` carries the complete validated answer once.
`run()` and `stream()` use the same compiled graph and the same result builder
and failure mapping. Each event carries one run ID, including failures. Memory
is an after-response side effect: failure is a memory status and completed
answer, not a failed Agent run. Explicit async-generator close and task
cancellation close the underlying graph stream. Closing before persistence
means the memory write may not occur; Phase 4 must define network-disconnect
orchestration. No HTTP, SSE or WebSocket contract is introduced here.
