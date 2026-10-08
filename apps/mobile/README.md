# Mobile app — Phase 7A

Expo SDK 57.0.27 / React Native 0.86.3 / React 19.2.3 / Expo Router 57.0.25 /
TypeScript 6.0.3. Use Node 22.13+ (validated 24.15.0) and the root project pin
pnpm 11.25.0. This is a real React Native shell with six reachable surfaces,
session-local system/light/dark preference and local state previews.

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

Static scripts: `typecheck`, `lint`, `format:check`, `test`, `compatibility`.
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
upload, Agent conclusion or saved memory is fabricated. Chat sending, profile
editing and file selection are disabled. State previews/Retry and theme/navigation
are functional local controls. The preference persists only across this session's
routes, not app restarts. No LLM/DB/backend call, provider secret or knowledge is
included. Phase 8 will replace the data source at the composition boundary.

**EXPO WEB SMOKE: PASS** is the accepted runtime platform. **ANDROID: NOT RUN**;
Android requires an SDK 57-compatible Expo Go/development build plus device/emulator.
Device keyboard and TalkBack checks remain unverified. Full feature UI, auth,
OpenAPI client, REST/SSE consumption, import and memory binding are deferred.

See [Mobile architecture](../../docs/MOBILE_ARCHITECTURE.md),
[ADR 0029](../../docs/adr/0029-mobile-shell-and-data-boundary.md), and
[Phase 7A acceptance](../../docs/PHASE_7A_ACCEPTANCE.md).
