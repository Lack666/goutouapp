# Phase 7C acceptance — 2026-10-08 (Asia/Shanghai)

PHASE: Phase 7C — Import, History and Settings UI

STATUS: PASS — CODE, TEST, DOC, DEMO and REGRESSION passed before marker update.
Final marker-aware full verification also exited 0.

ROADMAP PREFLIGHT: Initial HEAD `2168f0f`, clean worktree, marker `6 / 7B`.
Read AGENTS, MASTER_PLAN, ARCHITECTURE, MOBILE_ARCHITECTURE, MOBILE_CHAT_UI,
MOBILE_RELATIONSHIP_UI, IMPORT_API, IMPORT_JOBS, IMPORTED_MESSAGES, MEMORY_API,
MEMORY_DELETION, MEMORY_RETENTION, 7A/7B acceptance and current routes/components/
contracts/source/tests. Existing 47 Mobile tests passed before changes. All six
routes remain accessible; Import/History/Memory Settings were shells, and no
Phase 8 client existed. Phase 7 remains Expo React Native MVP; Phase 8 remains
Mobile API integration/generated client/stream consumption. Whole Phase 7 is pending.
Git uses invocation-local safe.directory because the checkout belongs to
Administrators; no global Git configuration is changed.

MOBILE TECH STACK: Unchanged Expo 57.0.27, RN 0.86.3, React 19.2.3,
Router 57.0.25, TS 6.0.3, Node 24.15.0, project pnpm 11.25.0.
Frozen install, Expo compatibility, peer audit and Doctor 21/21 passed.
No dependency addition/upgrade or lockfile modification.

IMPORT VIEWMODEL: Typed summary/inventory/wizard, discriminated speaker draft,
relationship draft, five-step presentation state and local readiness, supplied
through readImport. Fresh anonymous pair/group/empty fixtures; no ORM/wire schema copy.

IMPORT WIZARD: Source → Speakers → Relationship → Readiness → Result.
Next/Back/edit/reset work. Unloaded/empty sources block Next. Invalid readiness
blocks Result. No automatic success/timer/network action. Reset/unmount/reload
and changed route scope remove local source/bindings/confirmation/step.

PARSER SUMMARY: Source format, message/speaker counts, historical first/last dates,
Asia/Shanghai, warning explanation and possible-duplicate hint shown from fixtures.
No current date substituted; warning is not a fatal parser verdict.

SPEAKER BINDING: Raw `我`, `匿名同学🌱`, `系统通知🔔` and group `匿名参与者🌿`
preserve label/Emoji/source/count. All start unbound. User explicitly chooses
self/person/system/ignore and then a Person ID for person. No identity inference.

RELATIONSHIP BINDING: Incoming ID is preserved but not confirmed automatically.
Explicit local confirmation required. Changing the draft relationship clears
all speakers/confirmation and returns to identity confirmation. Unknown IDs fail
closed; Person must match the selected Relationship's Person.

IMPORT READINESS: One self/one selected Person, confirmed existing relationship,
no unbound speaker, compatible Person, nonempty loaded source. Issues displayed;
local preview expressly does not mean server ready.

GROUP CHAT HANDLING: More than two explicitly bound humans rejects one-to-one
readiness; extra participants are not silently merged. System/ignore require user
selection, matching Phase 5B semantics.

NO FAKE IMPORT / ANALYSIS: Disabled picker/upload/finalize/AI actions. Final text
only reports demo precheck completion and future real import. Synthetic analysis
overview explicitly is not analysis of source/input; fact/provenance, tentative
inference/alternative and unknown are separated. No Job/message/Memory write exists.

HISTORY VIEWMODEL: Discriminated Agent versus relationship item contracts,
separate roles/senders, filter/page models, historical timestamp, dataset/source
index, raw label, scope, stable IDs and synthetic provenance. Negative TS cases
reject mixed domains/roles.

HISTORY DOMAIN SEPARATION: AI user/assistant and external self/person/system are
separate views. Person is never AI assistant. Chat local-preview input never enters
the read-only History source or claims server persistence.

HISTORY PAGINATION: One FlatList, no outer ScrollView, initial/batch 12,
windowSize 5, local window 30, More increments at most 30, disabled at end.
Tests retain all 1,020 messages per scope, unique composite keys, equal-time and
cross-dataset ordering, timezone-aware instant ordering, all 34 pages, immutability
and bounded initial mounting. No content dedup or actual network cursor.
This is not a native-device performance benchmark.

HISTORY RELATIONSHIP SCOPE: Exact relationship filtering precedes sorting/windowing.
Missing/repeated scope fails closed. Selecting B clears A's loaded state/window/
filter; B rows only. General AI example has null scope, external history requires
selection. Empty/loading/error/Retry/reset and scoped Chat/Import actions work.

