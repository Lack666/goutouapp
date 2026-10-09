# Phase 7 final acceptance — 2026-10-09 (Asia/Shanghai)

PHASE: Phase 7D — Mobile MVP Integration and Phase 7 Final Acceptance

STATUS: PASS — CODE, TEST, DOC, DEMO and REGRESSION passed before marker advancement.
Both required complete root verifiers exited 0, including the final marker-aware run.

ROADMAP PREFLIGHT: Initial HEAD `6f9e17c`, clean worktree, marker `6 / 7C`.
Read AGENTS, MASTER_PLAN, ARCHITECTURE, Mobile architecture and all five feature
UI contracts, 7A/7B/7C acceptance, workspace/lock/package, routes, typed models,
data sources, components, tests, smoke, check_mobile and verifier. Phase 7 is
Expo React Native MVP; Phase 8 remains API/generated-client/stream integration.
No roadmap conflict or uncommitted user work. Invocation-local Git safe.directory
handles the checkout's Administrators ownership without changing global settings.

PHASE 7A AUDIT: Stack/root source/theme, six routes, shared presentation and
real theme changes retained. All 23 foundation cases retained. Initial actual
Mobile baseline passed 82 tests; reports alone were not used as proof.

PHASE 7B AUDIT: Chat/Profile code and all 24 focused cases retained. Seven
presentation states, explicit synthetic assistant examples, single virtualized
list, stable IDs and local-only multiline input remain. The first-message scroll
defect found by the new browser journey was fixed without redesigning Chat.

PHASE 7C AUDIT: Five-step wizard, separated history domains, 1,020-message
per-relationship fixture and all 35 focused cases retained. Existing import
tests were strengthened to assert earlier identity/confirmation gates instead
of expecting navigation past unconfirmed steps. No old scenario was removed.

SIX SURFACES: Home, Chat, Relationship/Profile, Import/Analysis, History and
Settings are real interactive local UI. Leaf back/fallback, Demo labels,
loading/empty/error recovery and formal disabled actions remain readable.
Home now renders its actual source loading/error state rather than a blank screen.

COMPLETE CROSS-PAGE JOURNEY: Nine new `smoke/integration.spec.ts` cases include
six full journeys (light/dark × 320/360/412px): Home → Relationship B → Import
source → explicit self/Person B/system-or-ignore → relationship confirmation →
readiness → Demo result → B History → 30/60/90 windows → scoped Chat → four-line
Chinese/Emoji user-only local preview → Stack back through History/result/B
Profile/Home → Settings controls/inspect/Undo/delete confirmation → reset →
reload → Home. Three other cases cover invalid/direct routes, scope/lifecycle
reset and empty/incompatible/group imports. All execute real Expo Web/Chrome.

RELATIONSHIP SCOPE: Existing and new component/browser tests check A/B profile
replacement, incoming/outgoing IDs, B-only imported history, unchanged B on
push/back, A→B history domain/window reset and Chat draft/messages/pending reset.
Unknown, blank, repeated-identical, conflicting and malformed IDs fail closed.
No missing relation silently chooses A or binds a Person.

NAVIGATION / DEEP LINKS: Root and all five direct leaf URLs return correctly;
unknown path recovers Home. All four scoped routes reject six malformed query
cases each in real Chrome. Reload honors explicit relationship ID but clears
ephemeral feature state; direct entry has an in-App Home fallback.

CHAT ACCEPTANCE: Whitespace blocked; Clear, bounded multiline Chinese/Emoji,
long text and actual append/scroll work. Input adds one user message and states
`仅在本地预览，尚未发送给 AI`. Only explicit fixture action creates predefined
assistant display. Seven run states remain independent of messages; starting/
progressing/pending disable composer and pending formal execution is disabled.
Latest bubble is verified above composer for first multi-line and long-list cases.
The fix waits for the last row's layout before consuming the pending scroll revision.

RELATIONSHIP ACCEPTANCE: A/B selection replaces all profile fields, missing B
values remain missing; no romantic label or relationship analysis is inferred.
Source/historical notices and three scoped leaf actions remain accurate.

IMPORT ACCEPTANCE: All five steps work with Back/edit/reset. Source must be
loaded/nonempty; speakers must explicitly include one self and one selected
Person with every label handled before advancing; relationship must explicitly
confirm before readiness. Person compatibility/group exclusion still guard
result. Raw labels/Emoji are preserved, `我` is never automatically self.
Changed relationship clears bindings/confirmation; changed route clears wizard.
Empty source, missing Person, incomplete binding and invalid relationship cannot
pass gates. Local readiness/result are clearly prechecks; actual picker, parser,
upload, finalize and AI analysis remain disabled.

