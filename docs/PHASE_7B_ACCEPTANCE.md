# Phase 7B acceptance — 2026-10-08

PHASE: Phase 7B — Chat and Relationship UI.

STATUS: PASS — CODE/TEST/DOC/DEMO/REGRESSION accepted; final marker-aware verification also exits 0.

ROADMAP PREFLIGHT: Clean worktree at `e8deb8b` (accepted 7A); marker 6/7A.
Read AGENTS, MASTER_PLAN, ARCHITECTURE, MOBILE_ARCHITECTURE, SKILL_CONTRACT,
AGENT_RUNTIME, RELATIONSHIP_ANALYSIS, AGENT_API, STREAMING_API, IMPORTED_MESSAGES,
7A acceptance, current routes/source/tests and workspace package/lock.
Actual six routes and local shells confirmed; no Phase 8 client existed.
Frozen install/SDK compatibility passed; the actual 7A baseline ran 23 Jest
tests and one Expo Web scenario successfully. Doctor initially hit an Expo API
timeout; a later real online run returned 21/21, without disabling any check.

MOBILE TECH STACK: Actual installed Expo 57.0.27, RN 0.86.3, React 19.2.3,
Router 57.0.25, TypeScript 6.0.3, Node 24.15.0 and project pnpm 11.25.0.
Same 7A dependencies/theme/Stack; no SDK upgrade, added dependency or lock drift.

CHAT VIEWMODEL: Typed public user/assistant messages, scoped thread, controlled
composer, seven-state run presentation and FIU preview union. Imported sender
and internal tool roles are rejected by strict TypeScript tests. No private
runtime state, prompts, hidden reasoning, tool arguments or memory evidence.

CHAT MESSAGE LIST: One FlatList; stable message IDs instead of timestamps,
memoized rows, 12 initial/batch rows and windowSize 5. Plain selectable Text
handles long Chinese, emoji and paragraphs. User/assistant, Demo provenance
and time are visible. Tests preserve 1,000 equal-time messages, unique keys,
correct append order to 1,001 and bounded initial mounting. Append copies once
without sorting/pairwise conversions; no strict device performance claim.

CHAT COMPOSER: Accessible multiline input, Clear, whitespace validation,
2,000 UTF-16 unit limit, count and disabled semantics. SafeArea and keyboard
avoidance contain a separate fixed composer. Browser verifies the last appended
bubble above input and successful long-message scrolling; native keyboard NOT RUN.

LOCAL PREVIEW: **添加到本地预览** appends one user bubble, clears input and
reports **仅在本地预览，尚未发送给 AI**. No save, upload, log, Memory write or
formal history. Route unmount/reload/changed scope clear the local draft/list;
a still-mounted route retains its state. Demo notice remains in the fixed composer.

NO FAKE AGENT RESPONSE: Preview never generates an assistant. Only explicit
**替换为合成对话示例** loads the predefined anonymous template and replaces
the local list. It says the input has not been analyzed. Tests assert the
assistant count stays unchanged after subsequent local input.

CHAT STATE PRESENTATION: idle/unavailable/starting/progressing/completed/failed/
pending_confirmation are manually held, labeled Demo, with no timer/transport.
Loading/progress/pending disable input. Error uses a safe alert and Retry is a
real **Demo state reset** to idle, preserving messages/draft. No exception dump,
fake connection, token animation or generated result. Future status-then-final
presentation matches current Phase 4 SSE semantics.

FIU / SAFETY PRESENTATION: Completed preview contains synthetic fact with
provenance, tentative inference with alternative and explicit unknown. It is
teaching content, not analysis of input. Neutral Safety notice reserves display
space; no diagnosis, probability, mind-reading or manipulation. Pending explains
the required confirmation and disables execution; no Undo/Delete or bypass of
Phase 6B challenge. Current public answer DTO lacks structured FIU/profile;
Phase 8 mapping is documented instead of changing the server.

RELATIONSHIP VIEWMODEL: Distinct Person and Relationship IDs/models; nullable
nickname/type/interaction/history/analysis; known/missing lists and Demo source.
Generic classmate Demo A and incomplete Demo B; no romantic default.

RELATIONSHIP PROFILE UI: Title/current card, Person, known/missing information,
history metadata, unavailable analysis, history/Chat/Import entries and source
explanation. Editing remains disabled. Missing data shows **未提供** or empty
explanation; no invented name/date/conclusion. Injected empty source is tested.

RELATIONSHIP SELECTION: Accessible local A/B selection replaces all profile
fields; A's nickname/background/time/history disappear on B. Selected border
and state are visible. Chat push/back preserves the still-mounted B selection;
reload returns to first supplied profile.

