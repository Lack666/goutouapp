# Mobile architecture — Phase 7A–7D and Phase 8B

Current 8B implementation adds generated resource HTTP and a Development Session.
The Phase7 sections below describe preserved Demo behavior. Connected uses
`ConnectionProvider → DevelopmentSession + ApiTransport + ResourceController →
generated DTO adapters → existing ViewModels/components`. Root selects Demo or
Connected ShellDataSource and remounts local scope state on mode/session epoch.
No new global state framework or screen redesign. Resource state contains no token.

New directories: `src/api/generated` (generator-owned), `src/api` (safe transport,
UUID validation, DTO adapters), `src/session` (lifecycle and platform storage),
async resource controller and Connected screens. The separate `tools/api-codegen`
workspace pins generator TS5 while Mobile keeps TS6. Native SecureStore57.0.4 and
Crypto57.0.3 match the SDK57 compatibility map; openapi-fetch0.17.0 uses injected
fetch. No Expo/React/RN upgrade or ignored peer conflict.

Connected handles Person/Relationship/Conversation create/list/detail only. Current
resource selections propagate UUIDs to unavailable Chat/Import/History screens;
no Agent, SSE, formal history, upload/binding or Memory network work exists.
Web is volatile; native secure credentials revalidate on restore. Epoch guards,
serialized storage and request aborts prevent owner leakage. Local CORS is explicit
and development/test-only. `api:check`, unit tests, Doctor and real connected browser
gate join root verification. Native connected runtime is NOT RUN on this host;
Android JS export is separate. See [API client](MOBILE_API_CLIENT.md),
[session](MOBILE_DEV_AUTH.md), [resource/platform steps](MOBILE_RESOURCE_INTEGRATION.md),
[ADR0032](adr/0032-generated-mobile-client-and-development-session.md) and
[8B acceptance](PHASE_8B_ACCEPTANCE.md).

The Expo React Native foundation, navigation shell and local Chat/Profile/Import/History/Settings UI are implemented.
Phase 7 remains the six-surface Mobile MVP; Phase 8 remains generated API client
and stream integration. No server/Agent behavior or frozen knowledge is changed.

## Toolchain and compatibility

