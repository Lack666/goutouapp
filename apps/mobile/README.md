# Mobile app — Phase 7A–7C

Expo SDK 57.0.27 / React Native 0.86.3 / React 19.2.3 / Expo Router 57.0.25 /
TypeScript 6.0.3. Use Node 22.13+ (validated 24.15.0) and the root project pin
pnpm 11.25.0. This is a real React Native shell with six reachable surfaces,
session-local system/light/dark preference, interactive local Chat/Profile/Import/History/Settings and
explicit Demo state previews. Dependencies and SDK remain the 7A pins.

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

Static scripts: `typecheck`, `lint`, `format:check`, `test`, `test:features`, `test:controls`, `compatibility`.
`format` writes formatting; `start` runs Expo. Root `make verify` adds these
static gates alongside Phase 0–6 regression. It does not launch a device.

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

Every surface is marked **本地演示 · Demo**. No authenticated account, successful
upload, Agent conclusion or saved memory is fabricated. Chat supports typing,
Clear and **添加到本地预览**, appending one local user bubble and reporting
**仅在本地预览，尚未发送给 AI**. No assistant is generated; only the explicit
**替换为合成对话示例** action replaces the list with predefined examples.
Input is capped at 2,000 UTF-16 units. Draft/list clear on unmount, reload or changed
relationship scope. Real Chat sending, profile editing and file selection remain
disabled. Profile A/B selection and missing-value cards work locally; selection
survives push/back while mounted and resets on reload. State previews/Retry and
theme/navigation are functional local controls. The preference persists only across this session's
routes, not app restarts. No LLM/DB/backend call, provider secret or knowledge is
included. Phase 8 will replace the data source at the composition boundary.

Import provides a five-step synthetic wizard with explicit speaker/Person and
relationship confirmation, compatibility/group checks, reset and navigation.
Real file upload/finalize/Agent analysis stay disabled. History separates AI
user/assistant from external self/person/system messages, filters exact relationship
scope and uses one FlatList with 30-row local windows/More. Unknown IDs never fall
back to A/B. Settings previews consent/pause/inspect/undo/delete confirmation and
server-configurable retention; formal guarded operations stay disabled and no
sample is deleted. Previews clear on unmount/restart; scope changes clear relevant
bindings/history windows. Every data source contains anonymous synthetic fixtures.

**EXPO WEB SMOKE: PASS** is the accepted runtime platform. **ANDROID: NOT RUN**;
Android requires an SDK 57-compatible Expo Go/development build plus device/emulator.
Device keyboard and TalkBack checks remain unverified. Phase 7D overall MVP
acceptance, auth, OpenAPI client, REST/SSE consumption, real upload/import/history
persistence and Memory mutation are deferred.

See [Mobile architecture](../../docs/MOBILE_ARCHITECTURE.md),
[ADR 0029](../../docs/adr/0029-mobile-shell-and-data-boundary.md), and
[Phase 7A acceptance](../../docs/PHASE_7A_ACCEPTANCE.md),
[Chat UI](../../docs/MOBILE_CHAT_UI.md),
[Relationship UI](../../docs/MOBILE_RELATIONSHIP_UI.md),
[ADR 0030](../../docs/adr/0030-mobile-chat-preview-and-relationship-scope.md) and
[Phase 7B acceptance](../../docs/PHASE_7B_ACCEPTANCE.md),
[Import UI](../../docs/MOBILE_IMPORT_UI.md), [History UI](../../docs/MOBILE_HISTORY_UI.md),
[Settings UI](../../docs/MOBILE_SETTINGS_UI.md) and [7C acceptance](../../docs/PHASE_7C_ACCEPTANCE.md).
