# Phase 7A acceptance

Date: 2026-10-08 (Asia/Shanghai).

PHASE: Phase 7A — Expo React Native Foundation and Navigation Shell

STATUS: PASS — CODE, TEST, DOC, DEMO and REGRESSION verified before marker update.

ROADMAP PREFLIGHT: Initial marker `completed_phase=6`, `completed_subphase=6D`,
clean worktree, HEAD `56ebda4`. Read AGENTS, MASTER_PLAN, ARCHITECTURE, both
READMEs, workspace/package/lock configuration, Phase 6 final acceptance and
Phase 4 REST/SSE, Phase 5 Import, Phase 6 Memory contracts. Mobile initially
contained only README. Phase 7 is still Expo React Native MVP; Phase 8 is still
generated client/API/stream consumption. Baseline full `make verify` exited 0
with 448 backend tests, actual signed HTTP/PostgreSQL/socket demos and all
Phase 0–6 gates. Git commands use invocation-local safe.directory because this
checkout belongs to Administrators; no global Git setting was changed.

PACKAGE MANAGER AUDIT: Original packageManager pin retained: pnpm 11.25.0.
Global shim 11.7.0 auto-delegates inside the repository through pnpm's normal
download flow. Existing root lockfile expanded from its empty root importer
through actual dependency installs. Single pnpm lockfile, no npm/yarn install,
no force, no prerelease, no ignored peer conflict. Relative workspace store,
exact direct versions, reviewed build allowlist and frozen offline install
are reproducible. Peer audit reports no issues. All dependency tool commands
in this phase ran with project pnpm 11.25.0, not global 11.7.0.

NODE / PNPM VERSIONS: Node 24.15.0; project pnpm 11.25.0; global shim 11.7.0;
Corepack 0.34.6 available; uv 0.12.11. SDK 57 minimum Node 22.13.x is satisfied.

EXPO SDK: Stable 57.0.27; React Native 0.86.3; React/DOM 19.2.3; Router 57.0.25;
RN Web 0.21.3; TypeScript 6.0.3. Official compatibility matrix and registry
stable tags checked. `expo install --check`: dependencies up to date.
`expo-doctor` 1.20.4: **21/21 checks passed**. Relevant official sources are
linked in MOBILE_ARCHITECTURE.md. Exact companion native/test versions satisfy
all peers. Jest 29.7.0 matches jest-expo 57.0.5; RNTL 14.1.0's explicit
test-renderer 1.2.0 matches React 19.2's reconciler.

PROJECT STRUCTURE: Actual `apps/mobile` workspace package with app/, src/,
assets/, config, README, tests and browser smoke. Expo Router entry and Metro
Web run in this monorepo; no separate project was generated.

TYPESCRIPT: Strict and noUncheckedIndexedAccess enabled. `tsc --noEmit` passed,
including typed props, state union, navigation paths, fixture interface and
compile-time rejection of an empty state without its ViewModel. No business any,
strict suppression or application casts to bypass the contract.

EXPO ROUTER: Actual SDK 57 Stack, root providers, six route modules and
not-found recovery. Tests render actual route components/layout through Router's
testing library rather than replacing navigation with a fake implementation.

SIX SURFACES: Home `/`, Chat `/chat`, Relationship/Profile `/relationship`,
Import/Analysis `/import`, History `/history`, Settings `/settings` all reachable
in both component integration and live browser testing.

NAVIGATION: Home has one prominent Chat action and four secondary cards.
Every leaf has working pop-or-Home fallback; all five direct links and an
unknown URL recover correctly. No automatic redirect loop or dead route.
Native Android back is provided by Stack but not claimed device-tested.

DESIGN SYSTEM: Shared light/dark palettes, typography, spacing, radius,
48-unit minimum targets and bounded fluid layout. Default system preference,
with explicit light/dark choices that actually update colors and status bar.
Preference stays across navigation in one app session, resets on reload.

REUSABLE COMPONENTS: ScreenContainer, AppHeader, PrimaryButton, SectionCard,
EmptyState, LoadingState, ErrorState used by current pages and exercised by
tests. Shared DemoNotice/StatePreview provide truthful preview UI.

DEMO DATA BOUNDARY: UI reads ShellDataSource/SurfaceState/ViewModels from an
injected provider; fixture import occurs at composition only. Alternate-source
test and fresh-copy isolation test pass. No fake message, analysis conclusion,
user, upload, authentication or memory success. All pages say 本地演示 · Demo
and explicitly state the server is unconnected.

