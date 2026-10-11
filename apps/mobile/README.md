# Mobile app — Phase 7A–7D and Phase 8B–8F acceptance

8F adds `test:final` for cross-controller owner/mode/background/restart boundaries
and `smoke:final` for all six actual Connected surfaces in one signed
FastAPI/PostgreSQL/LangGraph/MockLLM journey. Existing tests are retained.
Final acceptance requires separate Android evidence and remains incomplete.
See [final acceptance](../../docs/PHASE_8_FINAL_ACCEPTANCE.md) and
[native demo](../../docs/PHASE_8_FINAL_ANDROID_DEMO.md). No production accounts,
outbox, imported-chat analysis, provider quality or release APK is implied.

Phase8E connects Settings to the existing Memory APIs using shared development
JWT/generated transport. It includes server controls/retention/known-ID expiry,
guarded Undo, one/Person/all confirmation and durable receipts. `test:memory`
runs48 focused controller/UI cases; `smoke:memory` runs real signed HTTP,
PostgreSQL/LangGraph and Chrome Expo UI. No model keys or local Memory database.
Recovery is session-only; restart cannot automatically retry a lost key. See
[Memory/native instructions](../../docs/MOBILE_MEMORY_INTEGRATION.md) and
[8E report](../../docs/PHASE_8E_ACCEPTANCE.md). Whole8 stays incomplete;8F acceptance is underway.

Phase8D uses the SDK57 DocumentPicker and binary File adapters for existing
multipart Import APIs, explicit UUID/revision bindings, server readiness/finalize
and separate bounded Relationship/Agent history. `test:imports` runs focused
controller/platform/UI tests; `smoke:imports` runs signed HTTP/PostgreSQL and
Chrome file-picker E2E. See [8D acceptance](../../docs/PHASE_8D_ACCEPTANCE.md),
[import/native instructions](../../docs/MOBILE_IMPORT_UI.md) and
[history](../../docs/MOBILE_HISTORY_UI.md). Memory HTTP was deferred at8D acceptance.

Phase8C Connected Chat sends actual Agent REST/POST SSE through the same8B JWT
session, selects owned generic/bound Conversations and recovers public Agent History.
It shows server-confirmed answers, actual run/key IDs, safe same-key retry and explicit
unknown outcomes. At8C acceptance, Import/RelationshipMessage history and Memory
mutations were deferred; the current8D/8E sections above supersede that boundary.
See [Chat](../../docs/MOBILE_AGENT_CHAT.md), [streaming/native steps](../../docs/MOBILE_STREAMING.md)
and [8C acceptance](../../docs/PHASE_8C_ACCEPTANCE.md). `test:sse`, `test:agent-chat`
and `demo:agent` run focused parser/controller/UI and real CLI JWT/PostgreSQL/
FastAPI/MockLLM/Chrome flows. On 2026-10-10 actual Android core SSE/Chinese/replay/
History/logout/owner-isolation smoke also ran; active native faults/background/
expiry and complete keyboard QA remain unverified. See the 8C revalidation report.
For native verification use loopback Metro and adb reverse. If Metro listens only
on `::1`, a loopback-only IPv4 relay resolves the host-family mismatch; details
are in the final native demo. No LAN listener is needed.
The following8B/Phase7 notes retain their historical boundaries; Agent Chat is now
implemented as described above. The original Demo remains available unchanged.

Demo retains Phase7 behavior. Connected Development Mode adds real generated
Person/Relationship/Conversation create/list/detail and a manually entered short-lived
CLI JWT; Agent/SSE/import/history/Memory business operations are still unavailable.
See [API client](../../docs/MOBILE_API_CLIENT.md), [development session](../../docs/MOBILE_DEV_AUTH.md)
and [resources/Android smoke](../../docs/MOBILE_RESOURCE_INTEGRATION.md).

`pnpm api:generate` / `pnpm api:check` run from root. `test:connected` covers auth,
transport/adapters/UUID retries; `smoke:connected` uses real CLI JWT/FastAPI/PostgreSQL/
Chrome on ports8018/8088 with a disposable database. Root verify includes both Demo
and Connected gates. Configure only the public `EXPO_PUBLIC_API_BASE_URL` in Mobile;
the `.env.example` has no credentials. Native uses SecureStore57.0.4; Web credentials
are volatile. Logout/expiry/401 and mode/session changes cancel requests and clear
all resource/form scopes. Android connected runtime/storage is NOT RUN on this host;
JS export/Doctor are separate checks. Final Phase8 must provide actual native evidence.

Expo SDK 57.0.27 / React Native 0.86.3 / React 19.2.3 / Expo Router 57.0.25 /
TypeScript 6.0.3. Use Node 22.13+ (validated 24.15.0) and the root project pin
pnpm 11.25.0. This is a real React Native shell with six reachable surfaces,
session-local system/light/dark preference, interactive local Chat/Profile/Import/History/Settings and
explicit Demo state previews. The existing Expo/RN/React/TypeScript pins are retained;
Phase8B adds SDK-compatible SecureStore/Crypto and the generated API client dependency.

From the repository root:

```powershell
pnpm install --frozen-lockfile
pnpm --filter @goutou/mobile start
pnpm --filter @goutou/mobile web
pnpm --filter @goutou/mobile android
pnpm mobile:verify
pnpm --filter @goutou/mobile exec expo-doctor
pnpm --filter @goutou/mobile export:web
```

