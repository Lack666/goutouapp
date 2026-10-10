# Phase 8C acceptance — 2026-10-09 (Asia/Shanghai)

Current evidence: see the **2026-10-10 revalidation** addendum below. It preserves
this historical report and adds an actual native core smoke plus a logout fix.

PHASE: Phase 8C — Agent Chat REST / POST SSE Integration

STATUS: PASS — CODE, TEST, DOC, actual Web/socket DEMO and REGRESSION passed.
Full root verification exited0 both before and after advancing to7/8C. This is
Web engineering acceptance; ANDROID CONNECTED SSE: NOT RUN, whole Phase8 incomplete.

ROADMAP PREFLIGHT: HEAD5b14f11, clean worktree, marker7/8B. Read required plans,
architecture/contracts/handoffs/7-final/8A/8B acceptance and actual source/tests.
Existing signed SSE/Disconnect/Idempotency33 and retained Mobile143 actually passed
with new parser/controller tests in the full207-case run. Initial preflight used a
nonexistent test filename; corrected33-case execution is the acceptance evidence.
No Agent behavior, upstream snapshot, provider core contract or future-phase change.

EXISTING AGENT / SSE AUDIT: Actual routes/schemas/AgentService/persistence/auth,
operation fingerprint/replay/conflict/disconnect and public Agent History checked.
V1 is POST JSON/Bearer progress plus a complete committed answer, not token deltas.
Expo57.0.27 installed fetch/reader/TextDecoder source and official SDK57 docs audited.

GENERATED CLIENT: Existing unchanged36-operation authority/client reused for REST,
Conversation verification and History; SSE string has a separately audited V1 union.

CONNECTED CHAT: Shared composer/FlatList/theme/navigation; real resource selector,
states/draft/keys/IDs/read-only receipts and actual committed text. Demo retained.

REAL CONVERSATION SCOPE: Owned GET first, UUID validation, nullable generic/bound
scope and relationship assertion; foreign/missing404 neutral, invalid scope fail closed.

AGENT REST: Generated body/response, real JWT, actual run/Conversation/assistant IDs,
memory/warnings, safe auth/validation/conflict/recovery and uncertain completion.

POST SSE TRANSPORT: Native expo/fetch adapter/Web standard fetch, shared8B session,
origin/epoch/401/cancel, JSON POST,60-second deadline through reader and explicit race.

SSE PARSER: Independent incremental parser, blank delimiters/LF/CRLF/CR/multiline
data/comments/EOF/invalid JSON/version/event,128KiB frame/512KiB total bounds.

UTF-8 / CHUNK BOUNDARIES: Every two-part byte split and single-byte Chinese/emoji,
partial JSON and CRLF tested; incomplete/illegal UTF-8 fail closed.

EVENT V1 MAPPING: All seven public event types validated/mapped; status separated
from answer, committed text before completed, failed/unknown and read-only memory.

RUN ID: One immutable server run per logical operation; mismatch/old event rejected.

OPERATION KEY: Crypto UUIDv4 reserved with immutable payload before send; duplicate
click guard; per-Conversation retry, new explicit messages get new keys only after
known terminal outcome. Keys are session-memory, bounded20 attempts, no durable outbox.

IDEMPOTENT RETRY: Actual postcommit REST response loss and SSE completed-frame loss,
same-key recovery, concurrent attempts; DB run/user/assistant counts and provider calls
unchanged on replay. Memory counts unchanged; positive Memory replay also remains
covered by retained Phase4 PostgreSQL tests, not inferred from the zero-memory fixture.

UNKNOWN OUTCOME RECOVERY: No automatic new key; original REST/SSE retry or History.
Running/busy/unresolved explicit; History cannot prove a run's final metadata status.

REST/SSE CROSS-REPLAY: Both directions preserve run and Message IDs with no execution.

DISCONNECT / CANCEL: Reader cleanup/page blur/scope/background/logout/expiry isolation;
actual Phase4 socket pre/postcommit cases retained. Client stop never claims rollback.

SESSION / OWNER ISOLATION: Shared8B token only, guarded navigation stack reset;
old HTTP/events rejected, all state cleared on OwnerA→B. Actual foreign404/emptyB UI.

AGENT HISTORY: Generated public Message pages, bounded cursor continuation/refresh,
timestamp+UUID order/equal timestamps/empty/error/retry/scope reset and reload recovery.