SETTINGS VIEWMODEL: Typed control, public record summary/scope/dates/state,
read-only expected Undo preview, deletion target/scope/count/review stage and
retention notices. Templates injected through readSettings; no server operation IDs.

MEMORY CONTROL PREVIEW: Consent/pause are independent. Grant preserves pause;
revoke pauses and retains inspectable samples; resume while revoked does not grant.
Feedback is 本地演示状态已更新, with polite announcement semantics.

UNDO / DELETE UI: Undo Preview → Expected Operation explanation → disabled guarded
execution. One/person/all delete shows scope/count/consequences; all requires an
explicit preserve/revoke choice before local acknowledgement. New choice/target
resets acknowledgement, Cancel works. Formal execute is always disabled. No sample
is deleted; UI acknowledgement is not a challenge or frontend server confirm flag.

RETENTION / PRIVACY PRESENTATION: 示例保留策略：180 天; actual server policy
is authoritative. Expired cannot be recalled; cleanup may lag; primary deletion
does not erase backups/logs immediately. Inspection warns historical facts may be
outdated. No raw evidence/operation internals/hidden reasoning; no fake account.
Theme is session-local and application version/environment are truthful.

CROSS-PAGE RELATIONSHIP SCOPE: Relationship B → Import → History → Chat carries
explicit ID; return retains mounted B profile. Switching/reset/route-scope change
prevents A data/bindings from remaining. Changed profile route scope remounts its
selection. Feature unmount/reload/restart resets previews; still-mounted push/back
can retain them. Theme remains independent and root-session scoped.

DATA SOURCE BOUNDARY: Screens/components consume injected typed read-only models;
fixtures remain in data modules. Substituted import/history/settings sources and
empty models tested. No new global state store or local persistence.

RESPONSIVENESS: Real Chrome checks 320/360/412px in both themes, no document
horizontal overflow, Chinese/Emoji and long paragraphs. Thirty 7C screenshots
generated; ten representative wizard/readiness/history/inspect/delete PNGs across
widths/themes visually reviewed. Labels wrap and disabled/selected states remain clear.

ACCESSIBILITY: Existing semantic headers, readable controls/labels, 48-unit targets,
selected/disabled semantics, alert errors and polite Memory feedback retained.
Native TalkBack, keyboard/insets/back and full accessibility certification NOT RUN.

PRIVACY / NO NETWORK: Synthetic anonymous fixtures only. Static gate and tests
check no business network APIs, storage/log calls, key prefixes, private phone/email
fixtures or screen-to-fixture coupling. Browser records zero business requests,
page errors and console errors. Expo/Metro development requests are excluded.
No actual upload/local parser/Agent/SSE/Memory API/OpenAPI/JWT/SecureStore is added.

MOBILE TESTS: Final static run: 82/82 tests, retained 47 7A/7B plus 35 new 7C;
explicit 7B gate 24/24 and 7C gate 35/35. Frozen install, SDK, peer, strict TS,
lint and format pass. No strict setting or test gate is disabled.

EXPO WEB RUNTIME: Real Expo/Metro and headless installed Chrome: 13/13 PASS,
expected=13/skipped=0/unexpected=0/flaky=0. Includes retained 7A/7B, complete B wizard,
explicit identities/confirmation/readiness, B-only History/More/AI separation,
scoped Chat, Settings pause/resume/inspect/undo/delete confirmation and Home return,
reload/reset and unavailable history. Web export separately PASS (not runtime proof).

ANDROID RUNTIME: **ANDROID NATIVE SMOKE: NOT RUN**.
SDK android-37.0, adb 1.0.41 (37.0.1), emulator 37.1.11 present. `adb devices -l`
empty; `emulator -list-avds` empty; no system-images directory or configured AVD.
There is no launchable existing native target. No native PASS inferred from Web;
MASTER_PLAN allows this real Web demo as minimum proof. No SDK/system configuration
was changed.

BACKEND REGRESSION: Pre-marker .\make.cmd verify exited 0: 448 full backend tests,
32 Phase 6 signed HTTP/MockLLM/PostgreSQL E2E cases, Phase 5 parser/jobs/merge/API
(including 10k), Phase 4 REST/auth/SSE/disconnect/idempotency, Phase 3 standalone
runtime/replays, real existing socket demos, 13 repository tests, Golden 83,
Alembic upgrade/downgrade/upgrade/check, frozen upstream/secret boundary, Ruff.
No backend, migration, frozen knowledge, Python or JS lockfile changed.

ROOT VERIFY: Pre-marker complete verifier PASS, including explicit 7C gate.
That first root run had 81 Mobile/34 focused tests; the subsequently added wizard
unmount case and stronger paging/reload/console assertions passed full Mobile
static (82/35) and browser (13). Final marker-aware verifier: PASS, exit 0, with
82 Mobile / 24 7B / 35 7C, 448 backend, 32 Phase 6 E2E, 13 repository tests,
Golden 83, migrations/frozen upstream/secret boundary/Ruff and every prior gate.

