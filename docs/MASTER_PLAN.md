# Master plan

Source specification: `knowledge/goutoujunshi`, commit
`6db7354a4002dc7c448a9c87ffdad8132570c9d3`. The snapshot is MIT
licensed and its content hashes are frozen in `knowledge/upstream-manifest.json`.

## Phase gate

A phase passes only with CODE, TEST, DOC, DEMO, and REGRESSION. `make verify`
checks the gates implemented so far and names future gates as deferred. A
phase report records the exact command and output. No future feature is counted
as implemented by a placeholder directory or a golden expectation.

| Phase | Deliverable | Status |
| --- | --- | --- |
| 0 | Repository bootstrap, upstream audit, monorepo, verification | PASS |
| 1 | Skill contract and at least 40 synthetic Golden Cases | PASS |
| 2 | FastAPI, PostgreSQL, Pydantic, SQLAlchemy, Alembic, LLM Provider foundation | PASS |
| 3 | Standalone LangGraph runtime and Agent streaming integration | PASS |
| 4 | Agent Service and API transport over the standalone runtime | PENDING |
| 5 | User-facing memory controls and retention policy integration | PENDING |
| 6 | TXT/Markdown/JSON import and ordinary-code statistics | PENDING |
| 7 | Expo React Native MVP | PENDING |
| 8 | Mobile API integration, generated client and stream consumption | PENDING |
| 9 | Security, privacy, reliability and deletion | PENDING |
| 10 | Optional hybrid RAG with pgvector | PENDING |
| 11 | Agent eval and observability | PENDING |
| 12 | CI/CD, EAS preview, release preparation | PENDING |

## Exit criteria by phase

0. Preserve upstream exactly; inspect skill, README, documentation, references,
   scripts and license; record commit; run upstream validator and repository
   verifier. Demo: verified snapshot and `doctor` output.
1. Record behavioral, safety, evidence, memory, response, and knowledge
   contracts. Validate at least 40 anonymous synthetic cases with scenario,
   safety, references, and assertions. Demo: run the dataset validator. This
   phase tests the **evaluation specification**, not an absent Agent.
2. CRUD storage and migration with ownership checks; API/OpenAPI and database
   integration tests; local Compose demo.
3. Keyless MockLLM and OpenAI-compatible provider behind `chat`, `stream`, and
   `structured_output`; standalone LangGraph `run()` and typed `stream()`,
   consented memory with undo, independent CLI/Python demos, individual node
   tests and full standalone E2E regression.
4. Compose the standalone runtime behind Agent Service and owner-scoped API
   transport; map typed events to a network stream, orchestrate conversation,
   message and AgentRun persistence, and define API idempotency and disconnect
   behavior. No new relationship reasoning or embeddings.
5. Expose confirmed consent, inspect, pause, resume, undo and deletion controls
   through the service boundary, with owner/person isolation and production
   retention-policy decisions. The Phase 3 memory runtime is the baseline.
6. Decoupled parsers, speaker mapping, timestamps, source provenance and
   deterministic metrics with representative fixtures.
7. Six mobile surfaces: home, chat, relationship/profile, import/analysis,
   history, settings. Typecheck and on-device or Expo web demo.
8. OpenAPI-generated TypeScript client and mobile consumption of stable
   transport events with run and idempotency IDs.
9. Upload limits and type checks, traversal prevention, access isolation,
   deletion, log redaction, and high-risk safety priority.
10. Optional metadata, keyword/BM25, vector and rerank retrieval; prove value
    against deterministic baseline. `FEATURE_RAG=false` remains complete.
11. Behavioral eval on the running Agent, observability of nodes, latency,
    provider, tokens, cost and outcome; optional LangSmith failure isolation.
12. Locked dependencies, CI, Docker/Compose, EAS preview and release checklist.

## Implementation log

Phase 2A–2D, Phase 3A–3H and Phase 4A are complete. Phase 3 is accepted as a
transport-independent Agent Runtime. Phase 4A adds the application service;
Phase 4B–4D network transport, authentication, streaming and retry policy remain pending.

### Phase 0

- Copied 63 upstream Skill files, including 20 knowledge and 23 practical
  references, scripts, documentation and MIT license, into an immutable snapshot
  at `knowledge/goutoujunshi`. The source checkout matches the recorded commit.
- Recorded the exact source commit and SHA-256 inventory.
- Created `apps/mobile`, `apps/server`, `knowledge/goutoujunshi`, `docs`,
  `evals` and `scripts`, plus `AGENTS.md`, `.env.example`, `README.md`,
  `Makefile`, `pyproject.toml`, pnpm workspace and phase-aware verification.