MESSAGE DEDUPLICATION: Server Message ID only, identical bodies remain distinct.
Pending submission shown as status, not an optimistic formal user bubble. Confirmed
SSE/REST assistant shares actual History ID; refresh never adds a duplicate reply.

MEMORY STATUS: Read-only receipt/pending explanation; no formal Memory HTTP mutation.

FIU / SAFETY PRESENTATION: Only committed text/public progress; no inferred FIU DTO,
node state, hidden reasoning, prompt or synthetic fallback in Connected Chat.

DEMO MODE REGRESSION: Original seven previews/local composer/fixtures remain unchanged;
full Demo browser regression is included in root verify.

REAL JWT HTTP: CLI15-minute signed JWT, actual production verifier/HTTP/PostgreSQL.

REAL SSE SOCKET: Actual FastAPI POST SSE/MockLLM/AgentService/LangGraph in3 integration
scenarios; no mock-fetch substituted for server execution/authentication.

POSTGRESQL PERSISTENCE: Completed run/user/assistant IDs/owner/Conversation and exact
counts checked after real loss/replay/concurrency, formal History recovery and isolation.

EXPO WEB CONNECTED E2E: Actual Chrome/Expo sends POST SSE, displays completed answer,
replays REST, reloads/re-enters volatile credential and recovers History, logs out/B clears.
Browser revealed empty-stack dismissAll error; canDismiss guard fixed it. First recovery
test incorrectly used full document navigation after credential entry; SPA navigation
now exercises the intended volatile Web lifecycle. Failed attempts are not PASS evidence.

ANDROID NATIVE CONNECTED E2E: ANDROID CONNECTED SSE: NOT RUN. Actual Pixel_10
launch with no-snapshot/no-boot-anim/no-audio/software GPU did not produce an adb
device;127.0.0.1:5555 connection refused10061. Captured launch/crashpad logs under
`.cache/phase8c-android-launch.*.log`; no app/reader/UTF-8/native credential/Back/
keyboard PASS. Explicit local native Mock backend/CLI/network steps provided;
whole Phase8 must still obtain actual Android evidence.

MOBILE TESTS: Pre-marker full216, then final expiry case and focused parser28/
controller42/UI4 passed (74 new total); prior143 retained. StrictTS, lint, formatting,
offline frozen install, clean peers, SDK/Doctor21/21 and generator3 passed. Android
JS export passed independently. Accepted-marker full217 passed (143 retained +74 new),
including parser28 and controller42/UI4. No failed or unexecuted check is counted.

BACKEND REGRESSION: Retained555, all Agent/Import/Memory, Golden83, repository27,
actual migration cycle/check, frozen knowledge and Ruff170 passed. No runtime/provider/
schema/contract/lock resolution changes.

ROOT VERIFY: Pre-marker full PASS exit0 at7/8B, `.cache/phase8c-verify-pre-marker-clean.log`.
Earlier attempts failed a retained8B resource-only path assertion (Chat now legitimately
GETs formal Agent History), then one test-file formatting gate. Updated the assertion
to allow only that scoped History route, retaining all3 cases/no Agent POST/Import/
Memory; fixed formatting. Those failed logs are retained and not counted as PASS.
Accepted-marker full rerun at7/8C PASS exit0, `.cache/phase8c-verify-final.log`:
backend555, repository27, Golden83, Mobile217, Demo Web22, resources3 and Agent Chat3.

VALIDATION COMMANDS / OUTPUT: Actual commands and final results are recorded below.

ARCHITECTURE DECISIONS: ADR0033; shared authenticated transport, narrow V1 validation,
explicit unknown outcomes, ID-based History reconciliation and per-page consumption.

FILES CHANGED: Mobile transport/event/parser/platform adapter/controller/Chat UI,
shared composer/list/session/navigation and retained8B browser expectations; new unit/UI/
real socket/browser suites; optional Mock composition in disposable fixture and an
executable native manual backend/CLI entry; root gates, docs/ADR/scripts.
Knowledge/contracts/uv/pnpm resolution/Agent/Import/Memory untouched.

KNOWN ISSUES: Android native execution NOT RUN; pending keys lost on process restart,
no durable outbox/reconciliation/reattachment; public History lacks run association and
SSE final answer lacks timestamp. Cursors are live views. These limits are visible;
no automatic resend, invented time/status or production/provider quality claim.

DEFERRED: 8D Import/RelationshipMessage history;8E Memory controls; production auth,
real provider smoke/quality, FIU/Profile DTO and final Android verification.