HISTORY ACCEPTANCE: Agent user/assistant and imported self/person/system domains
stay separate. Exact relationship filtering precedes deterministic historical
time/dataset/source-index/ID ordering. Equal timestamps and duplicate content
preserve occurrences; keys remain stable. Existing tests exhaust all 1,020
external occurrences per relationship and all local pages, with bounded initial
mounting. Browser verifies More, source/scope changes, error hiding/Retry, reset
and empty states. FlatList/30-row windows retained; no network cursor is claimed.

SETTINGS ACCEPTANCE: Local grant/revoke/pause/resume/inspect, retention disclosure,
Undo Preview and one/person/all deletion scope remain aligned with Phase 6.
Revoke retains inspectable fixtures; resume does not grant; pause does not delete.
Expired examples cannot be recalled; 180 days remains only a policy example.
Delete-all requires explicit preserve/revoke choice, changing choice clears
acknowledgement, and formal deletion/undo stay disabled after acknowledgement.
No sample/cloud Memory is saved/deleted and no frontend challenge is invented.

LIFECYCLE / RESET: Push/back retains mounted controllers. Unmount/remount,
reload and scope changes clear documented draft/list/binding/filter/window state.
Import/History/Memory resets work and theme remains independent, session-local;
reload resets it to system. No preview becomes persistent or appears in saved history.

DATA SOURCE BOUNDARY: All surfaces still consume typed source/ViewModels;
fixture modules remain outside components. Empty substituted relationship sources
fail closed across all four related screens; empty Memory inspect/undo works.
Home loading/error is visible. Agent and imported message types stay distinct.
No new state library, ApiClient, ORM DTO copy or unnecessary abstraction.

ANDROID USER-MANUAL VALIDATION: **USER-MANUAL ANDROID SMOKE: REPORTED PASS**.
The user reported after 7C that Android Studio emulator operation showed no
obvious problem. This is later supplemental human evidence. The user's AVD,
Android version/model and individual keyboard/TalkBack steps were not provided;
none are inferred from Codex's separate SDK audit. Historical 7C NOT RUN remains
unchanged and truthful for that report's execution time.

ANDROID CODEX VALIDATION: **CODEX ANDROID SMOKE: NOT RUN / attempted launch
could not complete**. Initial `adb devices -l` was empty; `emulator -list-avds`
reported `Pixel_10`. One launch briefly exposed `emulator-5554`, model
`sdk_gphone16k_x86_64`, Android release 17/API 37, installed Expo Go 57.0.9.
Codex started existing Metro (8088), reverse and Expo Go deep-link commands,
but the emulator subsequently disconnected; retries exposed an unresponsive
shell and no completed App interaction/screenshot. A tracked default-renderer
retry also ended. SDK lock writes initially needed normal approved execution;
that failed sandbox attempt was not counted as a runtime pass.
No independent native page/keyboard/insets/hardware-Back/theme result is claimed.
No SDK upgrade, prebuild, new Android project or APK was generated.

ANDROID AUTOMATED VALIDATION: **NOT RUN**. No native UI test completed.
Android APK / Development Build: **NOT BUILT** (existing Expo Go used for attempts).
Native multi-line Chinese keyboard, latest bubble, scroll recovery and Back:
**NOT RUN independently**. User's general manual feedback is not evidence that
these individual steps or native automation passed.

EXPO WEB E2E: **PASS**, actual Expo/Metro on localhost:8087 and installed
headless Chrome. 22/22 scenarios, retained 13 + nine new; no skipped/flaky
replacement. New complete six-page paths pass in all width/theme combinations.
Web export is a separate build check, not a substitute for runtime proof.

RESPONSIVENESS: 320/360/412px, both palettes, long Chinese/Emoji, multi-line
composer, scrolling lists and confirmation descriptions pass existing/new
browser checks with no document horizontal overflow. Screenshots are synthetic
and ignored. Representative final Chat and delete-preview images are reviewed
before completion (light-320/dark-412 Chat and dark-320/light-412 confirmation).
Only component/browser performance is assessed; no native
FPS, memory usage or real large-upload benchmark is claimed.