- Rechecked this structure against the explicit Phase 0 acceptance list on
  2026-09-26. Simplified `ARCHITECTURE.md` to the confirmed system boundaries;
  moved the snapshot without changing source file contents. See ADR 0004.
- Acceptance: [Phase 0 report](PHASE_0_ACCEPTANCE.md).
- Commit: `eccc633` (`chore: bootstrap standalone runtime monorepo and freeze upstream`).

### Phase 1

- Completed `docs/SKILL_CONTRACT.md` with intake, evidence, scenario route,
  safety, relationship, memory, import and evaluation obligations.
- Added 55 anonymous synthetic Golden Cases across 21 categories, including
  13 high-risk cases, and a 19-reference alias map linked to the frozen source.
- Validated uniqueness, coverage, reference existence, safety precedence,
  explicit memory consent and fact/inference annotation structure.
- Acceptance: [Phase 1 report](PHASE_1_ACCEPTANCE.md).
- On 2026-09-26, completed the narrower Phase 1A behavior-contract audit
  against the frozen upstream. Expanded the contract with 18 source-backed
  scenarios, 9 fact/inference/unknown examples, all 43 reference names,
  response and memory rules, safety priority, 18 anti-patterns and explicit
  source/script ambiguities. Added three document acceptance tests. The
  existing Golden dataset was not changed or re-scored in this subphase;
  a later explicit Phase 1B instruction can rebaseline it against the
  expanded contract. See [Phase 1A report](PHASE_1A_ACCEPTANCE.md).
- On 2026-09-26, completed the requested Phase 1B Golden Dataset audit.
  Preserved all 55 original IDs, added 26 targeted synthetic cases, linked
  every case to contract rules and a behavioral rubric, and covered all 18
  scenarios plus memory. Added six linked minimal pairs, sourced FIU
  expectations, flexible 1–3-reference routing, explicit safety and memory
  decisions, a coverage matrix, and stronger static validation. No Agent or
  model behavior was run. See [Phase 1B report](PHASE_1B_ACCEPTANCE.md).

### Phase 2A

- On 2026-09-26, implemented the FastAPI backend foundation: environment-backed
  settings, `/health`, `/api/v1/status`, versioned routing, safe base error
  responses and logging, and a Uvicorn development launcher. No database or
  model connection is made at startup.
- Added root uv runtime/dev dependencies and `uv.lock`; integrated backend
  pytest and Ruff checks into the Windows `make.cmd verify` path while keeping
  `completed_phase` at 1 and marking only `completed_subphase` as `2A`.
- Ran a real Uvicorn process and requested both endpoints over localhost.
  See [Phase 2A report](PHASE_2A_ACCEPTANCE.md) and
  [ADR 0005](adr/0005-fastapi-foundation.md).

### Phase 2B

- On 2026-09-27, added the PostgreSQL persistence foundation: six UUID-based
  owner-scoped models, a lazy engine and request session dependency, a small
  repository/service layer, Alembic initial migration, database readiness and
  a Compose development service.
- The database gate creates disposable test databases, exercises Alembic CLI
  upgrade/downgrade/upgrade, then runs PostgreSQL integration tests. Agent and
  mobile gates remain deferred. See [database operations](DATABASE.md),
  [ADR 0006](adr/0006-postgresql-foundation.md) and the
  [Phase 2B acceptance report](PHASE_2B_ACCEPTANCE.md).

### Phase 2C

- On 2026-09-27, added a typed `LLMProvider` protocol, keyless queued Mock
  provider, a single OpenAI-compatible Chat Completions provider, strict
  structured-output validation, provider-level SSE streaming, and safe error
  normalization. No real model request or Agent behavior is part of this phase.
- Moved existing HTTPX to runtime dependencies in the single `uv.lock` and
  extended Settings with base URL, model and timeout. The verifier now runs an
  explicit offline LLM unit gate before all backend and PostgreSQL regression
  tests. See [LLM Provider architecture](LLM_PROVIDER.md),
  [ADR 0007](adr/0007-llm-provider-boundary.md) and the
  [Phase 2C acceptance report](PHASE_2C_ACCEPTANCE.md).

### Phase 2D

- On 2026-09-27, verified FastAPI, PostgreSQL and both LLM Provider choices in
  one backend environment. Added offline/dependency-isolated smoke tests,
  FastAPI shutdown disposal of the lazy database pool, and `alembic check` to
  the disposable migration cycle. Re-ran dependency sync, Compose startup,
  development migration, live Uvicorn HTTP checks and all prior gates.
