# Phase 9H — Full Data Erasure and Safe AgentRun Recovery

Status: PASS. CODE, TEST, DOC, DEMO and REGRESSION pass. Whole Phase9 engineering
acceptance: PASS. Public Production Readiness: NOT APPROVED. Accepted 2026-10-21.
Phase10–12 remain PENDING and are not started.

## Authoritative evidence and verification

- Clean9G baseline: dcc7085c6061fe43081b2b914507fa8ebd733fcb; original
  baseline-r3 make.cmd verify exited0 at marker8/9G. Backend810, Mobile396,
  repository99, Golden83, OpenAPI40, Expo Doctor21/21 and all earlier Web passed.
- Final source fingerprint: `dc0e1026713e5150f0a6c6eb4b5ae9b442e8264ae61c33ff92af3f02c75da20e`. The service, client,
  tests, verification tools, migrations, generated API and semantic contracts
  are bound by execution-time start/end hashes in the independent captures.
  Only closure status, marker, evidence links and acceptance reports are filled
  after actual root exits; executable code and the covered core contracts stay
  frozen. The fingerprint's exact input list is in phase9h_capture.py.
- Pre-marker: [evidence/phase9h/pre-marker-oct21-r4.log](../docs/evidence/phase9h/pre-marker-oct21-r4.log), original `make.cmd verify`,
  independent actual exit0 under8/9G.
- Post-marker: [evidence/phase9h/post-marker-oct21-r2.log](../docs/evidence/phase9h/post-marker-oct21-r2.log), a separate original
  `make.cmd verify`, independent actual exit0 under9/9H.
- [9H matrix](PHASE_9H_MATRIX.json) binds raw logs, independent exits, source
  records, signed native HTTP/SQL reports and immutable historical matrices.
  [Original exit criteria](PHASE_9_EXIT_CRITERIA_MATRIX.json) retains all nine IDs;
  all PASS, none blocks engineering closure. No production waiver is used.
- Final marker: completed_phase9 / completed_subphase9H. Validator accepts only
  the authorized conditional Phase9 closure backed by the independent roots.

## Implemented behavior and boundaries

Person deletes its exact structured relationships and descendants, including scoped
Memory/Undo and raw artifacts. Relationship deletes its exact descendants and keeps
the Person and other relationships. Shared/unbound Speaker references refuse rather
than broadening scope. Text mentions never cause a cascade. Owner Owned Data also
includes general Conversations, unbound imports, controls and inactive reservations;
only the private signed development/test operator command exposes this operation.
It requires the literal owner UUID and strong phrase. No Owner HTTP endpoint exists.
Local identity tombstones reject old JWTs and recreation of deleted UUIDs. This is
local data clearance, not production identity/account closure.

Prepare binds a five-minute dependency/content fingerprint and counts. Execute
requires explicit confirmation and the original immutable operation key. Changed,
expired and consumed confirmations refuse; same-key replay returns the one receipt.
Owner write barriers serialize every ordinary mutation with erasure. Raw unlink is
monotonic: if SQL commit subsequently fails, no success receipt is returned; SQL
rolls back and exact retry finishes cleanup. SQL cannot restore an already unlinked
file. Minimum UUID/key/hash/count/time tombstones and dedup barriers remain; Message,
RelationshipMessage, Speaker, scoped Memory/Undo and private text bodies are erased.

Private exact-run recovery holds an OS writer fence through receipt commit. The
fence covers Provider, persistence and Memory executor lifetime. A still-running
worker, cancelled coroutine with live executor, legacy/missing/mismatched fence or
bare recovered_at flag is insufficient. Verified stopped runs preserve actually
committed effects, become failed/writer_stopped and never reexecute the Provider.
Recovery requires its exact owner/run/token/scope/time receipt. Original run keys
remain fenced and unknown effects remain explicitly unknown_preserved.

Mobile uses one volatile immutable attempt, explicit execute, receipt GET validation,
same-key retry and owner/selection epochs. It clears resource/chat/import/Memory
caches before execution and verifies authoritative absence/fresh lists afterward.
Cancel never executes. Busy/expiry require fresh prepare. Lost descriptors across
restart are disclosed; no durable outbox is claimed.

Actual pg_dump/pg_restore into a quarantined database reconciles exact deletion,
identity, receipt/key/dedup and committed-effect state against an intact frozen
current primary. Live/unproved writers refuse. Missing current authority after
total primary loss refuses serving; an independent deletion journal is absent.

