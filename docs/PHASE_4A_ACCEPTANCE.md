# Phase 4A acceptance — Agent Application Service and Persistent Run Orchestration

Date: 2026-09-28

## PHASE / STATUS

**Phase 4A: PASS.** This is an application-service gate, not completion of
Phase 4 transport. `project-phase.json` records the last wholly completed phase
as 3 and the completed subphase as 4A.

## APPLICATION SERVICE / ACTOR BOUNDARY / CONVERSATION OWNERSHIP

`AgentService.execute` is a Python-only boundary. It requires a typed
`AuthenticatedActor`, issued by a trusted verified-identity adapter. The
service checks the actor's owned Conversation and any expected relationship or
person before a write or runtime call. Foreign ownership is denied with zero
messages, zero runs and zero runtime calls. The issuer is a trusted in-process
boundary until Phase 4B supplies an actual authentication adapter.

## MESSAGE PERSISTENCE / AGENTRUN PERSISTENCE / RUN ID CORRELATION

Transaction A commits the current user message and an AgentRun transitioned
from pending to running. The database run ID is injected into `AgentInput` and
is the same ID returned by the runtime. Transaction B atomically stores the
validated final answer as an assistant message and completes the run. The
run has created/start/completion timestamps and a failure code when relevant.
No provider output, prompt, hidden reasoning or full internal result is stored.

## TRANSACTION BOUNDARY / HISTORY BUILDING

The service closes A before awaiting the runtime and opens B afterward.
The integration spy observed zero checked-out service connections when runtime
execution began. Owner-scoped history is limited to the latest 20 prior
user/assistant messages, oldest first; current input is excluded and other
conversations do not enter the runtime request.

## MEMORY INTEGRATION / SUCCESS FLOW / FAILURE FLOWS

The service passes the owner and the Conversation's bound relationship to
Phase 3 memory. Real PostgreSQL memory tests prove object B cannot read object
A's memory, while A can read its own on a later run. A memory-store failure
produces a warning and a completed run with assistant message. Runtime failure
keeps the user message, marks the run failed and writes no assistant message.
Pre-runtime database failure rolls back all writes. If saving a successful
answer fails, B rolls back and a separate transaction marks the run failed;
the caller receives a typed persistence error and recovery status. If that
recovery write also fails, `running_unknown` is reported for later inspection.

## CONCURRENCY / STREAMING SEAM / IDEMPOTENCY SEAM

Tests cover two concurrent conversations for one user and separate users;
each has its own messages, run ID and history. Phase 4C can route runtime
stream events through the same service start/finish policy. Consumer disconnect
after final answer but before memory remains an **OPEN DESIGN QUESTION**.
`operation_key` is a typed, bounded service input reserved for Phase 4D;
deduplication is not yet promised.

## DATABASE / MIGRATION / TESTS / VALIDATION

Alembic revision `20260928_01` only adds three AgentRun lifecycle columns.
`uv ... python scripts/check_db_migrations.py` passed real PostgreSQL
upgrade → downgrade → upgrade → `alembic check`. The standalone
`apps/server/agent_service_demo.py` created a disposable migrated database,
ran MockLLM through AgentService without FastAPI, then reopened a session and
confirmed `completed`, persisted `user`/`assistant` roles and exact answer text.

Focused Phase 4A tests: **12 passed**. The full backend suite: **248 passed**.
The complete `.\make.cmd verify`
regression passed all Phase 0–3 gates, including Phase 3 E2E, runtime streaming,
81 Golden annotations, 81 routing cases, 24 semantic cases, 30 analysis cases,
38 action/response cases, 14 memory cases, PostgreSQL, frozen upstream and
secret checks. The full backend suite, Ruff and formatting also passed.

## ARCHITECTURE DECISIONS / FILES CHANGED

See [Agent Service](AGENT_SERVICE.md) and [ADR 0018](adr/0018-agent-service-orchestration.md).
Changes are limited to `apps/server/app/services/agent_service.py`,
AgentInput/run-ID injection, owner-scoped repository operations, three AgentRun
columns and migration, direct tests/demo, Phase 4A verifier gate, and the
architecture, database, server and phase documentation.

## KNOWN ISSUES / DEFERRED / NEXT

An in-process caller with access to the trusted actor issuer can assert an
identity; Phase 4B must place real credential verification before it. A second
database outage after answer generation can leave a run in `running`, reported
as `running_unknown`; reconciliation belongs to a later reliability phase.
There is no distributed transaction with the LLM or memory store. REST,
authentication transport, network streaming, disconnect policy, persistent
idempotency, Mobile and RAG remain deferred. **Next: Phase 4B only on a new
explicit instruction.**