DATA DOMAIN ISOLATION: Person, Relationship, imported RelationshipMessage and
Agent conversation roles remain separate. Only summary metadata appears in
Profile; no imported body is converted into an assistant or automatically analyzed.

DATA SOURCE BOUNDARY: Extended existing provider with readChat/readRelationships,
fresh nested typed values and no screen fixture import. Substituted Chat and
empty Profile sources work. Phase 8 needs a resource/controller and adapter;
these synchronous demo templates are not a copied wire schema.

NAVIGATION: Actual retained Expo Router tests cover all six routes, direct links,
back and unknown-route recovery. Profile passes selected relationshipId to Chat;
scope change clears Chat state. Unknown IDs show relationship unavailable without
falling back to A. Import and History entries navigate only to 7A shells.

RESPONSIVENESS: Browser flows at 320/360/412px in both light/dark themes, long
Chinese/emoji/multiline input and scroll. No document horizontal overflow;
input fits viewport; appended last bubble remains above composer. All 12 PNGs
(`phase7b-chat-{light,dark}-{320,360,412}.png` and corresponding relationship
images) were individually opened and visually inspected. Text wraps, local
feedback remains readable, and selected profile is visibly outlined.

ACCESSIBILITY: Input label; button/disabled semantics; sender labels;
status/feedback polite announcements; alert errors; selected controls with native
selected state and explicit Web aria-pressed. Browser exposed the missing RN Web
mapping during the first attempt; it was fixed and all flows rerun. Touch target
height >=48 retained in 7A smoke. TalkBack and native screen reader: NOT RUN.

PRIVACY / NO NETWORK: Anonymous synthetic fixtures only. Static gate forbids
application network calls, keys/provider/database access, screen fixture coupling,
console logging and storage APIs. Jest checks no fetch and no input logging;
browser tracks zero external/business requests and zero page errors. Only local
Expo/Metro asset traffic occurs. Input/screenshots are synthetic and ignored;
no private chat or secret appears in committed artifacts.

MOBILE TESTS: 47 tests pass (23 retained 7A + 24 Chat/Relationship focused),
three suites, zero snapshots. Strict typecheck, lint, formatting, frozen offline
installation, SDK compatibility and peer checks pass. Root gate separately runs
the two focused suites (24 tests), in addition to the complete Mobile suite.
The old 7A disabled-input expectation now verifies enabled local input and
disabled real server sending; its 23 test scenarios remain.

EXPO WEB RUNTIME: Actual Expo CLI/Metro on localhost:8087, installed headless
Chrome and Playwright. Seven scenarios pass: original 7A regression plus six
7B theme/width flows. No skipped/flaky substitution. Additional production Web
export is checked separately; export does not substitute for the live browser.

ANDROID RUNTIME: **ANDROID NATIVE SMOKE: NOT RUN**. SDK/adb exists outside PATH;
actual `adb devices -l` returns no attached device and `emulator -list-avds`
returns no configured AVD. No native launch, keyboard, Safe Area, hardware Back,
dark mode or scrolling is claimed. TalkBack: NOT RUN. Expo Web supplies the
MASTER_PLAN minimum runtime demo.

BACKEND REGRESSION: Full Phase 0–6 suite uses real local PostgreSQL 16.15 on
15434, disposable databases, signed JWTs, Uvicorn sockets and Mock LLM.
448 backend tests pass; focused Phase 6 E2E 32, Memory 7/10/26,
import parser/jobs/merge/API 19/6/8/10, REST/Auth 47, SSE/disconnect 16,
idempotency 17 and standalone Agent E2E 8. Golden annotations 83, replay subsets
24/30/38/14, migrations upgrade/downgrade/upgrade/check, frozen snapshot/hash
checks and 13 repository tests remain active. No server, runtime, memory,
import schema, Alembic, Python lock, golden data or frozen knowledge changes.

ROOT VERIFY: Complete pre-marker and final marker-aware `make verify` both
exit 0 with all active gates. Final output confirms 6/7B, 47 Mobile tests and
24 focused tests, 448 backend tests and 13 repository tests. Initial full backend
passed but integrated verification caught a Mobile React ref-during-render lint
failure; scroll revision now uses state and the standalone full static gate passes.
Root scripts include the explicit 7B focused gate whenever actual feature code
exists, before marker advancement. Live browser/Android gates remain separate.

ARCHITECTURE DECISIONS: [ADR 0030](adr/0030-mobile-chat-preview-and-relationship-scope.md)
records ephemeral local user-only preview, explicit synthetic template, scoped
profile selection, virtualized list/fixed composer and separate public state
presentation. ADR 0029 foundation/theme/navigation remain intact.