- Completed the Phase 2 verification gate and set `completed_phase` to `2`.
  Agent and Mobile gates remain deferred. See the
  [Phase 2D acceptance report](PHASE_2D_ACCEPTANCE.md) and
  [ADR 0008](adr/0008-backend-composition-lifecycle.md).

### Phase 3A

- On 2026-09-27, defined transport-independent Agent input, total TypedDict
  state, strict structured result/failure schemas, FIU and memory candidate
  separation, status/error vocabulary, and injected runtime dependencies.
- Added an offline compatibility test for all 81 Golden cases and six minimal
  pairs. This proves schema coverage, not Agent behavior or memory writes.
- Added the future node read/write matrix and hidden-reasoning policy in
  [Agent contracts](AGENT_RUNTIME.md), with [ADR 0009](adr/0009-agent-contract-boundary.md).
  Agent execution, knowledge loading, memory persistence and mobile remain
  deferred. See [Phase 3A report](PHASE_3A_ACCEPTANCE.md).

### Phase 3B

- On 2026-09-27, added locked LangGraph 1.2.12 and a reusable standalone
  `StateGraph` with independently testable nodes, a conditional synthetic
  safety branch, scoped state updates and an injected Mock LLM path.
- Runtime results and failures share a run ID; input, provider output and
  unexpected node failures map to safe project-owned errors. A keyless CLI
  demo prints JSON without FastAPI or PostgreSQL.
- A focused offline gate verifies graph structure, both routes, node limits,
  failure paths, run isolation and a Golden pair architecture smoke. The full
  81-case behavior eval remains deferred. See [Phase 3B report](PHASE_3B_ACCEPTANCE.md)
  and [ADR 0010](adr/0010-minimal-langgraph-runtime.md).

### Phase 3C

- On 2026-09-27, replaced synthetic safety routing, the constant scenario and
  minimal analysis with separate provider-backed `SafetyResult`,
  `ScenarioResult` and `FactExtractionResult` nodes. High risk exits before
  ordinary classification; explicit refusal has a distinct boundary route.
- Added short source-backed system prompts, speaker-labeled JSON context,
  structured-output failure handling and a 24-case Golden subset including all
  six minimal pairs. A deterministic evaluator checks structured fields and
  catches promoted inferences; oracle-derived Mock replay is not live accuracy.
- Updated the verifier with focused offline semantic tests. No live semantic
  model validation was run. See [Phase 3C report](PHASE_3C_ACCEPTANCE.md) and
  [ADR 0011](adr/0011-semantic-entry-nodes.md).

### Phase 3D

- On 2026-09-27, added deterministic Knowledge Router and independent Reference
  Loader nodes to ordinary, boundary and high-risk graph paths. The safety
  branch still skips scenario/FIU but now loads its safety reference first.
- An app-owned registry validates `reference_map.json` aliases against the
  frozen manifest and canonical paths. The loader verifies selected file
  hashes, returns typed excerpts under explicit document/total budgets and
  converts failures to a safe Agent error. The public result exposes aliases
  only. No RAG or relationship advice was added.
- The verifier runs all 81 Golden routing constraints with expected semantic
  labels as fixtures, plus runtime integration and loader security tests.
  This is a deterministic router evaluation, not a live model evaluation.
  See [Phase 3D report](PHASE_3D_ACCEPTANCE.md),
  [Knowledge routing](KNOWLEDGE_ROUTING.md) and
  [ADR 0012](adr/0012-deterministic-knowledge-loading.md).

### Phase 3E

- On 2026-09-27, added a provider-backed `relationship_analysis` node after
  knowledge loading on ordinary/boundary paths. High risk still bypasses it.
  The node consumes typed FIU and the actual loaded excerpts, and writes only
  structured `AnalysisResult` with evidence/reference provenance.
- Extended analysis points with observed/tentative/framework/uncertainty roles,
  relevant dimensions and source IDs. The runtime rejects invalid IDs,
  inference-to-fact promotion, missing boundary recognition and obvious action
  or unsupported certainty language. This does not prove semantic entailment.
- Added a 30-case Golden Mock replay and structural evaluator plus direct
  reference-content, truncation, injection and failure tests. Live-model
  relationship analysis was not run. See [Phase 3E report](PHASE_3E_ACCEPTANCE.md),
  [Relationship analysis](RELATIONSHIP_ANALYSIS.md) and
  [ADR 0013](adr/0013-grounded-analysis-contract.md).