Node **24.15.0**, project **pnpm 11.25.0**, Expo **57.0.27**, React Native
**0.86.3**, React/React DOM **19.2.3**, Expo Router **57.0.25**, React Native
Web **0.21.3**, TypeScript **6.0.3**. This follows the stable SDK 57
[official compatibility matrix](https://docs.expo.dev/versions/latest/).
Node exceeds SDK 57's minimum 22.13.x. The npm `latest`/`sdk-57` tags were
both 57.0.27 when audited on 2026-10-08; prereleases were not selected.

Versions were selected through the official
[Expo Router installation](https://docs.expo.dev/router/installation/)
`expo install --pnpm` flow, then pinned exactly in Mobile package.json and
locked in the existing root pnpm-lock.yaml. The original lockfile contained
only an empty root importer. No npm/yarn lockfile or broad dependency upgrade.

The global pnpm shim reports 11.7.0 outside the repository; within this workspace
it downloads/delegates to the existing `packageManager: pnpm@11.25.0` pin.
Corepack 0.34.6 is available but the installed pnpm shim handles delegation.
No global package-manager configuration is changed. `scripts/check_mobile.py`
requires the project invocation to return exactly 11.25.0.

The workspace uses an explicit relative `.pnpm-store`, isolated installation,
exact saves and strict peer checks. No custom Metro resolution is needed, per
[Expo monorepo guidance](https://docs.expo.dev/guides/monorepos/).
An explicit `pnpm peers check` gate rejects reported conflicts even if the CLI
returns zero. Reanimated 4.5.1/Worklets 0.10.1 match Expo; Metro config 0.86.3
satisfies the React Native CLI peer. They support Router's package dependencies,
not new application animation features.

Jest **29.7.0** matches jest-expo **57.0.5**'s Jest 29 dependencies. React Native
Testing Library **14.1.0** matches the
[Router test guide](https://docs.expo.dev/router/reference/testing/).
Its peer `test-renderer` is explicitly **1.2.0** (React reconciler 0.33) for
React 19.2; 1.3.0 would select reconciler 0.34 requiring React 19.3.
Tests keep Router's returned navigation handle before awaiting async render;
there is no Router replacement mock and no suppressed type error.

pnpm's `unrs-resolver` postinstall was reviewed: it prepares the platform N-API
binding through `napi-postinstall`. Only that build is allowed. The four explicit
release-age exclusions generated during installation name exact stable
Playwright/RNTL packages; strict release-age policy prevents silent future changes.
Upstream ESLint 9/Jest dependencies have deprecation notices; no peer conflict is
ignored. ESLint 9 is retained with Expo's recommended config in this foundation.

## Directory boundaries

- `app/`: Expo Router's root layout, six route modules and not-found route only.
- `src/features/`: Home, Chat, Relationship, Import wizard, History and Settings.
- `src/components/`: ScreenContainer, AppHeader, PrimaryButton, SectionCard,
  EmptyState, LoadingState, ErrorState, DemoNotice and StatePreview.
- `src/theme/`: shared palette, type, spacing, radius, layout and theme provider.
- `src/navigation/`: narrow typed route registry and entry labels.
- `src/contracts/`: UI ViewModel, state union and read-only DataSource contract.
- `src/data/`: injected provider and deterministic local source.
- `src/hooks/`: local scenario state and retry reset.
- `assets/`: provenance policy; no third-party assets or fonts.
- `tests/`: Router/component/provider/contract tests, outside the route tree.
- `smoke/`: real browser test; Playwright starts and stops Expo Web separately.

Screen files do not import demo fixtures. `_layout.tsx` is the composition root
that selects the source. No business logic or server calls live in route modules.
TypeScript extends Expo's base with `strict` and `noUncheckedIndexedAccess`.
Routes use a closed path union compatible with Router's `push`; generated typed
routes are not needed for these static routes and are not enabled as an experiment.

## Navigation and six surfaces

One Stack starts at Home `/`. Home has a prominent Chat `/chat` action, then
Relationship/Profile `/relationship`, Import/Analysis `/import`, History
`/history`, Settings `/settings` cards. Five leaf pages have a shared accessible
back button. It pops when history exists and replaces with `/` on a direct link.
Unknown routes offer a working Home return. Android's stack retains native back
handling; actual Android behavior is not counted as tested by Web or Jest.

No six-item bottom bar is introduced: it would crowd small screens. Home serves
as the compact launch surface. There are no automatic redirects or circular routes.

Home displays welcome and entry actions. Chat supports a virtualized message
list and local multiline preview; real server sending remains disabled.
Relationship has scoped synthetic Person/profile cards, missing-data handling
and A/B selection; real editing remains disabled. Import is a five-step explicit
source/identity/relationship/readiness/result Demo, with disabled file/finalize
actions and synthetic FIU teaching preview. History has separate AI/external
views, scoped synthetic data and virtualized 30-row incremental windows. Settings
has local consent/pause/inspect/undo/delete-confirmation/retention previews,
app information and theme. Generated API integration remains Phase 8.

## Data and interaction boundary

`ShellDataSource.readSurface(id, scenario)` supplies a `SurfaceState` discriminated
union of loading, empty-with-ViewModel or safe error. It is deliberately synchronous
and read-only for this local shell. Phase 7B extends it with `readChat` and
`readRelationships`, returning typed, freshly allocated feature templates.
Phase 7C adds readImport/readHistory/readSettings, also read-only templates;
feature controllers own only ephemeral presentation state. Import readiness is
local, History domains are discriminated, and Memory actions reflect existing
Phase 6 semantics without creating wire statuses/challenges/receipts.
Chat begins empty; an explicit action loads predefined assistant/user examples.
Local input adds only a user bubble. Synthetic profiles/FIU are clearly labeled;
there are no real analyses, saved memories, successful uploads or authenticated
sessions. Every page states
**本地演示 · Demo** and that the server is unconnected.

Import/History/Settings retain local loading/empty/error presentation controls.
Relationship retains the same
local loading/error controls alongside its complete Demo profile. Chat has a
separate seven-state presentation union: idle/unavailable/starting/progressing/
completed/failed/pending_confirmation. Manual previews never claim a live run.
Chat Retry resets its display state; profile/shell Retry restores local content.
Enabled controls also type/clear/preview input, load examples or select a profile.
No action persists, logs or sends input; real business controls remain disabled.
Draft/list state clears on Chat unmount/reload or a changed relationship scope.
Profile selection survives Stack push/back while mounted and resets on reload.
See [Chat UI](MOBILE_CHAT_UI.md) and [Relationship UI](MOBILE_RELATIONSHIP_UI.md).

All scoped navigation uses explicit relationshipId. Unknown/ambiguous IDs fail
closed on Chat/Relationship/Import/History. Import changes clear bindings and
confirmation; route-scope changes remount scoped controllers. History scope changes
clear loaded state/filter/window; Memory controls are owner-level demo state, not
relationship chat. Unmount/reload/restart clears feature previews. Stack push/back
retains still-mounted state; theme lives separately at root. There is no global
state library or durable storage. See [Import UI](MOBILE_IMPORT_UI.md),
[History UI](MOBILE_HISTORY_UI.md), [Settings UI](MOBILE_SETTINGS_UI.md).

Phase 8 can introduce async resource hooks and adapters translating existing
server DTOs into these UI ViewModels. It will replace the source at composition,
extend states for loaded records and preserve shared rendering/components.
This is not an ApiClient or a copied backend schema. JWT storage, generated
OpenAPI types, operation_key/run_id handling, REST and POST SSE consumption,
real imports and memory mutations remain deferred. Current backend supports signed
JWT verification and development tokens, not complete production registration.
The actual Phase 4 stream is progress SSE with a committed final response,
not model token streaming or WebSocket. Structured FIU/profile data is not
currently supplied by the public answer DTO; Phase 8 must coordinate its mapping.
Public Profile/Person resource reads and a general Agent-history-list adapter
also need contract coordination; internal AgentService history is not a mobile API.
See AGENT_API/STREAMING_API,
IMPORT_API and MEMORY_API for the future adapter's authority.

## Theme, layout and accessibility

Use system/light/dark; system is default with light fallback. Settings changes
the real palette and status bar across routes. Preference is held in the root
provider for this app session and resets on restart. No durable storage or token
store is implied. Color, typography, spacing, radius and 48-unit minimum touch
targets are central tokens; system fonts avoid external licenses and downloads.

SafeAreaProvider/SafeAreaView wrap each screen. Profile/shell ScrollViews,
bounded max width and wrapping controls handle small screens. Chat uses one
FlatList outside a fixed composer, with KeyboardAvoidingView around both.
Multiline input is enabled only for local preview. No fixed screen dimensions or dynamic font-size
suppression. Headers, buttons and input have readable labels and roles; selected
and disabled controls expose accessibilityState, error text uses alert semantics.
Web toggles explicitly expose aria-pressed and selected borders; native selected
state is retained. Text bubbles identify sender/source/time.
No device keyboard, TalkBack or complete accessibility certification is claimed.

## Run and verify

From the repository root:

```powershell
node --version
pnpm --version  # must be 11.25.0 inside this project
pnpm install --frozen-lockfile
pnpm --filter @goutou/mobile start
pnpm --filter @goutou/mobile web
pnpm --filter @goutou/mobile android
pnpm --filter @goutou/mobile exec expo-doctor
pnpm mobile:verify
.\make.cmd verify
```

Android requires Android Studio/emulator with adb or a physical device and
an SDK 57-compatible Expo Go/development build. The user reported a successful
manual emulator check after 7C; 7D Codex launch attempts did not complete native
UI smoke. These evidence categories remain separate from Web and automation.
Web works without Android SDK or backend. `pnpm mobile:verify` uses frozen
offline installation, so run the first online install on a new checkout.
Root verify retains all backend PostgreSQL gates and adds Mobile static gates
when the actual package exists, including before the phase marker changes.
Phase 7D additionally runs real Web export and all browser regression paths.
It never treats those as native Android evidence; Android remains a separate check.

For reproducible real Expo Web smoke:

```powershell
pnpm --filter @goutou/mobile exec playwright install chromium
pnpm --filter @goutou/mobile smoke:web
```

Alternatively use an installed Chrome:

```powershell
$env:PLAYWRIGHT_CHROME_PATH='C:\Program Files\Google\Chrome\Application\chrome.exe'
# This host's PATH lacks System32; restore it for Playwright's taskkill cleanup.
$env:PATH = 'C:\Windows\System32;' + $env:PATH
pnpm --filter @goutou/mobile smoke:web
```

Smoke runs Expo/Metro on `http://localhost:8087` (Windows resolves it to `::1`;
do not substitute 127.0.0.1 when using `--localhost`). Chrome is headless.
It tests five Home transitions/back, all direct links, unknown-route recovery,
three theme modes, state previews/retry, enabled local composer, 320/360/412 widths,
48px back target and no external application requests/page errors.
Thirteen scenarios include the retained 7A flow, six 7B light/dark/width flows
with preview typing, append/scroll, FIU, disabled confirmation, A/B profile,
scoped Chat and return navigation, plus six 7C wizard/B-only History/Memory-control
and confirmation flows at those widths/themes. Ignored current evidence goes to
`.cache/phase7c-web-smoke.json`, Web results and PNGs.
Web export is an additional build check, not a replacement for this live smoke.

## Environment and security boundaries

Network downloads and local sockets require the desktop sandbox's normal
approved execution path on this host. The exact pnpm is bootstrapped through
its standard package-manager mechanism. Docker daemon is unavailable; backend
regression uses the existing local PostgreSQL 16.15 cluster on port 15434 and
disposable databases. No unavailable environment check is counted as passed.

Mobile contains no model/DB key, provider/Agent prompt, knowledge snapshot,
JWT signing secret, direct LLM call, PostgreSQL connection, owner authorization,
auth success or memory mutation. Application source is scanned for known secret,
provider, database and network-call patterns in the static gate; runtime smoke
also records network requests. This baseline audit is not a general security
certification. All real authentication/ownership/model operations stay server-side.

See [ADR 0029](adr/0029-mobile-shell-and-data-boundary.md),
[ADR 0030](adr/0030-mobile-chat-preview-and-relationship-scope.md),
[Phase 7A acceptance](PHASE_7A_ACCEPTANCE.md) and
[Phase 7B acceptance](PHASE_7B_ACCEPTANCE.md), [Phase 7C acceptance](PHASE_7C_ACCEPTANCE.md).

## Phase 7D integration and acceptance boundary

All six interactive Demo surfaces are tested as one real browser journey.
Next is gated at speaker selection and explicit relationship confirmation;
compatibility still gates the final precheck. Changed scope clears draft state.
Chat waits for last-row layout before consuming its pending scroll revision,
so first multi-line previews remain above composer. Home loading/error is visible.
Architecture, dependencies and server contracts are retained.

The verifier adds focused integration/recovery tests and live Expo Web regression,
and supports the completed 7/7D marker while rejecting Phase 8+ completion.
`demo:final` reproduces the complete MVP journey/recovery suite. See
[final acceptance](PHASE_7_FINAL_ACCEPTANCE.md) for current gates and native limits,
and [API handoff](PHASE_8_MOBILE_INTEGRATION_HANDOFF.md) for confirmed endpoints
and explicit public-resource/analysis gaps. No Phase 8 behavior is implemented.
