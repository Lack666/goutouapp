# Phase 3G acceptance — Memory Candidate and Persistence Runtime

Date: 2026-09-27

## PHASE / STATUS

**Phase 3G — Memory Candidate and Persistence Runtime: PASS.** CODE, TEST,
DOC, DEMO and REGRESSION gates passed. `project-phase.json` remains at
`completed_phase=2`, `completed_subphase=3G`; the overall Phase 3 gate is still
pending its separate final acceptance.

## 3F PRE-FLIGHT

`SKILL_CONTRACT.md` §7.4 requires executable, stoppable advice, while
`ActionPlan.stop_conditions` is structurally optional. Requiring a nonempty
structured field for every simple reply/invitation was over-broad. The
validator now requires it for `observe`, `pause` and `stop_contact`; ordinary
reply/invitation can omit it. A focused test and the **38/38** Phase 3F Mock
replay pass. No ActionPlan redesign was made.

## MEMORY CANDIDATE / CONSENT MODEL / GROUNDING

`memory_candidate_extractor` is a distinct post-response graph node using
`LLMProvider.structured_output(MemoryCandidateBatch)`. Its bounded prompt
receives only current message, current FIU F statements and scope IDs. It can
propose one short `user`, `object` or `relationship` fact and cannot write.
The independent persistence node validates exact message/F substring, F ID,
source class, type, length, prohibited content and subject scope. Model
inferences and unknowns are excluded from factual memory. `memory_enabled`
only turns the feature on; a separate per-user explicit opt-in is required
before writing. Candidate, intent and typed receipt remain distinct.

## MEMORY STORE / DATABASE MODEL / MIGRATION

`MemoryService` uses a project-owned `MemoryStore` protocol, with an in-memory
store for runtime tests and a SQLAlchemy/PostgreSQL adapter with independent
sessions. Alembic revision `20260927_02` adds `memory_controls` and
`memory_records`; owner/person/relationship foreign keys, scope checks and a
unique normalized content hash enforce database boundaries. The isolated
`upgrade head → downgrade base → upgrade head → alembic check` cycle passed.
A new store/session read a record saved by a previous service in the real
PostgreSQL integration test. Transaction rollback was verified on a
cross-owner invalid row.

## MEMORY LOADING / OWNERSHIP / PERSON AND RELATIONSHIP ISOLATION

`load_memory` runs before safety and analysis. It recalls at most eight
consented, unpaused records for the current owner and relationship; no
relationship ID means user-level records only. The analysis prompt keeps
CURRENT USER EVIDENCE, HISTORICAL MEMORY and REFERENCE KNOWLEDGE separate.
Each historical item carries source and creation time, and never becomes a
current F fact. Tests cover another owner, another person, and two
relationships for the same person, including identical content in both.

## PAUSE / RESUME / INSPECT / DELETE ONE / DELETE ALL

Pause blocks recall and writes while inspect remains available. Resume
restores them if consent is still active; revoke-and-keep disables them.
`list_for_user` returns typed records. Delete-one requires owner, record ID
and person scope and returns false on repeat. Confirmed delete-person removes
only that owner's person records. Confirmed delete-all removes the owner's
primary memory rows, optionally revokes consent, and leaves chat messages
untouched. Graph-level destructive intents return `pending_confirmation`;
the programmatic service operations require a separate confirmed call.

## IDEMPOTENCY / FAILURE NON-BLOCKING / PROMPT BOUNDARY

Dedup uses owner, subject, type, relationship scope and normalized content;
retries do not append duplicates. The one-candidate limit avoids partial
batch commits. Store failures after response return a generic `failed`
receipt and warning while preserving `final_answer`; a synthetic secret in
the exception was absent from output. A stored instruction-like string appears
only in the historical JSON data field, never the system message. Loaded
memory is not included in the public Agent result by default.

## GOLDEN MEMORY EVALUATION / STANDALONE TWO-RUN DEMO

`scripts/check_memory_replay.py`: **14/14** selected Phase 1B Golden cases
passed with actual in-memory write counts. Minimal Pair D1 saved one record;
D2 saved zero. The set also covers full-chat refusal, consent, pause/resume,
revoke, delete intents and sensitive content. The keyless standalone demo
reported `first_run_memory_status=saved`, `first_run_saved_count=1`,
`new_conversation=true` and `second_run_historical_memory_loaded=1`. It used
Mock LLM and an in-memory store, with no API, network, key or private dump.

## TESTS / VALIDATION

- `10 passed` focused memory runtime tests; `3 passed` isolated PostgreSQL
  memory integration tests; `215 passed` full backend tests.
- `38/38` Phase 3F action/response replay, `30/30` Phase 3E analysis replay,
  `81/81` Phase 3D routing, and `14/14` Phase 3G memory replay.
- `13 passed` repository tests, `86 passed` contract tests, `32 passed` LLM
  tests and `7 passed` backend integration tests. Static 81-case Golden
  validation, frozen upstream validation, secret boundary and Ruff passed.
- `.\make.cmd verify`: **PASS** after the final implementation and docs.
  `git diff --check`: **PASS** before staging. The standalone two-run demo
  completed successfully.

The earlier standalone focused DB command without `--env-file .env` failed at
fixture setup because `TEST_DATABASE_URL` was absent. The same tests passed
with the repository's documented test environment, and the complete verifier
also passed. No development database was used as a fallback.

## ARCHITECTURE DECISIONS / FILES CHANGED

[ADR 0015](adr/0015-consent-gated-memory.md) records the narrow fact subset,
one-candidate atomicity, consent/pause semantics, scoped recall, confirmed
deletion and nonblocking response behavior. The main changes are in
`apps/server/app/agent/{contracts,memory,memory_nodes,runtime,state}.py`,
`apps/server/app/db/{models/records,repositories/memory}.py`, the new Alembic
revision, `evals/phase3g_memory.py`, `scripts/check_memory_replay.py`,
`scripts/verify.py`, focused tests, the standalone demo and the updated
architecture/database/runtime documentation.

## KNOWN ISSUES / DEFERRED

F-ID and exact-text checks provide structural grounding, not independent
proof that an LLM extracted the right fact. The Chinese intent parser is
narrow; future transport must authenticate the owner and obtain real user
confirmation for destructive service calls. Upstream `event` and `hypothesis`
types, undo history, backup retention/deletion policy, full live-model Golden
evaluation, streaming transport, business endpoints, RAG and mobile remain
deferred. Primary database deletion does not imply immediate removal from
unimplemented backups.

## PHASE 3 COMPLETION READINESS / NEXT

**NOT READY** to mark overall Phase 3 complete: the master plan also names
Agent streaming integration, which this explicitly scoped Phase 3G did not
implement. The 3A–3G runtime gates are ready for a separate Phase 3 final
acceptance task. Do not begin Phase 4 from this report alone.
