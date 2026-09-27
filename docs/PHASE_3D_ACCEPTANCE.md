# Phase 3D acceptance — Knowledge Router and Reference Loading Runtime

Date: 2026-09-27

## PHASE / STATUS

Phase 3D — Knowledge Router and Reference Loading Runtime: **PASS** for the
deterministic routing, trusted loading, offline integration and repository
regression gates. Live-model semantic accuracy was not evaluated.

## PRE-FLIGHT GIT STATUS

The working tree was clean at start. `git log -1 --oneline` showed `20db8c9
feat: complete backend foundation and Phase 3C semantic nodes`; the prior
repository-wide checkpoint was a real commit, not merely staged work. Phase
3D changes were made separately.

## KNOWLEDGE ROUTER

`route_knowledge` uses typed SafetyResult, route, ScenarioResult and narrow
message topic cues. It makes no LLM or retrieval call. High risk always
selects `safety`; boundary selects `consent` unless the breakup/refusal
scenario requires `breakup` as its Golden primary. Ordinary scenarios map to
stable aliases, with explicit invitation/attachment/research refinements.
The runtime produces `KnowledgeRouteResult` with selected aliases, primary,
reason and count limit.

## REFERENCE REGISTRY / REFERENCE LOADER

The registry binds 22 unique aliases from `evals/reference_map.json` to
canonical paths in the frozen source manifest. It records alias, relative
source ID, title, topic/category, source family and SHA-256. Its integrity
check read and verified all 22 actual files. `load_references` separately
resolves aliases, verifies the selected file's current hash and UTF-8 content,
and returns typed `LoadedReference` excerpts in original selection order.

## GRAPH CHANGES / SAFETY ROUTING

Ordinary/boundary: `normalize_input → safety_check → classify_scenario →
extract_fiu → knowledge_router → load_references → minimal_finalize → END`.
High risk: `normalize_input → safety_check → knowledge_router →
load_references → safety_finalize → END`. High risk still bypasses Scenario
and FIU, while loading the safety reference first. Finalizers remain fixed,
minimal and do not generate relationship advice from loaded content.

## CONTEXT BUDGET / PATH SECURITY

Defaults are at most 3 references, 4,000 characters per document and 9,000
characters total. Ordering gives the primary reference first access to
budget. Truncation is explicit; a selected later document with no remaining
budget fails. Registry resolution rejects unknown aliases, traversal,
absolute/noncanonical paths, unregistered files and paths resolving outside
the frozen root. Tests cover missing files, changed hash, decode/read errors,
invalid count/budget and resolved-path escape. The resolved-path test runs on
this host; an additional real symlink attempt is conditional on filesystem
permission. All failures become sanitized `knowledge_failure` results without
local paths or raw exception details.

## GOLDEN ROUTING EVALUATION / RUNTIME INTEGRATION

`scripts/check_knowledge_routing.py`: **81/81 PASS**. It feeds Golden expected
scenario/safety/route values to the deterministic router and checks required
primary, allowed, forbidden, maximum count, real alias existence and safety
ordering. It accepts flexible allowed sets, not an exact selected list.
Mock LLM graph integration tests run the actual router/loader across ordinary,
boundary, safety, personality, conflict, breakup, online and chat-import
paths. This proves routing/graph wiring under semantic fixtures, **not** live
model understanding of those inputs.

## STANDALONE DEMO

`uv --cache-dir .cache/uv --no-managed-python run --locked python
apps/server/agent_demo.py` passed without FastAPI, database, network or API
key. It printed `status=completed`, `scenario=reply`, `route=ordinary` and
`selected_references=[reply]`; it did not print document content.

## TESTS / VALIDATION

- `18 passed` Phase 3D knowledge tests; `86 passed` Agent contract tests;
  `8 passed` runtime tests; `8 passed` semantic tests.
- `178 passed` full backend tests; `32 passed` LLM tests; `7 passed` backend
  integration tests; `13 passed` repository tests.
- `81` Golden static annotations validated. Frozen upstream validator passed;
  registry integrity verified all registered source hashes. Alembic
  upgrade/downgrade/upgrade/check, repository secret boundary, Ruff check and
  format, and `git diff --check` passed.
- `.\make.cmd verify`: **PASS**, including active Phase 0–2 and 3A–3D gates.

## ARCHITECTURE DECISIONS / FILES CHANGED

[ADR 0012](adr/0012-deterministic-knowledge-loading.md) records deterministic
routing, separate selection/I/O nodes, safety priority and bounded frozen
loading. Core changes: `app/agent/knowledge.py`, Agent contracts/state/errors,
`nodes.py`, `runtime.py`, focused tests, `evals/phase3d_routing.py`,
`scripts/check_knowledge_routing.py`, `scripts/verify.py`, standalone demo,
phase marker and architecture/runtime/knowledge docs. No file under
`knowledge/goutoujunshi` was changed; no dependency or lockfile change was
needed.

## KNOWN ISSUES / DEFERRED / NEXT

The one-reference default is intentionally conservative; multi-reference
budget and ordering are tested independently. Character truncation can omit
later sections of a long document and is marked in internal state. Live model
classification and end-to-end advice quality are **NOT RUN**. Relationship
analysis, ActionPlan, memory persistence, RAG, embeddings, WebSocket and
mobile remain deferred. Next authorized phase: **Phase 3E — Relationship
Analysis Runtime**; it was not started here.