## Actual tests and demonstrations

- Backend:852 passed, all tests unfiltered;42 new tests cover full erasure22,
  stopped-run recovery8, real archive/restore10 and private owner operator2.
- Mobile:410 passed across28 suites;14 new controller tests. Strict TypeScript,
  ESLint, Prettier and Expo Doctor21/21 pass.
- Repository:121 passed;22 new evidence/marker/native-geometry counterexamples retain every old
  gate and reject incomplete, failed, stale, altered or spliced native evidence.
- Golden83 frozen; OpenAPI43 (old40 plus3 signed lifecycle routes),40 protected
  routes/3 public; generated-client export/codegen/drift pass. Migration upgrade,
  downgrade and schema validation pass against real PostgreSQL.
- Independent suites: admission27, lifecycle44, original erasure39, REST/SSE
  integration7, focused9G49, full new boundaries42, authorization41, upload45.
- Web: Demo22; connected3/3/4/5/1; erasure4 (old2 plus2 lifecycle cases), all pass
  in both complete root invocations.
- Android: all thirteen new complete canonical scenes exit0: resource_create,
  sse_normal, memory_smoke_revoke, session, import_history, dataset, conversation,
  erasure_faults, erasure_restart, person, relationship, lifecycle_faults and
  lifecycle_restart. Exact accepted r18 executions are linked per scene in the
  matrix. Earlier r14/r15/r16 results, including startup and Conversation failures,
  remain immutable and are superseded after the SDK57 patches. Each
  final execution first confirms the app is stopped before fixture
  initialization, then executes the unchanged full scene and unchanged proof check.
  All failed logs, exits and reports stay unchanged. The r16 Conversation receipt
  query reproduced an actual1909px Chat viewport under a fixed composer; using
  full2424px height reversed scroll direction at an inverted clipped control.
  The helper now recognizes the actual scrollable viewport. Three added tests
  reproduce the old failure and retain invalid/disabled refusal and composer
  clicks;24 attempts, canonical commands and service assertions are unchanged.
  All final suites and native scenes were freshly rerun after this tooling fix.
  Historical launcher-startup and native host-crash causes remain unconfirmed.
  These are actual9H executions, not retained9G UI results.
- Native runtime fingerprint:f52bb9cbf18e31a67916bd397f521e896b36ae122b0f2f8f2c4d5fb457f9f403, exact259 current executable
  inputs and canonical command arrays. All thirteen accepted r18 scenes bind the final
  full source at execution start/end. Earlier r7/r9/r10/r11/r12 results remain
  historical or superseded and are never relabeled as final-source executions.
  Independent android-r18-lifecycle-wire executes the entire canonical fault flow
  plus a final evidence snapshot at final full source, start=end. Its own raw
  signed prepare/execute/receipt-GET and SQL proof all pass. No cross-run endpoint
  borrowing or report splicing is accepted. All original reports stay unchanged.
  Each scene additionally checks the actual-device compiled build digest,
  including source, dependencies and Expo/Metro/TypeScript configuration. A
  source-map or disk-only fingerprint cannot substitute for this proof. The
  cached-bundle finding9H-EVIDENCE-01/P1 is closed by cold builds, actual-device
  marker checks, twenty-two tooling tests and all fresh final native executions.
  The supplement's exact raw input is retained as
  evidence/phase9h/lifecycle-wire-steps-final.json; its recorded command uses the
  identical temporary copy under .cache.
- All evidence is synthetic. Read-only privacy screening and repository secret
  boundaries pass; receipts and logs contain finite metadata, no bearer values,
  private full chats, provider secrets or hidden reasoning. Pattern screening is
  not a universal guarantee about arbitrary private prose.
- Ruff, frozen upstream/hash/license, matching dependency locks, complete earlier gates
  and git diff --check pass. Four exact SDK57 compatibility patches and their pnpm lockfile were required:
  expo57.0.30, expo-constants57.0.22, expo-linking57.0.13, expo-router57.0.28.
  The failed pre-marker-oct20-r2 log is retained. SDK57/RN0.86.3, workspace
  supply-chain policy, upstream and Golden stay unchanged. All final evidence
  was freshly executed after these patches; official Expo compatibility and
  frozen lockfile checks pass.

## Findings, production limits and final decision