FILES CHANGED: Mobile Chat/Relationship routes; new contracts, feature screens,
message/composer/state components and synthetic source; provider interface;
shared selected semantics and optional shell EmptyState; shell narrowed to
Import/History; existing/new tests and browser smoke/config/package script;
root check_mobile/verify; Mobile README, MASTER_PLAN, ARCHITECTURE,
MOBILE_ARCHITECTURE, Chat/Profile docs, ADR 0030, this acceptance and phase marker.
No dependency or backend file changes.

KNOWN ISSUES: No connected Android device/AVD, native keyboard/insets or TalkBack
validation. Local drafts/selections intentionally reset as documented. FIU/profile
wire mapping awaits Phase 8. Toolchain deprecation/NO_COLOR notices are retained;
no peer conflict or check is suppressed. Initial Doctor network, Web selected
mapping and lint failures were corrected/retried rather than counted as PASS.

DEFERRED: Phase 7C Import/History/Memory Settings UI; Phase 8 generated client,
API/SSE/auth/token management/upload/history persistence/Memory mutation;
OAuth, RAG, backend refactoring and release pipeline. No part was started.

PROJECT PHASE MARKER: After the complete pre-marker verifier, static gates,
Doctor and live Web smoke passed, advanced only to
`completed_phase=6`, `completed_subphase=7B`. Whole Phase 7 remains incomplete.

NEXT: Phase 7C — Import, History and Settings UI. Stop after 7B acceptance;
do not start 7C or Phase 8.

## Reproducible validation commands

From repository root:

```powershell
node --version
pnpm --version
pnpm install --frozen-lockfile
pnpm --filter @goutou/mobile compatibility
pnpm --filter @goutou/mobile exec expo-doctor
pnpm mobile:verify
pnpm --filter @goutou/mobile test:features
$env:PLAYWRIGHT_CHROME_PATH='C:\Program Files\Google\Chrome\Application\chrome.exe'
$env:PATH='C:\Windows\System32;'+$env:PATH
pnpm --filter @goutou/mobile smoke:web
pnpm --filter @goutou/mobile export:web
$taskAndroidSdk=Join-Path $env:LOCALAPPDATA 'Android\Sdk'
& (Join-Path $taskAndroidSdk 'platform-tools\adb.exe') devices -l
& (Join-Path $taskAndroidSdk 'emulator\emulator.exe') -list-avds
$env:TEST_DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:15434/goutou_test'
$env:DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:15434/goutou_dev'
$env:PYTHONUTF8='1'
$env:PYTHONUNBUFFERED='1'
$env:PYTEST_ADDOPTS='--basetemp=.cache/phase7b-pytest-pre-marker -o cache_dir=.cache/phase7b-pytest-cache'
.\make.cmd verify
# After gates pass and marker changes: use a distinct final basetemp/cache.
git -c safe.directory=F:/狗头军师app化/goutouapp diff --check
```

Ignored evidence: `.cache/phase7b-preflight-web.log`, `phase7b-expo-doctor.log`,
`phase7b-mobile-static.log`, `phase7b-web-smoke.log/.json`, `phase7b-web-export.log`,
`phase7b-verify-pre-marker.log` and `phase7b-verify-final.log`, screenshots and
browser results. Pre-marker root, Mobile static, Doctor, Web smoke and export
all exited 0. Final marker-aware root command also exited 0; no skipped/xfail
or unavailable environment verification is counted as a pass.

Final root evidence (`phase7b-verify-final.log`):

```text
Completed phase: 6
Completed subphase: 7B
Ran 13 tests ... OK
goutoujunshi validation passed
PASS: isolated Alembic upgrade head / downgrade base / upgrade head / check
32 passed (Phase 6 E2E)
448 passed (full backend)
Golden annotation validation passed: cases=83
Repository secret boundary check passed
All checks passed!
158 files already formatted
PASS: project pnpm 11.25.0
Dependencies are up to date
All matched files use Prettier code style!
Tests: 47 passed, 47 total
Tests: 24 passed, 24 total (explicit focused gate)
No peer dependency issues found
PASS: Phase 7B Chat/Relationship focused gate; runtime smoke is separate
PASS: all active Phase 0..6 and 7A static gates and 7B focused gate
```

Separate runtime JSON reports expected=7, skipped=0, unexpected=0, flaky=0;
Web smoke exit 0, export exit 0, Doctor 21/21. Final working and staged
`git diff --check` exit 0. Logs/build/screenshots remain ignored.
