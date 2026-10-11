# Phase 8F — Full Mobile Integration and Phase 8 Final Acceptance

PHASE: Phase 8F only, 2026-10-11. No Phase 9 implementation.

STATUS: **BLOCKED**. Engineering gates and native observations below do not
establish the entire requested Android acceptance matrix. Marker remains 7/8E;
Phase 8 remains IN PROGRESS. Missing native evidence is an acceptance blocker,
not a P2 production limitation. This report supersedes historical statements
that 8F had not started, without rewriting earlier acceptance evidence.

## Roadmap preflight and Phase 8A–8E audit

Started from clean HEAD `6e3744a`, branch `codex/phase8e-memory-controls`.
Current work branch: `codex/phase8f-final-acceptance`.
Read AGENTS, MASTER_PLAN, ARCHITECTURE, SKILL_CONTRACT, Mobile architecture,
Phase 7 and 8A–8E reports and handoff; reviewed resource/auth/generated client,
Agent/SSE/idempotency, import/history, Memory/deletion/retention contracts.
Existing code, tests and independent log exits were inspected rather than
treating a document PASS as execution evidence.

8E pre-marker `.cache/phase8e-pre-marker-final.exit` and post-marker
`.cache/phase8e-post-marker.exit` both contain 0. SHA-256 of their full logs:
`4001DE69D1126C1B1C092EFE9DDA65FE78C383A81E34B61E448664D1888D6216`
and `C65AC21199B44539E8B087BC346DFD05FC60221135CF3A838BCAA7145B6C4021`.
Both digests were checked against the local full logs.
8D's late audit addendum remains in Git history; earlier failed/aborted attempts
have not been replaced with a success claim.

Phase 8's original target remains generated contracts plus mobile API and
typed stream consumption. No production login, RAG, imported-chat analysis,
public FIU/Profile API, infrastructure expansion or new Agent reasoning.

## Implementation and automated evidence

- `test:final`: five cross-controller cases sharing one actual Session and
  Transport: A/B invalidation, Demo mutation boundary, late previous-owner
  response, lost Memory mutation key after reconstruction, background
  invalidation followed by authoritative foreground reads. This is unit
  evidence; it does not prove Android process death or SecureStore behavior.
- `smoke:final`: actual Expo Web/FastAPI/signed CLI JWT/PostgreSQL/MockLLM
  six-surface journey. Creates Person/Relationship/Conversation in the UI;
  POST SSE and same-key REST replay preserve run/message IDs and provider calls;
  imports 301 equal-timestamp, repeated-body occurrences; reads
  100→200→300→301 via server cursors and refreshes to 100; keeps Agent and
  Relationship histories separate; confirmed Memory deletion preserves both;
  logout and B session clear A's state and reject foreign resources.
- Focused Web `.cache/phase8f-focused-web-final.log`, independent
  `.cache/phase8f-focused-web-final.exit`: 1 test PASS, exit 0. Earlier failing
  Web attempt navigated with a full document reload and lost the deliberately
  volatile Web credential; corrected the test to use application navigation.
- Full Mobile count is 351 (346 retained + 5); repository count is 38
  (36 retained + 2 Doctor fallback cases); backend baseline is 556, Golden 83.
  Final root-run evidence is recorded below. No tests or Golden expectations
  were removed to obtain these counts.
- Doctor's official-schema network fallback now checks actual network cause,
  excludes TLS/abort/unknown errors, credentials/private headers and custom
  transports. All five network regression scenarios passed. It never skips
  Doctor, supplies an offline schema or changes application networking.
- Native helper uses private pipes, short-lived CLI credentials and disposable
  synthetic databases. It verifies exact file identity before overwrite/delete
  and excludes password nodes from UI metadata. UI actions alone are not
  authoritative success; database receipts and scope evidence must agree.

## Android evidence