No open P0/P1 finding remains in the authorized local engineering scope. Fixed and
regression-tested boundaries include live executor cancellation, bare recovery-flag
forgery, shared Speaker scope, Owner unknown raw files/reservations, SQL/raw failure,
receipt-confirmed unknown results, owner/selection stale callbacks, clipped Chat
receipt-query scrolling and native evidence
that lacks its own complete signed endpoint proof. Failed, aborted and superseded
executions remain in the evidence directory; no hidden retry is counted as a pass.

R-06/07/08/09/10 local controls pass with deployment prerequisites retained in
[production risks](PHASE_9H_PRODUCTION_RISKS.json):12 explicit limitations, all still
block public exposure and none is an unimplemented required local engineering item.
Production identity/revocation/account closure, durable outbox, supervised scheduling,
encrypted rotation/key custody, independent total-primary-loss authority, real
provider semantic evaluation, external/export/provider/collector copy lifecycle,
monitoring and public ingress/host topology are absent or undeployed. Legacy writer
proof remains quarantined. Historical Windows native process crashes remain recorded;
two new independent full roots pass without weakening a test or hiding failures.
Public Production Readiness remains NOT APPROVED.

## Phase9H A–Z acceptance ledger

A roadmap/legal marker:PASS; B Person:PASS; C Relationship:PASS; D Owner scope:PASS;
E local versus production identity disclosure:PASS; F exact-run recovery:PASS;
G live-writer refusal:PASS; H guarded confirmation:PASS; I original keys:PASS;
J replay once:PASS; K Run/Job/cursor resurrection fences:PASS; L Owner isolation:PASS;
M scope boundaries:PASS; N Memory/deletion contract:PASS; O actual archive consistency:PASS;
P missing-primary authority refuses:PASS; Q real Android/Web:PASS; R private evidence:PASS;
S old Agent/Import/Memory/Erasure regression:PASS; T no open P0/P1:PASS;
U complete earlier regression:PASS; V CODE/TEST/DOC/DEMO/REGRESSION:PASS;
W actual independent pre-marker exit0:PASS; X authorized9/9H marker:PASS;
Y actual independent post-marker exit0:PASS; Z stop after acceptance:PASS.

[Whole Phase9 final acceptance](PHASE_9_FINAL_ACCEPTANCE.md) records the nine original
criteria. Changed paths are inventoried in [final changed files](evidence/phase9h/changed-files-final.json).
Stop here. Any Phase10/11/12, real Provider, RAG, real-chat or public deployment work
requires a separate explicit instruction.

## Preserved execution history

The following entries describe intermediate and superseded states. The authoritative
final results above and machine-checked matrix supersede their pending statements.


Preflight: AGENTS, MASTER_PLAN, ARCHITECTURE, SKILL_CONTRACT and required 9G/privacy/
deletion/backup/recovery contracts read. Initial tree clean at
dcc7085c6061fe43081b2b914507fa8ebd733fcb, marker8/9G. Branch:
codex/phase9h-erasure-recovery. Pristine original make.cmd verify baseline-r3
exited0: Backend810, Mobile396, repository99, Golden83, OpenAPI40, Doctor21/21,
all prior Web journeys. Earlier environment/migration failures remain preserved.

Implementation: ADR0043, DATA_DELETION_CONTRACT/MATRIX, AGENT_RUN_RECOVERY.
Only9H and conditional original Phase9 final engineering acceptance are authorized.
Phase10–12, real providers, RAG, real chats and public deployment are not started.
Upstream Skill and Golden cases remain unchanged. The failed original pre-marker
oct20-r2 compatibility gate required four exact SDK57 patches: expo57.0.30,
expo-constants57.0.22, expo-linking57.0.13 and expo-router57.0.28, with pnpm lockfile.
SDK57, React Native0.86.3 and workspace supply-chain policy stay unchanged.
October21 official compatibility recheck exited0. Earlier sixteen independent
suites, thirteen native passes and the complete wire supplement are retained as
superseded evidence; final acceptance requires fresh executions after these patches.

October21 backend-final-oct21-r16 exited1 (397 passed/455 setup errors) after
starting before the local PostgreSQL listener was ready. Its complete log and
source record remain immutable. A new full backend invocation requires verified
SELECT1 readiness first; no test is removed or skipped. The official Expo Doctor
independent invocation expo-doctor-oct21-r1 passed all21 checks after the patches.