ARCHITECTURE DECISIONS: Extend the existing read-only provider seam with typed
feature templates, ephemeral controllers and narrow scope helpers; retain separate
history domains and guarded-operation boundary. No architecture replacement or
new infrastructure warrants another ADR; prior ADR 0029/0030 remain applicable.

FILES CHANGED: Mobile Import/History/Settings routes/features/contracts/fixtures,
HistoryList/RelationshipSelector, scope helper, small shared live-feedback addition,
existing Chat/Relationship scoped navigation/guards, new/retained Jest/browser tests,
package test script/Playwright evidence paths, root Mobile/verifier gates,
root/Mobile README/architecture/Chat/Relationship docs, three new UI docs, MASTER_PLAN,
phase marker and this report. Home, backend, knowledge and locks are untouched.

KNOWN ISSUES: Native Android/device keyboard/insets/hardware Back/TalkBack untested.
Local feature state resets as documented. Fixture history is held locally despite
bounded rendering; no native performance claim. Existing NO_COLOR/toolchain update
notices remain without suppression or upgrades. Initial test-query/semantic
expectation errors were corrected, not counted as PASS. No external service key
or account is required for this UI.

DEFERRED: Phase 7D full MVP integration/final acceptance; Phase 8 real file flow,
generated API client/auth/stream/history/memory integration. Coordinate public
FIU/Profile/Person/Relationship resource and Agent-history-list contracts; current
answer DTO does not expose full FIU/profile and import finalize does not analyze.
Cross-file partial overlap dedup, production scheduler/backup/release remain deferred.

PROJECT PHASE MARKER: After pre-marker CODE/TEST/DOC/DEMO/REGRESSION passed,
advanced only to completed_phase=6, completed_subphase=7C. Whole Phase 7 incomplete.

NEXT: Phase 7D — Mobile MVP Integration and Phase 7 Final Acceptance.
Stop after 7C. Phase 7D and Phase 8 are not started.

## Reproducible commands and evidence

Run from the repository root (private .env remains local):

```powershell
node --version
pnpm --version
pnpm install --frozen-lockfile
pnpm --filter @goutou/mobile compatibility
pnpm --filter @goutou/mobile exec expo-doctor
$env:PYTHONUTF8='1'
pnpm mobile:verify
pnpm --filter @goutou/mobile test:controls
pnpm --filter @goutou/mobile export:web
$env:PLAYWRIGHT_CHROME_PATH='C:\Program Files\Google\Chrome\Application\chrome.exe'
$env:PATH='C:\Windows\System32;'+$env:PATH
pnpm --filter @goutou/mobile smoke:web
$taskAndroidSdk=Join-Path $env:LOCALAPPDATA 'Android\Sdk'
& (Join-Path $taskAndroidSdk 'platform-tools\adb.exe') devices -l
& (Join-Path $taskAndroidSdk 'emulator\emulator.exe') -list-avds
Test-Path -LiteralPath (Join-Path $taskAndroidSdk 'system-images')
$env:TEST_DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:15434/goutou_test'
$env:DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:15434/goutou_dev'
$env:PYTHONUNBUFFERED='1'
$env:PYTEST_ADDOPTS='--basetemp=.cache/phase7c-pytest-final -o cache_dir=.cache/phase7c-pytest-cache-final'
.\make.cmd verify
git -c safe.directory=F:/狗头军师app化/goutouapp diff --check
```

Ignored evidence: .cache/phase7c-preflight-mobile.log, phase7c-frozen-install.log,
phase7c-compatibility.log, phase7c-expo-doctor.log, phase7c-mobile-static.log,
phase7c-web-export.log, phase7c-web-smoke.log/.json, phase7c-web-results,
phase7c-verify-pre-marker.log, phase7c-verify-final.log and phase7c-*.png.
The Windows make target is make.cmd; no unavailable GNU make check is called PASS.

Final root evidence (phase7c-verify-final.log):

```text
Completed phase: 6
Completed subphase: 7C
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
Tests: 82 passed, 82 total
Tests: 24 passed, 24 total (7B focused)
Tests: 35 passed, 35 total (7C focused)
No peer dependency issues found
PASS: Phase 7C Import/History/Settings focused gate; runtime smoke is separate
PASS: all active Phase 0..6 and 7A static gates and 7B focused gate and 7C focused gate
```

Separate runtime gates: Doctor 21/21; export exit 0; real Web smoke exit 0,
expected=13/skipped=0/unexpected=0/flaky=0. Working/staged git diff checks pass.
Only this Phase 7C work is committed; build/results/fixtures evidence remains ignored.