ANDROID ENVIRONMENT: Windows; Pixel_10 AVD, Android 17/API 37, Expo Go 57.0.9.
Original emulator-5554 was offline. Reconnected without success, then cold
booted the existing AVD without wiping data, using software GPU and port 5560.
`emulator-5560` boot completed and accepted real App actions. Metro/backend
remain loopback-only; explicit ADB reverse and local IPv4→IPv6 relay used.
LAN Metro launch was rejected by automatic approval review; local alternative
worked. See [native procedure](PHASE_8_FINAL_ANDROID_DEMO.md).

ANDROID RESOURCE TEST: actual owned resource reads and selection observed.
Resources used in this session's native flows were prepared through host REST;
native resource creation/update is not established by that preparation.

ANDROID AUTH / SECURESTORE: real hidden-input signed development JWT validated;
natural short-token expiration cleared the scope and showed the expiry message.
Native lifecycle sequence exited 0: waited for authenticated storage
acknowledgement, force-stopped Expo Go, reopened the same manifest and observed
revalidated Connected session; background/foreground retained it. After logout
and another force-stop/restart, no credential was restored. Renewed CLI B
credential connected explicitly. This proves these native storage boundaries,
not production identity or the entire six-domain A/B matrix.

ANDROID AGENT REST: host REST used for eligible deterministic Memory setup.
Native REST same-key retry was interrupted by credential expiry; NOT PASS.

ANDROID POST SSE: PARTIAL. Native Chat sent a synthetic keyboard message, rendered the
Chinese server reply and terminal state. Server evidence: completed run
`b94f55b1-7d75-4ea7-981c-42ec3424a7f6`, operation key
`54884b27-37fc-4b9c-bafa-bec7837337f4`, one run/two messages/no Memory.
Current native reader chunk count and typed-event sequence were not captured:
the debugger exposed Runtime.enable but rejected Runtime.evaluate. Historical
8C streaming evidence and current Web streaming do not establish this missing
current-run probe. Mid-stream failure/pending/failure mapping NOT RUN natively.
Post-restart probe recheck also returned Runtime.evaluate error -32601,
independent exit 1: `.cache/phase8f-native-probe-recheck.log`/`.exit`.

ANDROID MEMORY CONTROLS: grant, resume, pause, revoke and re-grant were executed
on Android. Eligible Memory was prepared with real host Agent REST/MockLLM,
explicitly separate from native mutation. Android read/inspect evidence exists;
Lifecycle report additionally corroborates SQL states: enabled/unpaused,
enabled/paused, revoked/paused; the saved Memory remained present through revoke.

ANDROID GUARDED UNDO: actual native latest-target confirmation and receipt
removed one Memory while preserving two Agent messages.

ANDROID CONFIRMED DELETE: actual native Prepare→explicit confirmation→Execute
for one Memory, structured Person, and all with preserve-consent choice.
Receipt counts progressed 1→2→3→4, Memory returned to 0, Agent messages
2→4→6→8 were preserved. After a fifth host-prepared Memory, replay of the
original all-delete key left Memory=1, receipts=4, Agent messages=10.
The next scripted selection was unavailable; full sequence exit 1. Do not
count its unexecuted revoke-consent/all-delete or B-session tail as PASS.
Evidence: `.cache/phase8f-native-memory.log` and sanitized JSON report.
Separate lifecycle sequence exited 0 and completed explicit revoke-consent
all-delete: Memory=0, receipt=1, Agent messages=2 retained, consent=false,
paused=true. That later success does not change the earlier failed log.

ANDROID IMPORT: PASS for the executed synthetic flow. Actual picker cancellation
and selection, URI binary Multipart, explicit self/person and real Relationship
bindings, Ready and Finalize. Native attempt 3 exited 0; server job
`cdb496e0-847c-4bdf-ab45-e82499264cb1`, imported/revision 5;
301 RelationshipMessages, zero Agent messages/Memory, zero active artifacts.
Exact current device fixture hash was verified before cleanup.

