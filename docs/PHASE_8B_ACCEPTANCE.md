# Phase 8B acceptance — 2026-10-09 (Asia/Shanghai)

PHASE: Phase 8B — Generated TypeScript API Client, Auth Session and Owned Resource Integration

STATUS: PASS — CODE, TEST, DOC, real Web/HTTP DEMO and REGRESSION passed before
marker advancement and in the full accepted-marker rerun (exit0). Android connected remains NOT RUN as explicitly permitted
for this subphase; whole Phase8 remains IN PROGRESS / NOT YET COMPLETE.

ROADMAP PREFLIGHT: Initial HEAD 6f4221a, clean worktree; read required plans,
architecture, handoffs/contracts/current Mobile/source/router/controller/tests
and verifier. 8A resource97/Mobile95 actually passed; deterministic OpenAPI36
and historical26 checked. No uncommitted user work, Agent/SSE Mobile networking
or roadmap objective change. Invocation-local Git safe.directory preserves global config.

OPENAPI GENERATION: Locked 7.13.0 generator in compatible TS5 tool workspace;
Mobile stays TS6. Authoritative OpenAPI only, generated callable client plus typed
contracts, UUID formats, optional/nullable fields, auth inventory and errors.

GENERATED CLIENT: Generated paths/components/operations and createApiClient over
openapi-fetch0.17.0; typed application adapters, no duplicate wire DTOs.

GENERATED CONTRACT DRIFT: Byte check, input SHA256, LF, repeat generation and
mutated-input/output tests; server contracts unchanged.

API TRANSPORT: Configurable public origin, injected current Bearer, cancellation,
timeout, safe HTTP/network normalization, current-epoch 401 invalidation and
resource-only allowlist. Browser fetch receiver defect caught and fixed by real smoke.
Accepted-marker focused timeout test exposed a missing guaranteed cancellation
completion; transport now races explicit timeout/cancel rejection through fetch
and body reads, including an injected fetch implementation that ignores abort.
The failed attempt is retained in `.cache/phase8b-verify-final-attempt-timeout.log`,
not counted as PASS. Subsequent focused48 and connected3 tests passed before rerun.

DEVELOPMENT AUTH: Manual hidden JWT entry, actual CLI issuer and server probe;
no production-login claim, signer, refresh or bundled credential.

TOKEN STORAGE: SecureStore57.0.4 native adapter read/write/delete tested; actual
native persistence NOT RUN. Web volatile only, reload clears. No token fixtures,
logs, test snapshots, traces/video/screenshots or public secret environment variables.

TOKEN EXPIRY: Local deadline/foreground/request checks and server401 cleanup;
expired/invalid/offline/storage states, new CLI credential required.

LOGOUT: Synchronous token invalidation, all lists/details/cursors/selections/create
attempts/errors cleared, requests aborted, forms remounted and secure deletion queued.
Old navigation stacks/query IDs are also discarded, returning to Settings.

SESSION / OWNER ISOLATION: User A→B clears all domains and stale-response guards;
real signed HTTP owner rejection, empty B lists and browser logout/reload checks.

DEMO VS CONNECTED MODE: Existing Phase7 source/controllers remain Demo; Connected
uses real confirmed resources and unavailable deferred business screens, with no fallback.

PERSON INTEGRATION: Actual create/list/detail, UUID/name/times and explicit states.

RELATIONSHIP INTEGRATION: Explicit owned Person/type/status, list/detail with Person
read, no inferred romance/Profile; missing/foreign/error states fail closed.

CONVERSATION INTEGRATION: Explicit generic or owned relation binding, create/list/
detail/selection; real server UUID, no Agent execution.

RESOURCE CREATION IDEMPOTENCY: Crypto UUIDv4 retained per original request. Lost
response retry for all three domains and concurrent creates verified with committed
PostgreSQL counts. Changed payload409. Row lifetime only; client pending attempts
are session-memory, no permanent receipt/outbox/delete API.

PAGINATION: Bounded opaque domain cursors, guarded More, visible-ID deduplication,
error retry, reset/logout cleanup and latest-request detail selection. Backend
equal-time regression retained; generated-client real multi-page read exercised.

ERROR HANDLING: 401/404/409/422/503, timeout/offline/cancel/protocol safe messages;
raw response/error bodies never surfaced or logged.

REAL JWT HTTP INTEGRATION: PASS — CLI-signed real15-minute JWT, actual FastAPI socket,
PostgreSQL and generated Mobile controller. Single-row lost-response retry for
Person/Relationship/Conversation; six concurrent Person creates leave one row.

EXPO WEB CONNECTED E2E: PASS — real Chrome/Expo browser and signed backend resource
flows, edited-form retry retains original semantics, UUID navigation, A→B clearing,
expired/malformed, offline recovery and server401 invalidation. Three integration
tests; no mock success or authentication override. Credentials remain in process pipes.