The October21 r16 native batch passed six full scenes, then Conversation deletion
completed but its formal receipt-query tap failed (exit1). Six remaining scenes
were not started. The complete original failure, SQL/wire snapshot, screenshots,
coordinates and interrupted teardown remain immutable. Diagnostic coordinates
reproduced a tooling defect: the unlabeled Chat FlatList ends at1909px above a
fixed composer, while the helper used the2424px screen to decide scroll direction.
An inverted2278..1909 receipt bound therefore made it scroll away from the button.
Recognizing the actual scrollable viewport fixes direction without changing24
attempts, canonical scene commands or service assertions. Three new tests also
retain invalid/disabled refusal and valid composer clicks. All sixteen final
suites and all thirteen native scenes plus the supplement must run again after
this fix; six r16 passes cannot be relabeled as new-source results. The existing
Pixel_10 emulator predates this task and is preserved; only owned Metro/relay
processes were stopped. No device or database storage was wiped.

Independent synthetic logs, exits, execution-time source fingerprints and native
reports reside in docs/evidence/phase9h. Failed/aborted/superseded runs stay immutable.
Prior9F/9G Android results are historical; changed executables require new actual runs.
Final counts and source binding are pending all final code/document/tooling changes.

Production limitations: identity/account closure, durable outbox, supervised scheduling,
encrypted rotation, independent deletion authority after total primary loss,
external/provider/export/collector copies and public ingress acceptance remain
unimplemented or undeployed. Legacy Runs without reliable writer proof stay quarantined.

## Review findings and corrected boundaries

- A bare recovered_at/failed flag cannot stand in for a stopped-writer recovery
  receipt. Erasure and actual restored serving both require the exact owner/run/
  writer-token/scope/time receipt. Actual negative archive/erasure tests retain this.
- Coroutine cancellation can leave a Memory executor thread alive. OS fences stay
  strongly owned for the process lifetime on every abnormal exit; recovery refuses
  the live cancelled worker, even after lost DB pools and30days elapsed.
- Owner erasure refuses unknown raw files and active upload reservations. Outside/
  unbound Person-speaker references reject rather than broadening a cascade.
- A successful Execute response without a validated receipt GET is still an
  unknown result. Mobile compares JSONB count fields semantically, preserves the
  exact operation descriptor for retry, and prevents stale owner/scope responses.
- Existing authentication and client-inventory tests now retain their original
  operation counts separately and assert all three additional authenticated routes.
  No earlier bearer assertion, test case or native assertion was removed.

Recovery/archive tests use independently migrated disposable PostgreSQL databases:
archives contain all owners, so unrelated unresolved synthetic incidents from other
cases must not masquerade as quiescent authority. The production restore refusal
remains strict. Earlier contaminated-run failures and aborted full runs are preserved.

## Evidence handling and interrupted environment

The Oct14/15 run was interrupted before full closeout. backend-final-r1 and
full-boundaries-final-r1 have partial logs and no successful independent exit;
they are ABORTED, never passing evidence. All failed native r1–r5 attempts remain
unchanged. On Oct20 the original private PostgreSQL15434, Metro8092/relay8093 and
Pixel_10 API37 emulator were restarted. A wrong-port startup was corrected to the
original loopback15434 endpoint; its timeout failure is retained. No development
owner data or emulator storage was wiped. Current independent captures use distinct
*-oct20-* names; source fingerprints distinguish superseded results.

## Engineering and deployment boundaries

Person erases exact structured descendants including scoped Memory/Undo; Relationship
preserves Person and other relationships. Owner Owned Data includes general
Conversations and unbound imports but is available only via the private signed
operator command and owner-specific confirmation. Local User tombstones reject
old credentials and UUID recreation permanently. This is not production account
or external-provider identity closure. Receipt lookup/replay stays private and
scoped; no public Owner erasure/recovery endpoint exists.

Restoration requires an intact frozen current primary and exact tombstone/key/
receipt/effect reconciliation. Missing proof or current authority denies serving.
No independent total-primary-loss deletion journal, durable client outbox,
supervised scheduler, encrypted rotation, production identity lifecycle, provider/
export/collector copy deletion or public deployment acceptance is claimed. R-06–10
and the seven additional limitations remain tracked in PHASE_9H_PRODUCTION_RISKS.
Final engineering status is independent of Public Production Readiness NOT APPROVED.

