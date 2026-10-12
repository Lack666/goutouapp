# Phase 8F — Full Mobile Integration and Phase 8 Final Acceptance

CURRENT CLOSEOUT STATUS (2026-10-12): **PASS**, marker8/8F, Pre/Post-marker
root exits0/0. See the [Closeout Addendum](#closeout-addendum--2026-10-12)
and [complete matrix](PHASE_8F_CLOSEOUT_MATRIX.json). The BLOCKED section below
retains the earlier execution and its failures as historical evidence.

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

## Closeout Addendum — 2026-10-12

This independent addendum retains the original BLOCKED report, old failures and
their exits above. The closeout began from clean HEAD `460564a`, branch
`codex/phase8f-final-acceptance`, with no pre-existing unstaged/staged work.
AGENTS, MASTER_PLAN, ARCHITECTURE, the original report/procedure/handoff and
native helper were inspected before work. Scope is8F closeout only; Phase9
has not started. The frozen Skill, Agent graph/behavior, public APIs, dependencies,
lockfiles, production auth and server confirmation contracts are unchanged.

NATIVE ACCEPTANCE: **PASS**,16 complete independent scenes, each exit0.
The full [closeout matrix](PHASE_8F_CLOSEOUT_MATRIX.json) gives each test ID,
preconditions, immutable complete steps, expected/actual UI and database results,
PASS/FAIL status, complete log/report/steps/exit artifacts and SHA-256 values.
Artifacts are committed under `docs/evidence/phase8f-closeout/`; Git attributes
preserve their original bytes and hashes across checkout platforms.

`closeout-final1` remains a failed suite, exit1: its cancel/resource/Undo smoke
failures are preserved. `closeout-final2` also remains a failed suite, exit1;
its complete successful scenes are individually identified. `closeout-final3`
reruns the entire Preserve Consent and REST replay scenes. All reruns start from
fresh App/fixture/credentials, never a failed tail. Matrix passes combine complete
independent test cases, not partial attempts or a claimed uninterrupted native
six-surface E2E. The retained Web final journey supplies that separate Web gate.

### Environment and direct SSE evidence

Existing Pixel_10, `emulator-5554`, Android17/API37, Expo Go57.0.9 and real
PostgreSQL16 were used. All Metro/API traffic remained loopback-only; native
fixture8024 was separate from Web Memory fixture8022. Device8092/8093 reversed
to the IPv4 relay on8093→IPv6 Metro on8092; device8022 reversed to host8024. No AVD
wipe, APK install, account/key weakening, broad Downloads cleanup or real chat.
The historical8D file hash mismatch continues to prevent deletion.

The Android development-only observer records actual `expo/fetch` Reader calls,
validated parser events and React-committed UI transitions. No JWT, Run ID value,
message/Memory body, prompt or provider key is exported by the observer. The
Run ID is retained only internally for a boolean consistency check. Release,
iOS and Web observers are disabled. Arrays are bounded to64 events/transitions.
The native helper reads accessibility metadata directly; it does not derive
client events from server logs or use the failed CDP Runtime.evaluate approach.

`8F-SSE-NORMAL`: actual POST/Bearer/JSON passed real signed-owner transport;
started/status/final/completed were accepted in order, consistentRun=true.
Rendered progress first appears at132ms, before final_response at49817ms;
an explicit visible-viewport assertion observes composing while the final-response
barrier is held. Chinese/Emoji reply and completed UI are observed after release.
Final Reader counts: reads=8, cancels=1,
releases=1; parsed events=10.
These are independent counts, with no read/event one-to-one assumption and no
fabricated token deltas. SQL confirms one completed Run, two messages, Memory0.

`8F-SSE-FAILED`, `8F-SSE-DISCONNECT`, `8F-SSE-CANCEL` and
`8F-SSE-BACK-LOGOUT` pass real native failure/EOF/Stop/Android Back/Logout.
Failed UI follows failed events; unexpected EOF and cancellation show Unknown,
with Reader cleanup. Cancel snapshots remain identical after delayed work.
Back/Logout cancel old work and B sees cleared state. Server disconnect retains
its existing failed-run policy; a retry of that original key confirms the known
failed result before a separate explicit new attempt. Failed is not mislabeled
Completed or assumed recoverably completed from user-message persistence.

### Resources, replay and scope isolation

`8F-RESOURCE-CREATE` performs all three creates from Android UI, then owned
Get/detail, navigation reload, Refresh and Get again. SQL and signed native
wire requests establish exactly one Person, Relationship and Conversation,
correct Person/Relationship binding and stable IDs. Host witness GETs only
read IDs; no host POST is counted as native resource creation.

`8F-REST-REPLAY` drops the real response after AgentService/SQL commit.
Android shows Unknown and retries its immutable original operation key.
The same Run ID, user/assistant Message IDs and provider-call list survive.
Actual UI has one user and one assistant bubble. Before/after SQL snapshots
establish identical Run/key/message IDs; the native retry uses the original
pending operation. Those ID labels were above the captured bubble viewport,
so the UI snapshot is evidence of bubble counts, not a separate ID-label capture.
Consent is granted natively; this message has no explicit save intent, so the
Memory candidate stage is correctly skipped, Memory0 stays0, and replay adds
none of the six provider calls or Memory side effects. An added assertion of
seven calls failed because consent alone does not imply a save request; that
failed complete attempt is retained. Eligible positive Memory writes retain their backend
idempotency regression; actual native Memory deletion replay is tested below.

`8F-OWNER-ISOLATION`: independent signed A/B; A creates a native resource,
views Agent Chat, paged RelationshipMessage, Memory and protected confirmation.
Logout explicitly removes A's credential/scope/cursor/challenge; B reads empty
owned resources/Memory and denied foreign Chat/History. A's real held GET is
released after B login and cannot overwrite B. Real B-owned signed requests
produce404 for A's Person/Relationship/Conversation/Memory/ImportJob. All later
native requests are independently signature-verified as B.

`8F-RELATIONSHIP-ISOLATION`: two distinct owned Person/Relationship/Conversation
sets contain101/3 messages. Actual A History→More→Return→B History→Import→Chat→A
resets cursor, source domain, bindings and selected conversation/person. A's
held history response cannot override B. Missing UUID scope fails closed for
History/Import; no older owned relationship is silently substituted.

### Memory safety and import/history regression

`8F-MEMORY-CHALLENGE`: Prepare cancel, real server challenge expiry and changed
target stale check preserve Memory1/receipts0. No local list substitutes for a
server confirmation or receipt, and no unconfirmed delete is executed.

`8F-MEMORY-REPLAY`: real native Execute commits then its response is lost.
Unknown→original-key replay returns the durable receipt, with Memory1/receipt1,
AgentMessages4 and RelationshipMessages3 unchanged on replay/receipt GET/Refresh.

`8F-MEMORY-RESTART`: response lost after committed deletion, then actual
Force Stop and Restart. SecureStore credentials are revalidated; authoritative
Memory1 is loaded, confirmation is cleared and lost-key limitation is disclosed.
No new deletion or retry key is invented. Manually entering a known receipt ID
performs a read-only inspection; Memory1/receipt1/Agent4/Relationship3 remain.
A durable outbox/automatic crash reconciliation remains a P2 Phase9 limitation.

`8F-MEMORY-SMOKE-PRESERVE` independently executes Inspect/Grant/Pause/Resume/
Revoke/Undo Preview+confirmation+Execute/Delete Prepare+confirmation+Execute/
Receipt/Refresh. Undo removes the latest selected Memory while preserving other
scope records; single deletion and all-delete preserve end Memory0/receipts3,
consent=true/paused=false, Agent6/Relationship3 preserved.
`8F-MEMORY-SMOKE-REVOKE` uses separate B, confirmed all-delete revoke, receipt
inspection and authority Refresh: Memory0/receipt1, consent=false/paused=true,
Agent2/Relationship3 preserved. Neither Unknown result is advertised Completed.

`8F-IMPORT-HISTORY-LIFECYCLE` adds real301-record long-list interactions,
100→200 paging, background/foreground cursor reset to100, Android Back and
Logout→empty history; SQL301/active artifacts0 remain. Host import is explicitly
preparation for this lifecycle test. The earlier real native picker/upload/
binding/Ready/Finalize301 flow and100→200→300→301 traversal are retained as
separate hashed successful evidence, not relabeled as a new native upload.
Relationship-switch cursor reset is additionally covered by the A/B scope case.
No evident blocking interaction was observed; no FPS or TalkBack certification.

`8F-TOKEN-EXPIRY` separately rejects a genuinely expired signed credential and
restores no credential on restart. Every business case gets a fresh CLI JWT
over private pipes and waits for authenticated SecureStore acknowledgement;
token expiry is not mixed into unrelated business acceptance.

### Fixes, full regression and final boundary

No production P0/P1 remains open in the requested A–G closeout.
The missing native proof was closed with fixture-only faults and direct client
observations. The test observer initially grew its rendered JSON text and moved
the Stop control; a fixed-height48 panel retains full metadata in its accessibility
label. A CI Metro restart/clear was required to load that fix. Resource scrolling
automation now uses actual device height and both directions. Undo smoke adds
explicit control-state acknowledgements; lower Mutation/Receipt titles are
searched toward their actual section before reversing direction. The second
Undo smoke failure showed the valid server target but did not reach that title,
so it remained FAIL and the whole scene was rerun. A failed expectation of zero persisted
user messages was corrected to the existing failed-run contract; unexpected EOF
is conservatively Unknown, not presumed Completed. The original failed attempts
and complete independent corrected executions remain separate.

Automated baseline tests are retained: backend556→558 (+2 fixture fault/privacy
tests), Mobile351→355 (+4 observer regressions), repository38→47 (+9 evidence
gate cases); Golden83 unchanged. Demo Web22, Connected Resource3/Agent3/Import4/
Memory5, final Web1, OpenAPI36, generated-client drift/strict checks, Expo Doctor
21/21, migrations, frozen/offline install, knowledge manifest and lint/format
all pass in the full root regression. One existing premature-Phase8 unit test
now explicitly supplies the Phase7D subphase so it keeps that rejection boundary
after real8F completion; its assertion was retained.

PRE-MARKER: `.\make.cmd verify`, marker7/8E, independent exit **0**.
Full log: `docs/evidence/phase8f-closeout/phase8f-closeout-pre-marker-r4.log`.
Log SHA-256: `2c2eba0db33f93b9c6c88bd1392e64b0434220250d145cbc42beed05e4b4356b`.
Exit artifact: `docs/evidence/phase8f-closeout/phase8f-closeout-pre-marker-r4.exit`.
The first closeout root attempt exited1 because the default Playwright Chromium
was absent; missing System32/taskkill also stalled owned Web Metro cleanup.
Only that verified Web child was stopped. Reruns use installed Chrome through
the existing PLAYWRIGHT_CHROME_PATH and include System32 in PATH; no browser
test was deleted, skipped or weakened. The second complete root exited0; the
final pre-marker run repeats all gates after the evidence-step guard and native
viewport-search fixes.

Post-marker execution and final marker/cleanup are recorded immediately below
after their actual results. The original status at the top remains historical.
Production auth, backup/scheduler, durable offline outbox, release APK/EAS,
real LLM quality, imported-chat analysis, FIU/Profile and optional RAG remain
unimplemented in the [Phase9 handoff](PHASE_9_SECURITY_RELIABILITY_HANDOFF.md).
No Phase9 implementation or new Agent business logic was introduced.


### Post-marker result, cleanup and final acceptance

POST-MARKER: `.\make.cmd verify`, actual marker8/8F, independent exit **0**.
Full log: `docs/evidence/phase8f-closeout/phase8f-closeout-post-marker.log`.
SHA-256: `d0491064f86b54cb3d26491e1737a275f8098ba9acb0a266ae37ada55de2a078`.
Independent exit: `docs/evidence/phase8f-closeout/phase8f-closeout-post-marker.exit`.
The log expressly prints Completed phase8/subphase8F and all active Phase0..8
PASS, Phase9 PENDING/NOT STARTED. Backend558, Mobile355, repository47, Golden83,
Web22/3/3/4/5/1, OpenAPI36 and Doctor21/21 passed again. No skipped or removed
baseline gate is counted as success. Native log bytes include original console
whitespace and CRLF; narrowly scoped Git attributes preserve it without editing
the hashed evidence. Source/test whitespace checks remain enabled.

CLEANUP: `docs/evidence/phase8f-closeout/phase8f-closeout-cleanup.json` records identity-verified shutdown of
this task's Metro8092 and IPv4 relay8093, removal of its exact device8022/8092/
8093 reverse mappings and no remaining native fixture8024 listener. All
independent fixture exits also include their disposable database cleanup.
The existing AVD, shared PostgreSQL and all Downloads files were preserved;
the old8D hash-mismatched file was not deleted.

FINAL COMMIT/WORKTREE: branch `codex/phase8f-final-acceptance`; initial parent
`460564a`. This closeout commit contains code, complete matrix, original failed
and successful native evidence, pre/post root logs, final markers and report.
The exact final commit SHA and clean status are captured after commit in
`.cache/phase8f-closeout-final-git.json` and returned in the completion message;
that avoids embedding a self-referential Git commit hash inside its own tree.

FINAL GATES: CODE/TEST/DOC/DEMO/REGRESSION **PASS**. Native A–G and requested
P0/P1 are closed; the sixteen scenes each pass as complete independent runs.
PROJECT MARKER: `completed_phase=8`, `completed_subphase=8F`.
PHASE8 FINAL: **PASS**. PHASE9: **PENDING / NOT STARTED**.
Production limitations remain in the handoff; they are not delivered features.
Stop after this8F closeout. No Phase8G or Phase9 work was begun.
