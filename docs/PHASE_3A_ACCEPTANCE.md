# Phase 3A acceptance — Agent State and Runtime Contracts

Date: 2026-09-27

## PHASE / STATUS

Phase 3A — Agent State and Runtime Contracts: **PASS**. Phase 3 runtime
execution remains pending. This subphase satisfies CODE, TEST, DOC, DEMO and
REGRESSION without implementing behavior.

## AGENT INPUT / AGENT STATE

`AgentInput` requires user ID, conversation ID and a current nonblank message;
history is a separate typed field. Optional relationship ID, locale, timezone,
memory flag and string metadata are explicit. `initial_state` builds 27 typed
fields with defaults. Its FIU lists are independent, and no secret, session,
HTTP object, provider instance or hidden reasoning field is present. Caller
authentication and owner checks remain transport responsibilities.

## STRUCTURED RESULTS / FIU MODEL

Strict Pydantic schemas cover scenario, safety, fact extraction, knowledge
route, analysis, action, memory candidate/intent, completed result and failed
result. Fact, inference and unknown use separate types; placing one type in
another list fails validation. Inference requires an alternative explanation.
`AgentResult` schema version is `1`, and JSON serialization/restoration passes.
It is distinct from internal `AgentState`. Candidate/intent person mismatch is
rejected, and a candidate is never a persistence receipt.

## RUNTIME DEPENDENCIES / NODE READ-WRITE MATRIX

`RuntimeDependencies` injects the existing `LLMProvider` and an optional
`ProfileReader`. Project-owned error codes cover input, dependency, structured
output and runtime failures. `docs/AGENT_RUNTIME.md` records reads and writes
for nine future nodes, including safety before ordinary analysis. There is no
runtime workflow, graph, node implementation or prompt in this phase.

## GOLDEN COMPATIBILITY / SERIALIZATION

All 81 cases construct and JSON-round-trip contract-shaped results. Tests
cover the dataset's scenario, safety, route, FIU, reference alias constraints,
memory decision and candidate expectation. Six minimal pairs have explicit
typed contrast checks. Required and forbidden behavior IDs are validated
against the catalog; actual semantic behavior and write effects are not
evaluated. The dataset and frozen Skill were not modified.

## DATABASE COMPATIBILITY

The four `AgentRunStatus` values equal the PostgreSQL model's status check
constraint. No schema change or new migration was needed. Existing Alembic
upgrade/downgrade/upgrade/check and disposable database tests passed.

## TESTS / VALIDATION

Commands run from the repository root on Windows, using the existing local
PostgreSQL test setup and no real model key or external network:

- `uv --cache-dir .cache/uv --no-managed-python run --locked pytest -q apps/server/tests/test_agent_contracts.py` — **86 passed**.
- `.\make.cmd verify` — **PASS**: 13 repository/contract tests, frozen upstream
  validator, isolated Alembic cycle and check, 32 LLM tests, 7 backend smoke
  tests, 86 Agent contract tests, full backend suite (**144 passed**), Golden
  validator (**81 cases, 19 scenarios, six minimal pairs**), repository secret
  check, Ruff check and Ruff format check.
- `git diff --check` — PASS; newly created Python files also passed Ruff.

One existing Starlette/HTTPX deprecation warning appears in backend tests;
there are no failed tests. No new dependency or lockfile change was made for
Phase 3A.

## DEMO

A direct keyless Python call created `AgentInput`, initialized its 27-field
state, constructed a completed `AgentResult`, serialized it to JSON and
restored it. Output reported `fiu_lists_independent: True`,
`result_roundtrip: True`, and `schema_version: '1'`. This demonstrates the
contract only, not relationship reasoning.

## ARCHITECTURE DECISIONS / FILES CHANGED

ADR 0009 documents the total TypedDict vs public Pydantic result split,
injected dependencies, stable vocabulary and deferred semantic evaluation.
Phase 3A adds `apps/server/app/agent/` and
`apps/server/tests/test_agent_contracts.py`; updates `scripts/verify.py`,
`project-phase.json`, `docs/MASTER_PLAN.md`, `docs/ARCHITECTURE.md`; and adds
`docs/AGENT_RUNTIME.md`, `docs/adr/0009-agent-contract-boundary.md` and this
report. Pre-existing uncommitted Phase 1B–2D work was preserved.

## KNOWN ISSUES / DEFERRED / NEXT

No known Phase 3A contract failure. Semantic behavioral grading, actual
memory writes/deletion receipts, import speaker verification, LangGraph nodes,
knowledge loading, streaming, API transport and mobile remain deferred.
Next authorized stage: Phase 3B — Minimal Standalone LangGraph Runtime.
