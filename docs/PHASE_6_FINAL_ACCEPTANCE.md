# Phase 6 final acceptance

Date: 2026-10-08 (Asia/Shanghai).

PHASE: Phase 6D — Memory Controls End-to-End and Phase 6 Final Acceptance

STATUS: PASS

ROADMAP PREFLIGHT: Started at `completed_phase=5`, `completed_subphase=6C`,
clean worktree, HEAD `1a5c8ef`. Read AGENTS, MASTER_PLAN, ARCHITECTURE,
SKILL_CONTRACT memory/safety boundaries, MEMORY/API/DELETION/RETENTION and
BACKUP_DELETION_POLICY, ADR 0015/0016/0026/0027/0028 and prior Phase
3G/3H/4D/5D/6A/6B/6C acceptance. Code/DB/test/demo evidence matched 6A–6C.
Only Phase 6D is in scope. Phase 7 stays pending.

PHASE 6A INTEGRATION: Same durable consent/control store is used by signed
HTTP inspection and actual AgentService REST/SSE. No identity dependency is
overridden; only the provider factory returns a synthetic schema-driven Mock LLM.
Inspection is bounded and owner/person/relationship scoped. Control APIs never
invoke the LLM. Consent starts disabled; unauthorized writes are zero.

PHASE 6B INTEGRATION: Preview/expected-operation undo, server-bound confirmation
snapshots, owner serialization and durable owner/key receipts remain the public
mutation boundary. Conversation undo stays pending, with no unguarded mutation.
All one/person/all deletes retain their explicit scopes and revoke flag semantics.

PHASE 6C INTEGRATION: Finite creation-based 180-day default, UTC query-time
expiry, owned expired detail, bounded deterministic maintenance, FK undo cascade,
challenge expiry+grace and owner-lifetime receipts remain intact. Legacy migration
and policy settings are unchanged. No background infrastructure is introduced.

EXPIRED DUPLICATE RE-SAVE: The existing unique key included expired rows, so
an otherwise valid new same-content save returned duplicate. The SQL adapter now
locks the owner, rechecks durable consent/pause/scope, checks the collided expiry,
removes only that expired row and its undo target, and inserts a new UUID,
creation/expiry and undo operation in one transaction. Failure restores the old
record and operation. Active duplicate dates do not renew. Concurrent resaves
produce one saved and one duplicate, with one new record/operation. Unauthorized
or paused attempts leave the expired row untouched. The standalone fake matches
the new save semantics. The existing expired Golden fixture now includes this
resave expectation; total Golden count stays 83.

CONSENT / PAUSE / REVOKE: HTTP grant enables actual Agent save/recall. Pause
blocks both but permits inspection. Revoke keeps primary memory for inspection,
sets disabled/paused and blocks new read/write; the retention clock continues.
Regrant preserves pause, explicit resume restores consented read/write, and resume
while revoked does not grant. A controlled barrier during candidate extraction
lets HTTP pause/revoke commit first; both REST/SSE then decline persistence.
Context already loaded into an in-flight run cannot be remotely retracted.

GUARDED UNDO: A then B are saved through the real Agent endpoint. Preview B,
undo B and receipt replay from a new HTTP session leave A. Two concurrent keys
against B produce one success and one 409, never consecutive deletion of A.
Expired B is unavailable; cleaned B makes the old expected operation stale.
Neither path falls back to A or creates a success receipt.

DELETE CONFIRMATION: Prepare does not remove memory. One-delete requires the
exact inspected person/relationship scope; person-delete keeps other person
memory and entities; all-delete clears primary memory and undo only. Missing,
foreign, expired, consumed and widened-snapshot challenges are rejected. Clients
cannot replace stored action/target via execute extra fields. Both explicit
delete-all consent flag modes are exercised.

RECEIPT IDEMPOTENCY: Matching undo/delete keys replay the original durable
receipt. Changed expected-operation/challenge payloads conflict. Delete replay
still works after maintenance physically removes its challenge. Maintenance
removes zero receipts; receipts contain safe mutation metadata, not copied content.

RETENTION / CLEANUP: Real Agent recall contains active A and excludes expired
B before cleanup. A clock-controlled Agent run tests one microsecond before and
exactly at expiry. Dry-run leaves rows untouched; bounded execute removes expired
rows and associated undo, leaves controls/receipts untouched, and repeats safely.
Existing 6C suites cover rollback, partial progress, restart and cleanup/control/
undo concurrency; the new replacement rollback test covers a failure after old
deletion and new insert while flushing the new operation.