ANDROID HISTORY PAGINATION: PASS for the executed native traversal. Final
pagination sequence exited 0 and brought each authoritative header into view:
100→200→300→301, Refresh→100, then independent AI Conversation→0.
Evidence `.cache/phase8f-native-pagination.log`, `.json`, `.exit`; actual
relationship `58410be8-4b58-4d60-a75a-7f1ed50b0d61`. Dataset contains
301 equal-timestamp repeated-body occurrences; actual native counts preserve
them rather than collapsing text. Current exact test file safely removed and
session logged out. Earlier offscreen snapshots are retained as incomplete
evidence; Web's four-page PASS is separate. Relationship switch and lifecycle
while paging remain untested natively.

ANDROID LIFECYCLE / FAILURE RECOVERY: Back, actual token expiry, authenticated
force-stop/restore, logout/cleared-storage restart and background/foreground
observed. Pending destructive operation kill/restart, unknown result and controlled
network/database outage matrix NOT RUN on Android. Conservative controller
unit tests are separate evidence. Unknown outcome must not be retried with a
fresh key or advertised as success.

## Cross-module audit and limits

FOCUSED GATE COVERAGE: final journey covers six surfaces, resource→Chat,
run-ID continuity/same-key replay, ImportJob→history, multi-page/domain isolation,
consent/pause/resume, confirmed all-delete, receipt/history preservation and
owner switch. Existing `agentChat`/SSE suites retain failure/terminal/timeout/
response-loss cases; `connectedImport` retains revision conflicts, expiry and
unknown upload/finalize; `connectedMemory` retains exact-target Undo, all deletion
scopes, stale/expired challenges and original-key receipt replay; session suites
retain expiry/renewal/old-response isolation. Five new shared-controller tests
cover mode/background/reconstruction boundaries. These all run in the root gate.
Native URI upload, native SSE, native Memory and lifecycle/failure matrix require
the separate Android evidence above. No logging success is inferred from a
mocked response. Missing current native matrix items remain blockers.

EXPO WEB FINAL E2E: PASS, 1 real full journey in the final root run; previous
Connected resources/Agent/Import/Memory 3/3/4/5 all PASS.

MOBILE TESTS: PASS, 351/351 full Mobile; dedicated final focused 5/5.
BACKEND TESTS: PASS, 556/556 full backend plus all preceding demos/gates.

DEMO REGRESSION: PASS, all 22 retained Demo Web cases; no Demo-to-Connected fallback
after failure, no local preview upload or real Demo deletion. Final root results
below govern the actual current run.

OWNER / RELATIONSHIP ISOLATION: final real Web A→B and backend ownership tests
plus new shared-controller invalidation tests. Native full A/B journey and
relationship-switch/cursor/confirmation matrix remain incomplete.

OPERATION KEY / IDEMPOTENCY: Web SSE→REST replay and native Memory same-key
replay have actual evidence. Existing Agent/Memory regression tests preserve
immutable pending payload/key and exact receipt targets. Durable crash recovery
is not present; a lost key cannot authorize a recreated old operation.

PRIVACY: all data synthetic; no model key, real chat or token in committed
fixtures. JWT flows through private pipes and hidden inputs. Trace, video and
screenshots disabled in final Web gate. Runtime/frozen Knowledge untouched;
FEATURE_RAG=false remains complete. No external model calls required.

UI / ACCESSIBILITY / PERFORMANCE: actual soft keyboard, Chinese reply, scroll,
loading and destructive confirmations observed. Basic labels/disabled state
exist and are exercised. TalkBack, theme matrix, long-list lifecycle performance
and FPS measurement NOT RUN. No numerical performance claim.

P0 / P1 FINDINGS / RESOLUTION: no newly established unsafe product replay was
found in executed tests. This is not certification that every P0/P1 is closed:
native streaming/lifecycle/fault/owner matrix evidence remains blocking.
The helper's failed scroll lookup was fixed with bidirectional search and
preference for labelled controls so disabled parent buttons are not bypassed
by enabled text descendants. Product confirmations are unchanged.