Final regression preparation also retained backend-final-oct20-r1 (850 pass,
2 compatibility-inventory assertions failed) and intentionally aborted superseded
backend-final-oct20-r2. The final r3 source retains all original26 baseline,
ten resource, three original erasure, Dataset-discovery and three new lifecycle
operation assertions separately. Contract7, Backend852 and admission27 now pass
on the final source; final focused/native/root records remain authoritative.
A concurrent admission run returned408 for a normal upload under its unchanged
0.5second total deadline; the subsequent serial27-case run passed without changing
any threshold. No timeout retry is hidden inside a passing test invocation.

Native r6 LifecycleFaults failed before its Busy prepare request: a host-created
Person was absent from the cached Person page, so a refreshed Relationship row
correctly displayed the unknown-name fallback. The named-row selector could not
match it. The final canonical scenario explicitly refreshes both Person and
Relationship lists before selection; every expiry, response-loss, same-key and
Busy assertion remains. No App/service behavior or timeout was changed. Because
the canonical input changed, all thirteen native scenes and twelve independent
regression captures are rerun under r7 / final-oct20-r5. Earlier r5/r6 successes
remain historical, not final current-fingerprint evidence.

The thirteen r7 canonical scenes all actually exited0 on runtime5b33ca19. The
first summary gate correctly refused LifecycleFaults' raw receipt-GET proof:
its recorded SQL/wire snapshot preceded replay, while later UI/replay assertions
were complete. A separate full original flow adds only a final `evidence` command
and records the post-replay signed receipt GET and SQL state. The original thirteen
reports are unchanged; no report is spliced. Gate validation still requires all
canonical commands, exact current runtime, independent exits, raw signed endpoint
proof and final-source binding of the supplement. Three counterexample tests reject
incomplete/changed/failed/stale executions and cross-execution endpoint borrowing.
All three signed endpoint proofs must come from the supplement's own full run.
Tool-only changes leave
all259 actual native executable inputs unchanged; all twelve service/client/tool
captures are nevertheless rerun under final-oct20-r6 before root acceptance.
Backend r6 and supplemental native r8 began before the final counterexample was
added; their actual logs/exits remain superseded. Final selection requires a fresh
Backend r7 and full supplemental native r9 with identical final start/end hashes.

Pre-marker-oct20-r1 actually exited1:115 repository tests found three historical
marker-compatibility assertions still rejecting now-authorized9F/9H, or relying on
another gate's incidental failure before the new valid matrix existed. Their
unsupported future marker is now9I; every old native/security assertion and
unsupported whole9/10 rejection remains. No service, App, threshold, canonical
native input or evidence-gate requirement changed. The failure log and its actual
exit/source stay immutable. Final full source is now d73bfa296be76bcaa79ef8dc362aaff8923997e7ccfbf2bd183bcc3744dc455d.
All259 native executable inputs remain exactly5b33ca19. Independent repository115
and lint pass under r10. All strict final-source service/client captures and the
complete independent native wire supplement are rerun under r10 before retrying
the original full pre/post root processes. Earlier final-labeled captures remain
superseded, not relabeled.

The r10 native supplement actually exited1 at its first UI tap after restarting
the emulator: the prior adb reverse mappings had not been restored. The failure
report/log/exit/source are preserved. Restoring only the original device-local
8092-to8093 and8024 forwarding fixes the environment; the unchanged complete flow
is independently restarted as r11. No data deletion occurred in the failed r10
sequence and no test/helper/source change was made for the rerun.

The r11 supplement reached its unchanged login step but no App request reached
the disposable fixture. The Expo bundle's device8022 endpoint must forward to
host8024, not host8022. Restoring this original mapping fixes the setup; r11's
failed report/log/exit/source stay preserved. During screen inspection a stale
Settings disclosure still claimed Person/Relationship erasure had no UI entry.
It now points to the implemented resource-detail confirmation and still states
that production account closure is absent. No behavioral test was added for this
copy-only correction. Because SettingsScreen is an actual native executable input,
all thirteen canonical native scenes are freshly rerun under r12, rather than
reusing r7. Final native fingerprint a237d19bce9a8f28a34a71e33f1c406e2601682e24d7372e78296716a95d41ee
and full source90a2e386fe1e23aa15056729db19eb99e22d8e0550a9df0e4dec7bafc5e95884.
The native wire supplement and every final independent regression are also r12.

Backend-final-oct20-r12 actually exited1 while native acceptance was active:
851 tests passed; the original finalize/cancel admission race received503 where
its normal successful-race assertion requires200/409. No code, assertion, timeout
or threshold is changed. The entire852-case suite will run independently as r13
only after the owned emulator/Metro/relay are stopped. This is a separately
recorded full retry, not an internal retry or a passing r12 result. Production
capacity/topology validation remains absent; the actual failed invocation is kept.

