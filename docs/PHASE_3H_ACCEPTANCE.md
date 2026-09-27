# Phase 3H acceptance — Runtime Streaming and Phase 3 Final Acceptance

Date: 2026-09-27

## PHASE / STATUS

**Phase 3H — Runtime Streaming & Phase 3 Final Acceptance: PASS.** The Phase 3
transport-independent Agent Runtime meets CODE, TEST, DOC, DEMO and REGRESSION
gates. `project-phase.json` is `completed_phase=3`, `completed_subphase=3H`.

## MEMORY CONTRACT AUDIT / UNDO STATUS

`SKILL_CONTRACT.md` §8 explicitly includes “撤销最近更新” under MUST user
controls. Frozen upstream
`references/practical/长期记忆与关系档案.md` §用户控制 describes `undo`, and frozen
`scripts/memory_store.py` implements `command_undo`, caps operation history at
20 and clears history on object hard deletion. Phase 3G's undo deferral was
therefore a Contract gap and has been closed. `MemoryService.undo_last` now
reverses the owner's latest newly inserted record, including after a new SQL
session and while paused. Duplicate saves create no operation; hard deletion
removes affected operations. The owner/record composite foreign key and
PostgreSQL transaction protect scope and atomicity. One undo returns `undone`;
an empty history returns `nothing_to_undo`. With older operations remaining,
another unkeyed undo intentionally reverses the next one. See
[ADR 0016](adr/0016-memory-undo.md).

## RUNTIME STREAM API / EVENT CONTRACT

`AgentRuntime.stream(AgentInput)` is a transport-independent async iterator
using the same compiled LangGraph, result builder and failure mapping as
`run()`. It executes the graph once. The discriminated, strict Pydantic event
union is JSON round-trippable and includes `run_started`, stable `status`,
validated `final_response`, optional `memory_status`, and exactly one terminal
`completed` or `failed`. All events carry the same run ID; nested terminal
values must match it. No internal node name, prompt, hidden reasoning,
reference text, historical memory collection, provider object, secret or raw
exception is emitted. See [Streaming runtime](STREAMING_RUNTIME.md) and
[ADR 0017](adr/0017-runtime-streaming.md).

**TOKEN-LEVEL GENERATION STREAMING: DEFERRED.** The final response arrives as
one event after structured Action/Response validation; progress is streamed
before it. This preserves the existing safety and answer contracts.

## RUN / STREAM PARITY / SAFETY STREAM / MEMORY STREAM

Deterministic Mock fixtures produced semantically equal `AgentResult` values
through `run()` and `stream()` (excluding fresh run IDs). The ordinary stream
orders `run_started → status* → final_response → memory_status? → completed`.
The high-risk stream uses only safety/context statuses and the dedicated safety
response; it does not execute Analysis, Action or ordinary Response nodes.
Boundary refusal retains `stop_contact`. A failed memory save arrives after
`final_response` as `memory_status(failed)` and still ends in `completed` with
the answer intact. Delete intents yield typed `pending_confirmation`; explicit
undo yields its actual reversal receipt. Provider/runtime failures end in a
safe correlated `failed` event.

## CANCELLATION / CLEANUP

Tests cancel a consumer while a Mock provider is blocked and explicitly close
the generator before safety. The underlying graph iterator closes, the model
call receives cancellation, no extra provider call occurs and no memory write
is made. Closing after the answer but before memory persistence can stop that
side effect; future network transport must define disconnect behavior.

## FULL E2E

The eight standalone, keyless complete-pipeline cases passed:

1. Ordinary copyable reply through Safety, Scenario, FIU, Knowledge, Analysis,
   Action and Response.
2. Explicit refusal through boundary route with `stop_contact`.
3. High risk through Safety, safety reference and safety finalization only.
4. Explicit consent saved one memory and a new conversation loaded it as
   historical context without promoting it into current FIU.
5. The same relationship fact without consent wrote zero records.
6. Store failure preserved the answer and emitted a failed memory receipt.
7. Person B's run did not receive Person A's memory.
8. `run()` and `stream()` produced equivalent final structured results.

The standalone run demo printed one saved record followed by one cross-run
historical recall. The streaming demo printed event types, product statuses,
`memory_status=saved`, `completed=completed` and
`single_persistent_write=true`, without private content or API transport.

## GOLDEN REGRESSION / LIVE MODEL VALIDATION

- Static Golden annotation validation: **81 cases PASS**.
- Deterministic Knowledge routing: **81 cases PASS**.
- Phase 3C semantic subset: **24-case Mock replay gate PASS**.
- Phase 3E analysis replay: **30 cases PASS**.
- Phase 3F action/response replay: **38 cases PASS**.
- Phase 3G actual-memory replay: **14 cases PASS**.

**LIVE MODEL END-TO-END QUALITY: NOT VERIFIED.** Mock and deterministic tests
prove graph wiring, contracts, persistence and event behavior, not live-model
semantic accuracy on unseen cases.

## TESTS / VALIDATION

`10 passed` focused runtime-stream tests, `8 passed` Phase 3 full E2E tests,
`11 passed` memory runtime tests, `5 passed` real PostgreSQL memory tests, and
`236 passed` full backend tests. Prior contract, semantic, knowledge, analysis,
action/response, LLM and backend integration gates passed. The isolated
Alembic `upgrade head → downgrade base → upgrade head → alembic check` cycle
passed with all nine tables. Frozen upstream validation, repository secret
boundary, Ruff check/format, `git diff --check` and `.\make.cmd verify` passed
under the Phase 3 marker.

## ARCHITECTURE DECISIONS / FILES CHANGED

The main new components are `app/agent/events.py`, `AgentRuntime.stream()` and
`agent_stream_demo.py`; the undo closure extends the memory service/stores,
contracts, graph intent and Alembic schema. New focused streaming and eight
case E2E tests join the phase-aware verifier. Documentation changes cover the
full graph, memory undo, runtime events and the Phase 4 boundary. [ADR
0016](adr/0016-memory-undo.md) and [ADR 0017](adr/0017-runtime-streaming.md)
record the durable decisions.

## KNOWN ISSUES / DEFERRED

The current Chinese memory-intent parser and provenance checks are narrow;
live semantic quality is unverified. The runtime emits progress and a complete
validated answer, not token deltas. Undo covers new-record insertions only;
there is no general update mutation or public operation-ID workflow. An
unkeyed undo is not an idempotent network retry when older operations remain.
Phase 4 must supply authenticated service composition, REST/WebSocket/SSE,
conversation and AgentRun persistence, API idempotency and disconnect policy.
RAG, embeddings, chat import and React Native remain deferred.

## PHASE 3 FINAL STATUS / PROJECT PHASE MARKER / NEXT

**Phase 3 Agent Runtime: PASS.** Marker: `completed_phase=3`,
`completed_subphase=3H`. Next explicitly authorized stage is Phase 4 — Agent
Service and API Transport; this acceptance does not start it.