Static scripts: `typecheck`, `lint`, `format:check`, `test`, `test:features`, `test:controls`, `test:integration`, `compatibility`.
`format` writes formatting; `start` runs Expo. Root `make verify` adds these
static gates alongside Phase 0–6 regression, followed by real Web export and all
browser regression scenarios. It does not launch a device or claim native results.

Live smoke starts Expo Web on localhost:8087 and uses headless Chromium:

```powershell
pnpm --filter @goutou/mobile exec playwright install chromium
pnpm --filter @goutou/mobile smoke:web
```

On the acceptance host use installed Chrome instead of downloading Chromium:

```powershell
$env:PLAYWRIGHT_CHROME_PATH='C:\Program Files\Google\Chrome\Application\chrome.exe'
$env:PATH = 'C:\Windows\System32;' + $env:PATH
pnpm --filter @goutou/mobile smoke:web
```

Navigation: Home → Chat, Relationship/Profile, Import/Analysis, History, Settings;
each leaf returns to the prior page or Home on a direct link. No crowded six-item
tab bar. `app/` contains routes only; `src/` contains UI, contracts, injected local
source, hooks and theme. Tests are outside `app/`.

In Demo mode every surface is marked **本地演示 · Demo**. No authenticated account, successful
upload, Agent conclusion or saved memory is fabricated. Chat supports typing,
Clear and **添加到本地预览**, appending one local user bubble and reporting
**仅在本地预览，尚未发送给 AI**. No assistant is generated; only the explicit
**替换为合成对话示例** action replaces the list with predefined examples.
Input is capped at 2,000 UTF-16 units. Draft/list clear on unmount, reload or changed
relationship scope. Real Chat sending, profile editing and file selection remain
disabled. Profile A/B selection and missing-value cards work locally; selection
survives push/back while mounted and resets on reload. State previews/Retry and
theme/navigation are functional local controls. The preference persists only across this session's
routes, not app restarts. Demo makes no LLM/DB/backend call. Provider secrets and
knowledge remain server-only. Connected selects its source at the composition boundary.

Import provides a five-step synthetic wizard with explicit speaker/Person and
relationship confirmation, compatibility/group checks, reset and navigation.
Real file upload/finalize/Agent analysis stay disabled. History separates AI
user/assistant from external self/person/system messages, filters exact relationship
scope and uses one FlatList with 30-row local windows/More. Unknown IDs never fall
back to A/B. Settings previews consent/pause/inspect/undo/delete confirmation and
server-configurable retention; formal guarded operations stay disabled and no
sample is deleted. Previews clear on unmount/restart; scope changes clear relevant
bindings/history windows. The Demo data source contains anonymous synthetic fixtures;
Connected resource data comes only from confirmed server responses.

**EXPO WEB SMOKE: PASS**, 22 scenarios including nine new 7D integration/recovery
cases. The user reported manual Android emulator smoke passed after 7C.
**CODEX ANDROID SMOKE: NOT RUN / launch attempt incomplete**: the configured AVD
briefly connected then disconnected or stopped responding to shell/UI commands.
Native keyboard/Back/TalkBack automation and APK/development-build construction
remain **NOT RUN / NOT BUILT**, independently of the user's manual feedback.
Android requires SDK-compatible Expo Go/development build plus device/emulator.

Reproduce the final six-surface Demo with the same Chrome/PATH setup above:

```powershell
pnpm --filter @goutou/mobile demo:final
```

This runs actual Home → Relationship B → five-step Import (explicit speaker and
relationship gates) → B History/More → Chat multi-line user-only preview →
Settings Memory/Undo/delete-confirmation/reset/reload → Home, in both palettes
at 320/360/412px. Screenshot/JSON evidence is written under root `.cache`.
For interactive use, start `web` and follow those controls; no backend/key needed.
Phase8B development auth, generated client and owned resources are implemented.
Agent REST/SSE, real upload/import/history persistence and Memory mutations remain
deferred. Read the [8B acceptance](../../docs/PHASE_8B_ACCEPTANCE.md) for current status;
the Phase7 reports below document the retained Demo behavior.

See [Mobile architecture](../../docs/MOBILE_ARCHITECTURE.md),
[ADR 0029](../../docs/adr/0029-mobile-shell-and-data-boundary.md), and
[Phase 7A acceptance](../../docs/PHASE_7A_ACCEPTANCE.md),
[Chat UI](../../docs/MOBILE_CHAT_UI.md),
[Relationship UI](../../docs/MOBILE_RELATIONSHIP_UI.md),
[ADR 0030](../../docs/adr/0030-mobile-chat-preview-and-relationship-scope.md) and
[Phase 7B acceptance](../../docs/PHASE_7B_ACCEPTANCE.md),
[Import UI](../../docs/MOBILE_IMPORT_UI.md), [History UI](../../docs/MOBILE_HISTORY_UI.md),
[Settings UI](../../docs/MOBILE_SETTINGS_UI.md) and [7C acceptance](../../docs/PHASE_7C_ACCEPTANCE.md).

See [Phase 7 final acceptance](../../docs/PHASE_7_FINAL_ACCEPTANCE.md) and
[Phase 8 API handoff](../../docs/PHASE_8_MOBILE_INTEGRATION_HANDOFF.md).