Actual compiled-source inspection then rejected Metro's cached pre-copy Settings
module (bundle SHA6317cf05d36dba4d77364c0a6d351aa754b2abf55339fd6d42bd07bef09fda45).
Its source map already returned current Settings sourcesContent; this was not
proof of the compiled JS. All r12 native results are SUPERSEDED, despite the nine
completed functional scenes exiting0. The partial Person run and followthrough
are ABORTED, with original logs and finite process metadata retained. Metro alone
was stopped for a cold rebuild; emulator storage and PostgreSQL data were kept.
9H-EVIDENCE-01/P1 now has a required actual-device compiled build digest, cold App
startup, checks after open/restart, and three counterexamples including Metro
configuration changes. The marker remains8/9G. All thirteen native scenes and
the complete wire supplement must run freshly on the final compiled source; all
strict service/client/tool records are also regenerated before pre/post roots.

Warmup-r14 refused a cold deep-link startup before the App root loaded; that
actual failed invocation remains. Warmup-r15 uses the existing established Expo
root URL and exits0 on final source, recording the actual Android-accessibility
digest5fce585ec817d956d3354f5a3c6fb170bd3c7358144b25a64ea38a6c0593a423.
The cold bundle now contains the corrected Settings disclosure and not its old
claim; SHA bf025ba76727f69c0635c7225c16ce25e08be93fb238f704606ec108ed2ee535.
Final full source0f6d1d92234581b322d1cb1cce7e9c5db49f82ed97b46def3b255acc91bb89e9;
native runtime743a3c876be160b5b3a01ec4e3506ad329e84eff18fb19d6ce62d95cf980d31f,
259 inputs. Nineteen9H tooling tests pass (repository total118). Native emulator
shut down cleanly for serial regression. Cleanup first refused unknown DevTools
dotslash/curl descendants; executable identities and exact owned ancestry were
verified before stopping them, retaining PostgreSQL SELECT1. No storage was wiped.
All final service/client/tool captures use r14; native13 plus full wire supplement
must follow a new cold build with actual-device digest proof before root acceptance.

### Preserved r14 SSE compiled-build preflight failure

All sixteen final independent service/client/tool captures exit0 on frozen source
0f6d1d92234581b322d1cb1cce7e9c5db49f82ed97b46def3b255acc91bb89e9.
The fresh r14 resource_create native scene exits0 with actual-device compiled
digest5fce585ec817d956d3354f5a3c6fb170bd3c7358144b25a64ea38a6c0593a423.
The next r14 sse_normal capture exits1 before any canonical business command:
the required compiled-build observer cannot obtain matching device proof within
its bounded startup window. Its original log/exit/source/report remain immutable.
The following Memory scene obtains matching proof; this does not establish the
cause of the SSE startup failure. No assertion, timeout or source is changed.
The other complete canonical scenes continue collecting independently. A separately
named full r15 SSE run is required; r14 SSE is never counted as a pass. Root
acceptance remains blocked unless every required complete scene and the independent
full wire supplement obtains its own actual proof and actual exit0.

### r14 startup observations and preserved receipt-query failure

The same initial proof check also refuses session, dataset, erasure_faults and
person. None reaches a canonical business command. A read-only diagnostic PNG
`evidence/phase9h/android-r14-dataset-startup-observation.png` shows the Android
launcher during the missing-proof window. Filtered platform activity/crash reads
do not establish a deeper cause. The following independent scenes can obtain the
correct digest; the existing canonical restart path (which waits after stop)
also obtains matching proof. Complete repeats will explicitly force-stop and
confirm the app is absent from the foreground before fixture initialization;
no storage is reset, assertion removed or proof timeout changed.

Conversation r14 is a distinct failure: actual signed execution returns a receipt,
target Conversation reads404, its messages are0 and the survivor keeps2 messages.
The UI asserts completed, Receipt ID and authoritative verified, then its canonical
tap on “查询正式删除回执” fails. All HTTP/SQL diagnostics and the failed command
remain unchanged; this partial run cannot satisfy acceptance. A separate complete
Conversation repeat, with read-only screen observation if the same tap stalls, is
required. No root advancement is allowed from partial assertions or borrowed wire
records. All current executable code and semantic contracts remain frozen at0f6d.