LOADING / EMPTY / ERROR: Four feature surfaces expose controlled, clearly local
previews. Loading is a held demonstration, not a request; Error Retry really
resets to empty. Tests cover these transitions independently on all four routes.

BASIC INTERACTIONS: Navigation, back, recovery, preference/state changes and
Retry have actual effects. Send/input, profile edit and file selection are
explicitly disabled/read-only. App information is visible in Settings.

RESPONSIVENESS: SafeAreaView, ScrollView, KeyboardAvoidingView, fluid bounded
width and wrapping controls. Browser checks 320/360/412px widths without
document horizontal overflow; screenshots reviewed. Chinese text wraps.
Device density, keyboard/insets and native Android layout remain NOT RUN.

ACCESSIBILITY: Buttons/navigation/input have readable labels/roles, state
controls expose selected/disabled semantics, errors have alert role and titles
have header semantics. Browser verifies back target height >=48px. Tests locate
controls by role/label. No TalkBack or full accessibility certification claimed.

NO DIRECT LLM / DATABASE: Application source boundary audit passes; no provider
secret, signing secret, DB URL, model/DB library or application network request.
Browser captures zero external application requests and zero page errors.
Owner authorization and memory mutation remain server-side; no Skill corpus or
Agent prompt is bundled. The unchanged server/knowledge regressions pass.

NO FAKE AUTH: No login UI or authenticated identity. Only truthful local Demo;
production auth and session storage remain deferred.

MOBILE TESTS: 23 component/integration/provider tests; strict contracts,
lint and format checks. One real Expo Web browser scenario covers route/back,
theme/system preference, state/Retry, disabled controls, screen sizes and recovery.
No snapshot-only proof or empty script is used.

EXPO WEB RUNTIME: **EXPO WEB SMOKE: PASS**. Actual Expo CLI/Metro on
`http://localhost:8087`, headless installed Chrome, Playwright 1.64.0.
Browser test reports **1 passed**, exit 0. Separate `expo export --platform web`
also exits 0 and emits a Web bundle/index. Export alone is not the runtime gate.
Screenshots `.cache/phase7a-home-light.png` and `.cache/phase7a-chat-dark.png`
were visually reviewed. Repeatable test and screenshots are retained locally.

ANDROID RUNTIME: **NOT RUN** — no usable adb/device/emulator in the session.
Only Web is accepted; no Android Device PASS, APK/EAS/native build claim.
Setup instructions and SDK-compatible Expo Go/development-build requirement
are documented. Android remains the intended final Mobile priority.

BACKEND REGRESSION: Full Phase 0–6 baseline and integrated final verifier use
real PostgreSQL 16.15 on localhost port 15434 and disposable test databases,
actual signed JWT verification, LangGraph/Mock LLM and real Uvicorn sockets.
Focused gates include Phase 6 E2E 32, Memory 7/10/26, Phase 5 import 19/6/8/10,
Phase 4 REST/JWT 47, SSE/disconnect 16, idempotency 17, standalone Phase 3 E2E 8.
Full backend is 448 tests, without skipped/xfail substitution. Golden annotation
83, replay subsets 24/30/38/14, frozen upstream validator/hash tests, migration
upgrade/downgrade/upgrade/check, Ruff and repository boundary all run.
Python/server/Agent code, uv.lock, golden dataset and frozen knowledge unchanged.

ROOT VERIFY: **PASS**, both pre-marker and final marker-aware `make verify`
exited **0**. Static gates are implemented in scripts/check_mobile.py and invoked
by `make verify` whenever the actual Mobile package exists, including before
marker advancement. Runtime smoke is explicitly separate. The script validates
project pnpm, strict/routes/boundaries, frozen offline install, compatibility,
typecheck, lint, formatting, tests and rejects any peer audit report of conflict.
No backend command starts Android/Chrome to claim Mobile demo success.

ARCHITECTURE DECISIONS: ADR 0029 records Stack/Home navigation, minimal injected
read-only ViewModels, session-local theme and separate static/runtime gates.
Architecture diagram clarifies the existing server's REST/POST SSE and future
Phase 8 integration; it does not introduce a new transport or change Phase 8.