PROJECT PHASE MARKER: completed_phase=7, completed_subphase=8C, advanced after all
applicable engineering gates passed. Whole Phase8 IN PROGRESS / NOT YET COMPLETE.

NEXT: Phase 8D — Chat Import and History Mobile Integration. Stop after8C, do not start8D/8E.

## Executed commands and evidence

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONUNBUFFERED='1'
$env:TEST_DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:15434/goutou_test'
$env:DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:15434/goutou_dev'
$env:PLAYWRIGHT_CHROME_PATH='C:\Program Files\Google\Chrome\Application\chrome.exe'
$env:PATH='C:\Windows\System32;'+$env:PATH
uv --cache-dir .cache/uv --no-managed-python run --locked pytest -q apps/server/tests/test_agent_stream_contract.py apps/server/tests/test_agent_stream_api.py apps/server/tests/test_agent_stream_disconnect.py apps/server/tests/test_phase4_idempotency.py
pnpm --filter @goutou/mobile test
pnpm --filter @goutou/mobile test:sse
pnpm --filter @goutou/mobile test:agent-chat
pnpm --filter @goutou/mobile smoke:agent
$env:PYTEST_ADDOPTS='--basetemp=.cache/phase8c-pytest-pre-marker-clean -o cache_dir=.cache/phase8c-pytest-pre-marker-clean-cache'
.\make.cmd verify # exit0, marker7/8B; full216 plus focused46, parser28
# Advance only to7/8C after gates; mandatory accepted-marker rerun:
$env:PYTEST_ADDOPTS='--basetemp=.cache/phase8c-pytest-final -o cache_dir=.cache/phase8c-pytest-final-cache'
.\make.cmd verify # exit0, marker7/8C; Mobile217, backend555, Demo22/resources3/Agent3
pnpm --filter @goutou/mobile exec expo export --platform android --output-dir ../../.cache/phase8c-android-export
```

Actual focused74 and socket/Web3 pass. The native manual backend/CLI was also
executed over actual HTTP/PostgreSQL: completed REST and2 formal messages, private
configuration removed on stop. It is not native-device proof. Credentials travel through internal
pipes; no tracing/video/screenshots. Evidence under ignored `.cache` is never staged.

## 2026-10-10 revalidation (Asia/Shanghai)

PHASE: Phase 8C — Agent Chat REST / POST SSE Integration

STATUS: PASS — applicable engineering CODE/TEST/DOC/DEMO/REGRESSION gates.
Actual Android core streaming smoke passed; full native lifecycle/fault acceptance
remains PARTIAL. Whole Phase8 remains IN PROGRESS / NOT YET COMPLETE.

ROADMAP PREFLIGHT: Actual HEAD was f4cb2cc, clean worktree, marker7/8C;
the requested expected7/8B state was already superseded by that committed8C work.
Read the required plans, contracts, handoff and7-final/8A/8B acceptance, then
audited real code/tests and reran all gates. No phase was skipped or advanced.

EXISTING AGENT / SSE AUDIT: Rechecked actual routes, request/response schemas,
AgentService persistence, V1 envelopes/order, JWT/owner scope, operation lookup,
pre/postcommit disconnect and public Message History. Transport remains POST JSON,
Bearer and text/event-stream, with progress plus a committed full answer.

GENERATED CLIENT: PASS; unchanged36-operation OpenAPI and generated client,
all26 pre-8A contracts preserved, generation/drift tests3. No new wire DTO or endpoint.

CONNECTED CHAT: PASS; existing real composer/FlatList/controller/theme/navigation,
shared8B JWT/session/origin and actual server text retained. No synthetic fallback.

REAL CONVERSATION SCOPE: PASS; actual owned generic Conversation verified before
sending; retained scope tests cover bound/mismatched/Demo IDs. Native OwnerB's
request for OwnerA's Conversation shows the neutral resource denial and no messages.

AGENT REST: PASS; generated request/result, real JWT, persisted run/assistant IDs,
memory/warnings and safe failures. Native same-key REST replay also observed.

POST SSE TRANSPORT: PASS; existing native expo/fetch reader and shared transport.
Actual SDK57 docs/source audited. Native safety and ordinary Chinese runs exercised
the actual FastAPI/AgentService/LangGraph/MockLLM/PostgreSQL path through adb reverse.

SSE PARSER: PASS; focused28 tests and real socket/native frames. Independent bounded
incremental parser retained; no network-chunk/frame assumption or token delta added.

UTF-8 / CHUNK BOUNDARIES: PASS; all existing byte splits/Chinese/emoji/CRLF/invalid
UTF-8 tests retained. Actual native Chinese complete answer decoded without replacement
characters. Deliberately splitting a UTF-8 character on the native socket was NOT RUN;
the exhaustive parser byte-split tests remain its separate evidence.

EVENT V1 MAPPING: PASS; all seven event unions tested. Native ordinary run observed
run_started, seven public status events, final_response and completed across8 reader
chunks. A prior safety run observed7 events across5 chunks. Read-only memory/pending
and failed events remain covered by parser/controller and retained server integration.

RUN ID: PASS; native ordinary run7605edc7-27f1-423e-8a25-a2c5e34f1e5b remained stable
on REST/SSE replay; persisted owner/Conversation/assistant association verified.

OPERATION KEY: PASS; native key8157712c-6296-42f1-93cf-32dec1dea26c retained across
replay. Existing timeout/loss/payload immutability and duplicate-click tests retained.

IDEMPOTENT RETRY: PASS; real Web/socket loss/concurrency and all Phase4 PostgreSQL
tests passed again. Native REST plus SSE replay left exactly1 completed Run and2
Messages; no duplicate bubbles after History refresh. Native replay added only
final_response/completed (aggregate reader probe10 chunks/12 events). Memory rows0;
positive Memory replay is proven by retained Phase4 tests, not by this zero-row fixture.

UNKNOWN OUTCOME RECOVERY: PASS; no automatic new key, truthful running_unknown,
controlled original-key retry/History. No live-run reattachment or durable outbox added.

REST/SSE CROSS-REPLAY: PASS; both directions through real signed socket tests;
native SSE→REST and SSE persisted replay also observed with unchanged database IDs.

DISCONNECT / CANCEL: PASS in focused controller and real Phase4 socket tests;
native Back after completion returned to the prior screen. Active native disconnect,
page leave during execution, background interruption and token-expiry cancellation:
NOT RUN. Do not infer those native fault cases from Web/unit success.

SESSION / OWNER ISOLATION: PASS; old epochs/events/401 cannot update a new owner.
Native credential restoration, logout and OwnerA→B foreign denial observed.
Native testing found no_token was published before asynchronous SecureStore deletion
finished; immediate process termination could restore the old token. Fixed reset to
invalidate in-memory credentials/requests immediately, show clearing, and publish
no_token only after storage confirms deletion. Failure shows storage_error; older
clear completions cannot replace a new epoch. Actual updated App logged in, logged
out, waited for no_token, was force-stopped/restarted and still showed no_token.
Killing the process while clearing is pending can still interrupt storage removal;
the UI now explicitly asks the user to keep the App open until completion.

AGENT HISTORY: PASS; generated owned pages, cursor/equal-time/order/refresh/scope
tests retained. Actual Web reload and native re-entry loaded formal Messages.

MESSAGE DEDUPLICATION: PASS; authoritative IDs, equal-text distinct occurrences,
confirmed final/History reconciliation; native run remains one user/assistant pair.

MEMORY STATUS: PASS; read-only statuses/confirmation explanation only. No8E mutation.

FIU / SAFETY PRESENTATION: PASS; public text/progress only, no inferred FIU DTO;
native safety response and ordinary Chinese validated answer observed separately.

DEMO MODE REGRESSION: PASS; all retained seven previews/local input and22 real
browser scenarios passed after the shared-session change. No Demo business requests.

REAL JWT HTTP: PASS; existing development CLI/production verifier, actual sockets
and disposable PostgreSQL. Native credentials passed via private subprocesses/input,
never printed or captured while being entered.

REAL SSE SOCKET: PASS; retained signed/disconnect/idempotency integration plus3
real8C socket/browser scenarios; successful requests are not mock fetches.

POSTGRESQL PERSISTENCE: PASS; native ordinary Conversation6bad7e5f-c0d5-4d9e-8830-
4857867a9ff6 belongs to owner70092684-3c13-4368-8543-68a2c05cdac9. Both cross-retries
and OwnerB denial preserved1 Run,2 Messages and0 Memory rows. Native fixtures were
stopped, disposable databases dropped and private CLI config removed.

EXPO WEB CONNECTED E2E: PASS; final Demo22, retained8B resources3,8C Agent Chat3.
Actual Chrome/Expo/FastAPI/PostgreSQL/MockLLM, not an Android inference.

ANDROID NATIVE CONNECTED E2E: CORE SMOKE PASS / FULL LIFECYCLE PARTIAL. Actual
Pixel_10, emulator-5554, sdk_gphone16k_x86_64, Android17/API37, Expo Go57.0.9.
App launch, signed JWT, owned Conversation, incremental POST SSE, Chinese answer,
completed, History, REST/SSE replay, postcompletion Back, credential restoration,
logout/restart and OwnerB denial observed. A temporary local QA route wrapped the
actual ConnectedChatScreen/shared session/production parser and reader to record
only chunk/event/Unicode counters. It was removed before final root verification.
No QA route, observer or automatic synthetic send is shipped. Synthetic-only native
screenshots and sanitized counts remain ignored under.cache. Keyboard text entry
and hide were used; complete keyboard-obstruction/TalkBack QA remains NOT RUN.

MOBILE TESTS: PASS; final219 (prior217 retained +2 logout persistence cases).
Focused parser28, Chat controller/UI46, connected50,7B24,7C35,7D13. StrictTS,
lint/format, frozen offline install, peer audit, compatibility and Doctor21/21 passed.
The retained Demo-switch test now checks immediate clearing and final no_token;
its original isolation assertion remains. No old scenario was removed or skipped.

BACKEND REGRESSION: PASS;555 full backend,32 Phase6 E2E, resources97, all earlier
Agent/Import/Memory/socket demos, Alembic cycle/check, Golden83, repository27,
frozen knowledge/secret boundary and Ruff170 formatted files. Provider core unchanged.

ROOT VERIFY: PASS twice at the unchanged7/8C marker: pre-fix baseline217 and final
219. Both full approved runs exited0. Final log ends with all active Phase0..7
and8A/8B/8C PASS, Phase8 IN PROGRESS / NOT YET COMPLETE.

VALIDATION COMMANDS / OUTPUT: Same documented environment variables above;
actual commands included .\make.cmd verify, focused test:connected/test:agent-chat,
typecheck/format:check, native backend `--port 8020 --scenario chinese`, Expo --lan on
isolated native ports, adb reverse/devices/deep-links/input/Back/force-stop, sanitized
PostgreSQL queries and actual native reader observations. Evidence:
`.cache/phase8c-20261010-verify-approved.log`,
`.cache/phase8c-20261010-verify-final.log`,
`.cache/phase8c-20261010-native-reader.json`,
`.cache/phase8c-20261010-native-safety-evidence.json`,
`.cache/phase8c-20261010-native-chinese-final-evidence.json`.
Initial sandbox verification failed on pytest temp-directory access; the approved
rerun passed. Two focused lifecycle expectations initially failed after the new
clearing state, then were corrected/strengthened and all suites rerun. These failed
attempts are excluded from PASS. Native localhost download failed because Metro
listened on IPv6; --lan plus IPv4 reverse worked. adb later hung and was recovered
by restarting its confirmed server. Runtime.evaluate was unsupported; it supplied
no probe evidence. DevTools dotslash installation used a fallback after a cross-drive
rename warning. None of those attempts is counted as a successful native check.

ARCHITECTURE DECISIONS: Preserve ADR0033 and the single session/runtime/transport.
Separate immediate in-memory invalidation from acknowledged durable credential
removal. Disposable native demo adds optional port/Chinese scenario using existing
standalone Mock queues. No new dependency, ADR, API, schema or infrastructure required.

FILES CHANGED: Shared DevelopmentSession/controls;2 new session-isolation tests and
strengthened retained connected test;native demo;Mobile README;8C acceptance,
MASTER_PLAN/ARCHITECTURE/Chat/Streaming/API-client/resource/development-auth/handoff
documentation.
Temporary native route deleted. Knowledge, generated authority/client, locks and
project marker unchanged.

KNOWN ISSUES: Native active-run faults/background/expiry, deliberate native UTF-8
character split and complete keyboard/TalkBack QA remain NOT RUN. Pre-confirmation
process death can interrupt credential deletion; clearing is not a completed logout.
Existing volatile operation keys/outbox/history association/FIU limitations remain.

DEFERRED:8D Import/RelationshipMessage History;8E Memory network controls; full native
lifecycle acceptance, production auth/provider quality/reconciliation and public FIU.

PROJECT PHASE MARKER: completed_phase=7, completed_subphase=8C, unchanged.
Whole Phase8 IN PROGRESS / NOT YET COMPLETE; no marker rollback or future advance.

NEXT: Phase 8D — Chat Import and History Mobile Integration.
Stopped after8C.8D/8E/8F were not started.