ACCESSIBILITY: Existing labels/roles, selected/disabled semantics, alerts,
polite feedback, headers and minimum 48-unit controls retained and queried in
tests. Native TalkBack: **NOT RUN**; complete accessibility certification is not claimed.

PRIVACY / NO NETWORK: Static source scan, component fetch/log spies and real
browser request audit show no business requests, provider credentials, JWT,
DB URL, storage/log calls, real contacts or private conversations in Mobile.
Only normal Metro assets are permitted. Local typed text stays ephemeral.
No Mobile LLM, real Agent/Memory/import request or fabricated server success.

PHASE 8 API HANDOFF: [audited handoff](PHASE_8_MOBILE_INTEGRATION_HANDOFF.md)
checks actual source, generated OpenAPI and docs. Confirmed Agent REST/POST SSE,
import upload/binding/ready/finalize/receipt/history and Memory controls/challenges/
receipts; explicit gaps for public Conversation/Person/Relationship resources,
Agent history, FIU/Profile DTOs and imported-data analysis workflow. Production
account issuance is absent; development CLI is not a production login API.

BLOCKING ISSUES FOUND: No P0 discovered. Three P1 findings:
import Next skipped intermediate identity/relationship confirmation; first
multi-line Chat bubble remained below visible list after preview; Home source
loading/error returned blank UI. Each has new component or actual browser
regression. Settings' stale 7C implementation label was also removed.

BLOCKING ISSUES FIXED: All three P1 findings fixed with component/browser
regression; no known P0/P1 remains in the accepted local Web MVP.

REMAINING NON-BLOCKING ISSUES: Native smoke/keyboard/Back/TalkBack and native
performance remain independently unverified because the emulator did not stay
usable. Fixture arrays are held in local memory despite bounded list rendering.
Feature/appearance state is intentionally session-local. Current SDK toolchain
deprecation/NO_COLOR notices remain; compatibility/peer checks are not suppressed.

MOBILE TESTS: **95/95**, original 82 + 13 new. Explicit 7B 24/24, 7C 35/35,
7D 13/13. Frozen install, exact pnpm 11.25.0, Expo compatibility, Doctor 21/21,
strict TypeScript, lint, format and peer audit passed. Dependencies/locks unchanged.

BACKEND REGRESSION: **PASS**, both complete root runs: 448 full backend cases,
32 Phase 6 HTTP/MockLLM/PostgreSQL E2E, Phase 5 import
(including 10k), Phase 4 REST/SSE/disconnect/idempotency, Phase 3 graph/replays,
Golden 83, Alembic cycle/check, frozen upstream/secret boundary and Ruff.
All 17 repository tests pass (retained 13 plus four completion-marker cases).

ROOT VERIFY: **PASS**, both complete runs exited 0; final output is
`PASS: all active Phase 0..7; Phase 8 PENDING`.

PRE-MARKER RESULT: **PASS**, complete `.\make.cmd verify`, exit 0
at `6 / 7C`, including 95 Mobile/24 7B/35 7C/13 7D tests, export and all 22 browser
scenarios, plus 448 backend and every prior gate. Evidence: phase7d-verify-pre-marker.log.
The new verifier runs focused 7D tests plus actual export/browser regression;
it accepts only complete `7 / 7D` and rejects Phase 8+ markers. Four repository
tests exercise those completion/future-marker boundaries.

POST-MARKER RESULT: **PASS**, complete `.\make.cmd verify`, exit 0 at `7 / 7D`:
17 repository, 448 backend, 32 Phase 6 E2E, 95 Mobile, 24/35/13 focused tests,
22 Web scenarios, Golden 83, migration cycle/check, Ruff, upstream and secret
boundaries. No skipped/flaky replacement. Evidence: phase7d-verify-final.log.

FILES CHANGED: Three minimal feature fixes, Chat list scroll correction,
strengthened import tests, new 7D component/browser suites and scripts, verifier
and marker tests, runtime evidence paths, final acceptance/API handoff,
root/Mobile README and architecture/UI/MASTER_PLAN updates, and finally marker.
Server, DB schemas, frozen knowledge, golden cases and locks remain untouched.

ARCHITECTURE DECISIONS: Preserve ADR 0029/0030, source/theme/Stack, feature-local
state and separate message domains. Add deterministic step gates and wait for
actual row layout before marking latest-message scroll handled. Root completion
now requires real Web runtime regression instead of relying on historical PASS.
No replacement architecture or extra infrastructure warrants a new ADR.