FILES CHANGED: Mobile project/config/routes/components/theme/source/hooks/tests/
smoke/assets README; root package/workspace/pnpm lock/ignore; scripts/verify.py
and new scripts/check_mobile.py; root/Mobile READMEs; MASTER_PLAN, ARCHITECTURE,
new MOBILE_ARCHITECTURE, ADR 0029 and this acceptance report. project-phase.json
is updated only after verification. No unrelated server change.

KNOWN ISSUES: Android/TalkBack/device keyboard not verified. Theme choice is
session-only. Dependency deprecation notices exist in Expo's Jest/ESLint/native
toolchain; all compatibility/peer checks pass. The first install downloads peers
too new for SDK 57; explicit SDK-compatible Reanimated/Worklets, Metro and test
renderer pins resolve this rather than ignoring warnings. This host's System32
is absent from PATH; it is added for Playwright's normal taskkill cleanup.
Expo --localhost binds IPv6 ::1, so smoke uses localhost rather than 127.0.0.1.
Docker unavailable; existing local PostgreSQL used, no Docker PASS claimed.
Ordinary sandbox blocks registry/sockets, so approved execution runs the normal
tools. Expo rewrote the initial tsconfig include list on first startup; its
resulting strict config is committed and formatted. Neither that rewrite nor
failed initial smoke/static attempts were reported as passes.

DEFERRED: Phase 7B Chat and Relationship UI; full six-surface business behavior;
Phase 8 generated API client, JWT/token storage, Agent requests, progress SSE,
operation_key/run_id tracking, Import upload and Memory binding; production auth,
RAG, release/EAS pipeline and production backup/scheduler.

PROJECT PHASE MARKER: After the full pre-marker verifier exited 0 and the
separate live Web smoke passed, updated to `completed_phase=6`,
`completed_subphase=7A`; whole Phase 7 stays incomplete. Phase 7B and 8 are not
implemented. Final marker-aware verifier exited 0 with the accepted 6/7A marker.

NEXT: Phase 7B — Chat and Relationship UI. Stop after 7A; no 7B or Phase 8 work.

## Validation commands and evidence

From repository root, use project pnpm 11.25.0. Final gates run with:

```powershell
pnpm install --frozen-lockfile
pnpm peers check
pnpm --filter @goutou/mobile compatibility
pnpm --filter @goutou/mobile exec expo-doctor
pnpm --filter @goutou/mobile typecheck
pnpm --filter @goutou/mobile lint
pnpm --filter @goutou/mobile format:check
pnpm --filter @goutou/mobile test
pnpm --filter @goutou/mobile export:web
$env:PLAYWRIGHT_CHROME_PATH='C:\Program Files\Google\Chrome\Application\chrome.exe'
$env:PATH = 'C:\Windows\System32;' + $env:PATH
pnpm --filter @goutou/mobile smoke:web
$env:TEST_DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:15434/goutou_test'
$env:DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:15434/goutou_dev'
$env:PYTHONUTF8='1'
$env:PYTHONUNBUFFERED='1'
$env:PYTEST_ADDOPTS='--basetemp=.cache/phase7a-pytest-final -o cache_dir=.cache/phase7a-pytest-cache-final'
.\make.cmd verify
git -c safe.directory=F:/狗头军师app化/goutouapp diff --check
```

Preflight: `.cache/phase7a-preflight-verify.log`, exit 0, Phase 0–6 all PASS.
Web smoke: `.cache/phase7a-web-smoke.log` / `.json`, 1 passed, exit 0.
Web export: `.cache/phase7a-web-export.log`, exported dist, exit 0.
Pre-marker integrated gate: `.cache/phase7a-verify-pre-marker.log`, exit 0,
23 Mobile tests, 448 backend tests, 13 repository tests, all active gates PASS.
Post-marker integrated gate: `.cache/phase7a-verify-final.log`, exit 0,
23 Mobile tests, 448 backend tests, 13 repository tests, all active gates PASS.
Key final output:

```text
Completed phase: 6
Completed subphase: 7A
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
Tests: 23 passed, 23 total
No peer dependency issues found
PASS: Phase 7A Mobile static gates; runtime smoke is a separate command
PASS: all active Phase 0..6 and 7A static gates
```

Separate Web smoke returned 1 passed with skipped=0, unexpected=0, flaky=0.
`git diff --check` and staged diff check exited 0. Expo Doctor returned 21/21.
All logs/screenshots/output bundles remain ignored; no private chats or credentials
are included in the acceptance artifacts.