NONBLOCKING LIMITATIONS / PHASE 9 HANDOFF: see
[seven explicit reliability items](PHASE_9_SECURITY_RELIABILITY_HANDOFF.md).
Production authentication/backup/restore/scheduler, durable offline outbox,
full crash recovery, release APK/EAS, real LLM quality, imported-chat analysis,
public FIU/Profile and optional RAG remain unimplemented, not implicit PASS.

## Root regression and stage decision

PRE-MARKER VERIFY: `.\make.cmd verify`, full log
`.cache/phase8f-final-root.log`, independent `.cache/phase8f-final-root.exit`.
SHA-256 `56D05B4AF5B33F9E6A62AC4E9FD2EC8EEACFAA7173D00F01BD75E5B7760C28FC`.
All active automated gates passed: backend 556; Mobile 351; repository 38;
Golden 83; Demo Web 22; Connected resources 3, Agent 3, Import 4, Memory 5;
new final Web 1 and focused unit 5; OpenAPI 36 operations, generated deterministic
drift checks, Expo Doctor 21/21, migration cycle, frozen install/knowledge,
strict/lint/format/Ruff and secret boundary. Root expressly retains whole8
IN PROGRESS and separates native acceptance. No hidden FAIL in this final log.
Native-helper refinements after the root's Ruff step were separately rechecked
with Ruff check/format and actual Android lifecycle/pagination execution. Earlier
`.cache/phase8f-baseline.log` exited 1 on new file formatting;
`.cache/phase8f-pre-marker.log` exited 1 because a separate native fixture occupied
the Memory Web fixture port 8022. Keep those failures. Retry after stopping the
native fixture; no removal of Memory Web tests.

PRE-MARKER EXIT CODE: **0**, independently read from the exit file.

POST-MARKER VERIFY: NOT RUN; marker intentionally not advanced.

POST-MARKER EXIT CODE: NOT APPLICABLE; never substitute a previous phase's exit.

OPENAPI / GENERATED CLIENT: no public schema change, 36 operations retained;
deterministic export, drift and strict checks remain enabled in root verification.
GOLDEN / UPSTREAM: 83 cases and frozen snapshot unmodified; root checks retained.

FILES CHANGED: Mobile final test/config/scripts, fixture test protocol, native
acceptance helper, root verification registration, Doctor boundary and tests,
README/architecture/master-plan/handoff documentation. No production Agent or
frozen Skill changes, public DTO additions or new dependency/lockfile changes.

KNOWN ISSUES: incomplete native final matrix; failed attempts retained above.
Historical 8D device fixture remains: its hash differs from the retained original
local fixture, so identity-verified cleanup refused deletion. Evidence:
`.cache/phase8f-old-fixture-cleanup.json`. Current 8F file was safely removed by
the successful final pagination sequence. Reproducible successful native command
sequences are committed under `scripts/native` without credentials.
All disposable native fixtures stopped; owned Metro/relay processes and the
three test reverse mappings were removed after identity verification. Existing
emulator-5560 and shared PostgreSQL were left running; no AVD data wipe.
DEFERRED: production/reliability/analysis/release features listed in the handoff.
PROJECT PHASE MARKER: `completed_phase=7`, `completed_subphase=8E` unchanged.
PHASE 8 FINAL STATUS: **IN PROGRESS / BLOCKED acceptance**, not PASS.
GATES: CODE integration/gate implementation PASS; automated TEST and REGRESSION
PASS; DOC PASS; required native TEST/DEMO matrix PARTIAL. Root exit 0 alone cannot
authorize advancing the marker.
NEXT: finish missing Phase 8F native acceptance; only after explicit later
instruction and phase closure, Phase 9 — Security, Privacy, Reliability and
Deletion. Do not start Phase 9 in this work.