KNOWN LIMITATIONS: Native runtime-specific checks did not complete; state is
local/ephemeral, fixture data is synthetic and full arrays are held locally.
Web/component validation is not native performance or accessibility certification.

DEFERRED: Auth/session/generated SDK/API/SSE/network cursor,
real upload/binding/import/analysis/Memory mutation, public resource gaps,
live-model quality, production account system, RAG, scheduler/backup/release.
Phase 7 completion does not connect any of those Mobile business capabilities.

PHASE 7 FINAL STATUS: **PASS**, CODE/TEST/DOC/DEMO/REGRESSION and both root runs complete.

PROJECT PHASE MARKER: After all pre-marker gates passed, `completed_phase=7`,
`completed_subphase=7D`. Phase 8 stays PENDING; no Phase 8 implementation begins.

NEXT: Phase 8 — Mobile API Integration, Generated Client and Stream Consumption.
Stop after Phase 7D. Phase 8 requires a new explicit instruction.

## Validation commands / output and reproduction

Run from the repository root. Use local test databases ending in `_test`, as
documented in [Database](DATABASE.md); private configuration is not committed.

```powershell
pnpm install --frozen-lockfile
pnpm --filter @goutou/mobile exec expo-doctor
$env:PYTHONUTF8='1'
pnpm mobile:verify
pnpm --filter @goutou/mobile test:integration
pnpm --filter @goutou/mobile export:web
$env:PLAYWRIGHT_CHROME_PATH='C:\Program Files\Google\Chrome\Application\chrome.exe'
$env:PATH='C:\Windows\System32;'+$env:PATH
pnpm --filter @goutou/mobile demo:final
pnpm --filter @goutou/mobile smoke:web
$taskSdk=Join-Path $env:LOCALAPPDATA 'Android\Sdk'
& (Join-Path $taskSdk 'platform-tools\adb.exe') devices -l
& (Join-Path $taskSdk 'emulator\emulator.exe') -list-avds
# Configure TEST_DATABASE_URL/DATABASE_URL to the documented local test/dev DBs.
$env:PYTHONUNBUFFERED='1'
$env:PYTEST_ADDOPTS='--basetemp=.cache/phase7d-pytest-pre-marker -o cache_dir=.cache/phase7d-pytest-cache'
.\make.cmd verify
# After all gates and marker update, repeat with a distinct final basetemp/cache.
git -c safe.directory=F:/狗头军师app化/goutouapp diff --check
```

Final Demo: `demo:final` launches Metro plus Chrome, performs six complete
journeys and three recovery scenarios, writes JSON and screenshots, and closes
the browser/server. For interactive use, run `pnpm --filter @goutou/mobile web`
and follow the complete cross-page journey described above. No server/key required.
Settings retains a local theme selection through navigation; reload resets it.

Ignored evidence: `.cache/phase7d-frozen-install.log`, `phase7d-baseline-mobile.log`,
`phase7d-expo-doctor.log`, `phase7d-mobile-static.log`, `phase7d-focused-mobile.log`,
`phase7d-web-smoke.log/.json`, `phase7d-web-results`, final Chat/confirmation PNGs,
`phase7d-openapi.json`, `phase7d-openapi-audit.log`, native attempt/Metro logs,
`phase7d-verify-pre-marker.log`, `phase7d-verify-final.log`.
Initial selector-test and Chat-scroll failures are superseded only by complete
reruns; none are counted as passed.

Final root evidence (`phase7d-verify-final.log`):

```text
Completed phase: 7
Completed subphase: 7D
Ran 17 tests ... OK
goutoujunshi validation passed
PASS: isolated Alembic upgrade head / downgrade base / upgrade head / check
32 passed (Phase 6 E2E)
448 passed (full backend)
Golden annotation validation passed: cases=83
Repository secret boundary check passed
All checks passed!
158 files already formatted
Tests: 95 passed, 95 total
Tests: 24 passed, 24 total (7B)
Tests: 35 passed, 35 total (7C)
Tests: 13 passed, 13 total (7D)
No peer dependency issues found
Exported: dist
22 passed (real Expo Web)
PASS: Phase 7 Expo React Native MVP
PASS: all active Phase 0..7; Phase 8 PENDING
```

Final browser JSON: expected=22, skipped=0, unexpected=0, flaky=0.
Working and staged diff checks passed; stage commit contains only Phase 7D
changes. Generated bundles, raw logs and screenshots stay ignored.