### Phase 3F

- On 2026-09-27, replaced the ordinary-path placeholder with independent
  `action_planner` and `response_generator` nodes. Each uses typed
  `LLMProvider.structured_output` and writes only its declared state field;
  high-risk input still bypasses both nodes.
- Extended `ActionPlan` with a contact policy and analysis-point provenance,
  added `ResponseResult`, bounded prompts and project-owned validation for
  refusal, manipulation, unsupported certainty, internal IDs and plan/answer
  consistency. No memory persistence or transport was added.
- Added a 38-case Golden Mock replay, focused mutation tests, a keyless
  standalone demo and an active verifier gate. This validates wiring and
  structural rules, not live-model advice quality. See
  [Phase 3F report](PHASE_3F_ACCEPTANCE.md), [Action and response](ACTION_RESPONSE.md)
  and [ADR 0014](adr/0014-action-response-boundary.md).

### Phase 3G

- On 2026-09-27, added a post-response memory intent, bounded structured
  candidate extraction, fact/source/consent validation and separate persistence
  node. Early memory loading provides historical context to analysis without
  changing current FIU; high-risk runs skip memory writes.
- Added per-user opt-in and pause state, scoped inspect/deletion operations,
  in-memory and SQLAlchemy stores, a two-table Alembic migration, duplicate
  prevention and nonblocking memory failure receipts. A narrow user/object/
  relationship fact subset is persisted; event/hypothesis remain deferred.
- The verifier runs focused memory tests, real PostgreSQL persistence and
  migration checks, a 14-case Golden Mock replay, all prior gates and a
  standalone two-run demo. The Phase 3F stop-condition validator was corrected
  for simple reply/invitation and its 38-case replay rerun. See
  [Phase 3G report](PHASE_3G_ACCEPTANCE.md), [Memory](MEMORY.md) and
  [ADR 0015](adr/0015-consent-gated-memory.md).

### Phase 3H and Phase 3 final acceptance

- On 2026-09-27, closed the Phase 1A memory undo MUST gap with a bounded
  20-operation, owner-scoped undo history for newly saved records. Alembic
  revision `20260927_03` adds `memory_operations`; undo works across sessions,
  while hard deletion clears affected operation history.
- Added transport-independent `AgentRuntime.stream()` over the same compiled
  LangGraph as `run()`. Typed, JSON-restorable events provide stable progress,
  a validated full final answer, memory receipt and terminal result/failure.
  Token-level model generation remains deferred. Cancellation closes the
  underlying graph iterator; high-risk runs never publish ordinary planning
  or composing statuses.
- Eight standalone full-pipeline E2E cases cover ordinary reply, explicit
  refusal, high risk, cross-conversation memory, absent consent, memory failure,
  person isolation and run/stream parity. The verifier also runs focused
  streaming tests and all earlier gates. Phase 3 is complete as an engineering
  runtime gate; live-model end-to-end quality remains unverified. See
  [Phase 3H report](PHASE_3H_ACCEPTANCE.md),
  [Streaming runtime](STREAMING_RUNTIME.md), [ADR 0016](adr/0016-memory-undo.md)
  and [ADR 0017](adr/0017-runtime-streaming.md).

### Phase 4A — Agent application service

- `AgentService.execute` binds a verified actor to an existing owned conversation,
  stores the user message and running run in a short transaction, then calls the
  standalone runtime without a database transaction. A second transaction stores
  the validated answer and completion, or a failure state. Runtime and database
  run IDs are identical. The owner-scoped history contains at most 20 prior
  user/assistant messages.
- A failed runtime preserves user input but writes no assistant answer. If the
  answer commit fails, the service rolls it back and attempts a separate failed
  run update; it reports recovery status either way. Memory failure remains a
  completed response with a warning. See [Agent Service](AGENT_SERVICE.md),
  [ADR 0018](adr/0018-agent-service-orchestration.md) and
  [Phase 4A acceptance](PHASE_4A_ACCEPTANCE.md).

## Dependency policy

Official documentation was checked before selecting the layout: uv's project
and lockfile guidance, FastAPI's request-model tutorial, SQLAlchemy's ORM
documentation, and Expo's SDK compatibility table. Exact application library
versions are chosen at their implementation phase and locked in `uv.lock` or
`pnpm-lock.yaml`; no pre-release versions by default. Phase 2A introduced the
first Python runtime dependencies, selected against official release records
and verified with the lockfile.