ANDROID CONNECTED RUNTIME: NOT RUN — two Pixel_10 launch attempts logged boot,
then exited with no stable adb device; localhost5555 refused. No on-device SecureStore,
background/restore/logout/network PASS claimed. Doctor21/21 and JS export are
separate checks. Reproduction steps in MOBILE_RESOURCE_INTEGRATION.md; final Phase8
still requires actual Android connected evidence.

MOBILE TESTS: PASS143 (existing95 + new48), focused8B48; existing7B24/7C35/7D13
retained. StrictTS6, lint, formatting, frozen offline install, SDK compatibility,
peer audit and Doctor21/21 pass. Generated3 reproducibility/drift tests pass.

BACKEND REGRESSION: PASS555 (retained545 + new CORS10), focused8A97, all Agent/
REST/SSE/Import/Memory, migration cycle/check and prior demos. Repository24,
Golden83, frozen knowledge and Ruff169 pass. Both OpenAPI snapshots/uv lock unchanged.

ROOT VERIFY: Full pre-marker .\make.cmd verify PASS, exit0 at7/8A. Evidence
`.cache/phase8b-verify-pre-marker.log`; old Web22 and connected3 passed. Marker
advanced after all gates. Accepted-marker full rerun also PASS, exit0 at7/8B;
evidence `.cache/phase8b-verify-final.log` includes backend555, Mobile143,
Demo Web22, Connected3 and all previously completed phase gates.

ARCHITECTURE DECISIONS: ADR0032; generated authority, separate compatible toolchain,
credential adapters/session epochs, real-resource controller seam, narrow local CORS.

FILES CHANGED: Mobile generated client/adapters/transport/session/storage/resources
UI/controller/context; native dependencies/plugin and root pnpm lock/tool workspace;
CORS settings/middleware/tests; signed disposable fixture and actual browser tests;
root gates/marker tests; docs/ADRs/readmes and public address example. Upstream,
Agent/Import/Memory behavior, golden cases, uv lock and both contract snapshots unchanged.

KNOWN ISSUES: Android connected behavior unverified on this host; resource retry
reservation is row-lifetime and client pending bodies disappear on restart/logout.
Opaque pages are committed live views rather than fixed snapshots. Production
account issuance/refresh and prior scheduler/backup limitations remain.

DEFERRED: 8C Agent Chat REST/POST SSE; 8D import/upload/binding/formal message history;
8E Memory network controls/mutations; production accounts, public FIU/Profile,
imported-data analysis, optional RAG and final Android proof. No future phase begun.

PROJECT PHASE MARKER: completed_phase=7, completed_subphase=8B, after all required
pre-marker gates. Whole Phase8 in progress; 8C not started.

NEXT: Phase 8C — Agent Chat REST / POST SSE Integration. Stop after 8B; do not start8C.

## Reproduction and evidence

Commands executed from the root on the existing local PostgreSQL16.15 cluster.
The harness creates/drops randomized migrated `_test` databases; no SQLite,
development-database substitute, JWT verifier override or live LLM call. Docker
daemon availability is not claimed. Initial sandboxed pytest temp-directory access
was denied, then the normal approved execution passed all97 preflight cases; the
denied attempt is not acceptance evidence. Git safe.directory is invocation-local.

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONUNBUFFERED='1'
$env:TEST_DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:15434/goutou_test'
$env:DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:15434/goutou_dev'
$env:PLAYWRIGHT_CHROME_PATH='C:\Program Files\Google\Chrome\Application\chrome.exe'
$env:PATH='C:\Windows\System32;'+$env:PATH
pnpm api:generate
pnpm api:check
pnpm --filter @goutou/mobile typecheck
pnpm --filter @goutou/mobile test:connected
pnpm --filter @goutou/mobile smoke:connected
pnpm --filter @goutou/mobile exec expo-doctor
pnpm --filter @goutou/mobile exec expo export --platform android --output-dir ../../.cache/phase8b-android-export
$env:PYTEST_ADDOPTS='--basetemp=.cache/phase8b-pytest-pre-marker -o cache_dir=.cache/phase8b-pytest-pre-marker-cache'
.\make.cmd verify  # exit0, 7/8A
# Advance marker to 7/8B only after all CODE/TEST/DOC/DEMO/REGRESSION gates.
$env:PYTEST_ADDOPTS='--basetemp=.cache/phase8b-pytest-final-fixed -o cache_dir=.cache/phase8b-pytest-final-fixed-cache'
.\make.cmd verify  # exit0, accepted marker 7/8B
git -c safe.directory=F:/狗头军师app化/goutouapp diff --check
```

Pre-marker and final accepted-marker actual output: repository24 OK; isolated Alembic migration/check PASS;
backend555 passed; resources97 passed; Golden83 passed; Ruff169 already formatted;
Mobile143 passed/focused48; generation3 passed; peers clean; Doctor21/21; Web export;
Demo22 passed; connected3 passed; all active0–7 and8A/8B PASS; Phase8 incomplete.
Ignored evidence: pre-marker/final verifier logs, connected JSON/results, existing
Demo browser results/screenshots and Android JS export. Connected traces/video/
screenshots remain disabled to prevent credential capture.