OWNER / PERSON / RELATIONSHIP ISOLATION: Real JWTs for two users each have
their own memory, relationships, controls, receipts and challenges. Foreign detail,
scopes, receipts, undo and challenge execution fail without exposing owner data.
Extra owner override is rejected. Person A/B actual Agent recall is separate;
delete A leaves B and all Person/Relationship entities. Unknown and foreign
resource errors are identical.

AGENT REST INTEGRATION: Uses the actual signed endpoint, lazy AgentService
composition, LangGraph graph, deterministic Mock LLM, persisted AgentRun and
assistant Message. Memory status matches durable controls and inspected records.
Historical memory is labeled historical and is not current F evidence.

AGENT SSE INTEGRATION: Every received frame is validated against the public
versioned SSE union. In-flight control races, persistence failure, guarded
conversation undo and high-risk requests execute through the real stream route.
Failure to save memory still yields the final answer and completed event.
Existing real socket disconnect tests remain part of full Phase 4 regression:
pre-answer cancellation fails the run; post-answer cancellation keeps the
committed answer and prevents late memory save/re-execution on keyed replay.

PHASE 5 DATA ISOLATION: Upload, bind speakers, bind Relationship, mark ready
and finalize are actual signed HTTP calls against the Phase 5 pipeline. Import
creates no Memory. Imported text is absent from actual Agent recent-message
payloads and analysis. One/person/all memory deletion and retention cleanup
preserve Conversation, Message, RelationshipMessage, ChatImportJob, Person and
Relationship; additional Agent runs add only their expected user/assistant pairs.

MEMORY FAILURE BEHAVIOR: Injected memory-store failure through actual REST/SSE
leaves a completed AgentRun and persisted assistant answer, with failed memory
status and a generic REST warning/SSE status. Raw SQL/token/private exception
text is absent from the public response. No memory is reported saved. Replacement
transaction failure restores its old expired row and operation as well.

PUBLIC API CONTRACT: All 13 existing memory routes remain signed and expose
typed responses in OpenAPI. Missing/invalid credentials are 401. Invalid cursor
or operation key is 400, invalid typed/extra body fields are 422, owner-neutral
missing resources are 404, stale/unavailable/conflicting mutations are 409 and
database failure remains generic 503. Internal hashes, raw evidence, first-run
linkage, confidence/ORM internals and hidden reasoning are excluded from views.
No API retention-maintenance or client owner override is added.

PRIVACY / DELETION SEMANTICS: Challenge and receipt views add an explicit
`deletion_scope_notice`, alongside existing `primary_store_only=true` receipts.
Deletion covers scoped primary Memory and its undo targets only. Necessary
challenge/receipt metadata follows its policy. It does not erase Agent chats,
imports, identities, backups, logs or provider copies. Delete-person does not
search all text mentioning a person. Backup/restore guarantees are not claimed.

PRODUCTION DEPLOYMENT STATUS: Engineering controls, expiry exclusion and
one-shot CLI are implemented/testable. Automatic scheduler, backup encryption,
daily copy/35-day rotation, restore quarantine automation, independent deletion
journal and exact restore replay are **NOT DEPLOYED**. The operational checklist
is in MEMORY_BACKUP_DELETION_POLICY.md. Complete authoritative deletion/key
reconciliation is required before restored Memory serving resumes.

PHASE 6 FULL E2E: The focused suite has independent scenario tests, real
PostgreSQL and real signed JWT verification; authentication is never substituted.
The standalone demo binds a real localhost Uvicorn socket and exercises grant,
REST/SSE save, inspect, pause/no read-write, resume/recall, guarded undo/replay,
save, confirmed deletion/receipt/retry, expire, dry-run/execute/idempotent cleanup,
expired duplicate new-ID save and final delete-all/revoke/inspection. Output is
operation/status/counts/IDs only, without saved content, prompts, chats or JWT.

TESTS: Phase 6D focused suite **32 passed**; full backend **448 passed**.
Phase 6A **7**, 6B **10**, 6C **26** passed. Signed REST/JWT contract/integration
subset **47**, stream/socket/disconnect **16**, Phase 4 idempotency **17**,
import parser/jobs/merge/API **19/6/8/10** passed. Standalone Phase 3 E2E **8**,
memory runtime **11** and SQL memory **5** passed. Golden annotation **83**;
semantic/analysis/action-response/memory Mock replay **24/30/38/14** passed.
Frozen upstream, repository secrets, Alembic cycle/check and Ruff all passed.
No skipped or xfailed backend tests were reported.

VALIDATION COMMANDS AND OUTPUT: Full pre-marker `make verify` exited 0 and
included all prior gates, the 32-test Phase 6D suite and real socket demo.
Log: `.cache/phase6d-verify-pre-marker.log`. The commands are:

```powershell
$env:TEST_DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:15434/goutou_test'
$env:DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:15434/goutou_dev'
$env:PYTHONUTF8='1'
$env:PYTHONUNBUFFERED='1'
$env:PYTEST_ADDOPTS='--basetemp=.cache/phase6d-pytest-verify -o cache_dir=.cache/phase6d-pytest-cache-verify'
uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env pytest -q apps/server/tests/test_phase6_e2e.py
uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env python apps/server/memory_phase6_e2e_demo.py
.\make.cmd verify
git -c safe.directory=F:/狗头军师app化/goutouapp diff --check
```

Final accepted-marker run also exited **0**, with log
`.cache/phase6d-verify-final.log`. Key output:

```text
Completed phase: 6
Completed subphase: 6D
Ran 13 tests ... OK
goutoujunshi validation passed
PASS: isolated Alembic upgrade head / downgrade base / upgrade head / check
32 passed (Phase 6D focused)
448 passed (full backend)
Golden annotation validation passed: {'cases': 83, 'categories': 27, 'scenarios': 19, 'high_risk': 16, 'minimal_pairs': 6}
Repository secret boundary check passed
All checks passed!
157 files already formatted
PASS: Phase 6 Memory Controls and Retention
PRODUCTION SCHEDULER / BACKUP / RESTORE REPLAY: NOT DEPLOYED
PASS: all active Phase 0..6 gates
```

The final socket demo reported `real_socket=true`, `real_signed_jwt=true`,
`real_postgresql=true`, REST/SSE saved count **2**, pause read/write blocking,
undo replay preserving the older record, receipt-backed deletion, expired
exclusion before cleanup, cleanup record/undo counts **1/1**, expired duplicate
new ID, final inspected count **0**, and `status=PASS`. `git diff --check`
exited 0. These summaries omit private content and credentials.

Validation uses the dedicated localhost PostgreSQL 16.15 cluster on port 15434;
each test/demo/migration cycle creates and drops a disposable database. Docker
daemon is unavailable; local PostgreSQL is real, and no Docker success is claimed.
No production database, account, model key or provider network request is needed.

ARCHITECTURE DECISIONS: Reuse owner-row lock and transaction rather than
changing the unique schema or refreshing expired IDs. Keep active duplicate
behavior and new-save provenance. Keep receipts durable and before-challenge
replay. Expose deletion scope as additive typed text. Add a real Phase 6 verifier
branch; later phases still fail if prematurely marked complete. No new dependency,
migration, graph redesign or infrastructure. ADR 0028 receives a clarification.

FILES CHANGED: SQL and in-memory adapters; mutation response contracts; new
Phase 6 mock support, E2E suite and socket demo; expired Golden retention fixture;
phase-aware verifier; root/server READMEs; MASTER_PLAN, ARCHITECTURE, MEMORY,
MEMORY_API, MEMORY_DELETION, MEMORY_RETENTION, MEMORY_BACKUP_DELETION_POLICY;
ADR 0028; this report; project-phase marker after passing all gates. Frozen
knowledge, lockfiles and mobile code stay unchanged.

KNOWN ISSUES: Production readiness gaps listed above. Real-provider semantic
quality is unverified; tests use synthetic Mock LLM. Previously loaded context
cannot be retracted. Receipt storage grows and needs monitoring. Auth provisioning,
production scheduling/backup/restore and Mobile remain outside this phase.
Installed pnpm is 11.7.0 versus project pin 11.25.0; Mobile checks remain correctly
deferred, and version inspection avoids project auto-download. No skipped check
is counted as a pass.

DEFERRED: Expo/React Native, generated mobile client, RAG, OAuth, new reasoning,
distributed queues, production backup infrastructure, complete account/all-history
deletion, independent deletion journal and general recovery engine.

PHASE 6 FINAL STATUS: PASS — CODE, TEST, DOC, DEMO and REGRESSION verified.

PROJECT PHASE MARKER: Updated only after the full pre-marker verification passed:
`completed_phase=6`, `completed_subphase=6D`. Final marker-aware verification
also passed the accepted Phase 6 verifier branch. MASTER_PLAN marks Phase 6 PASS
and Phase 7 PENDING.

NEXT: Phase 7 — Expo React Native MVP. Stop after Phase 6D; no Phase 7 work
has been started.
