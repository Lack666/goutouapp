# Owned resource integration — Phase 8B/8C

Phase8C uses these actual Conversation IDs for Connected Chat, validates owned
detail and any relationship assertion, and enables Agent REST/POST SSE plus public
Agent History. Generic Conversations have a direct Chat action. Relationship scope
cannot borrow another Conversation. Import/RelationshipMessage History and Memory
controls remain unavailable. See [Chat](MOBILE_AGENT_CHAT.md),
[streaming/native steps](MOBILE_STREAMING.md) and [8C acceptance](PHASE_8C_ACCEPTANCE.md).
The following8B notes remain historical resource-acquisition evidence.

Demo keeps all Phase 7 UI/controller behavior and makes no business requests.
Connected Development Mode reads only server-confirmed Person/Relationship/
Conversation resources through the generated client, transport, resource
controller and DTO-to-ViewModel adapters. `ShellDataSource` remains the composition
seam: Demo selects existing templates, Connected selects an unavailable source
for deferred business features and async resource controllers. Screens keep the
existing Router, theme and components and do not import wire DTOs or fixtures.

The Relationship page supplies three resource list/detail/create sections. Choose
an owned Person explicitly and fill type/status to create a Relationship; unknown
may be typed as `unknown`, with no inferred romantic relationship. Person nickname
never becomes its ID. Detail fetch also reads its owned Person independently.
Conversation creation explicitly selects a generic null association or an owned
Relationship; detail and selection retain the actual UUID for later 8C use.
Absent nickname/profile/interaction/history/analysis remain absent.

Each list fetches 30 rows, treats next_cursor as opaque, guards overlapping More,
deduplicates visible UUIDs in server order and exposes loading, empty, retry and
load-more states. Cursors are held separately per resource domain and cleared on
reset/logout/session switch. Detail selection aborts the previous selection and
accepts only the current controller/request/epoch. Server scopes authorize every
request; Mobile passes no owner override.

One explicit creation reserves a cryptographically random UUID v4 via Expo Crypto
**57.0.3**, matching SDK 57. Retry resends the private retained body unchanged,
even if form fields were edited after an uncertain result. A separate explicit
new-creation action reserves a new UUID. Duplicate active create/retry calls are
guarded. Server confirmation alone produces “服务器已确认保存”; failure never
inserts a local resource or substitutes Demo. Post-save refresh/detail failures
are shown independently and do not claim a failed read succeeded.

Pending create attempts are session-memory only, cleared on logout, switch or app
process restart. Retry safety therefore covers retained attempts in this process;
after a restart and uncertain submission, inspect the server before starting a new
logical creation. No durable client outbox or permanent server receipt is claimed.
The 8A UUID reservation lasts only while the resource row exists; internal/future
deletion removes that reservation. No resource deletion API is implemented in 8B.

Selecting a real Relationship opens Chat/Import/History with the real UUID. A
selected Conversation is passed only when its actual association matches that
Relationship. Those screens verify resource context but continue to show business
operations as unavailable. They read no messages, upload nothing and execute no
Agent or Memory operation. Unknown/synthetic/deep-link IDs fail closed, without
silently choosing another relationship. URL parameters never authorize resources.

## Reproduce real connected HTTP and Web

With a separate PostgreSQL `_test` namespace and Chromium or installed Chrome:

```powershell
$env:PYTHONUTF8='1'
$env:TEST_DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:15434/goutou_test'
$env:PLAYWRIGHT_CHROME_PATH='C:\Program Files\Google\Chrome\Application\chrome.exe'
$env:PATH='C:\Windows\System32;'+$env:PATH
pnpm --filter @goutou/mobile smoke:connected
.\make.cmd verify
```

Three actual tests share a disposable server: generated client create/list/detail,
lost-response recovery for all domains and six concurrent creates; real Expo Web
manual token entry, Person/Relationship/Conversation creation and cross-page
UUIDs, logout/A→B and reload; expired/malformed credentials, offline retry and
injected server 401. PostgreSQL counts verify single-row response-loss recovery.
Only loss/401/offline are deliberately fault-injected; successful requests use
actual sockets, signed CLI JWTs and the unchanged owner-scoped resource service.
No mock fetch replaces success or JWT verification. Ports 8018/8088 must be free.

## Android real HTTP smoke

Use SDK 57-compatible Expo Go on an Android Studio AVD or device. In separate
terminals start the actual development backend and obtain the CLI credential
above. Choose one explicit local path, then start Metro with a public address:

```powershell
# adb reverse: both Metro and backend reach the development host through loopback.
adb reverse tcp:8000 tcp:8000
adb reverse tcp:8081 tcp:8081
$env:EXPO_PUBLIC_API_BASE_URL='http://127.0.0.1:8000'
pnpm --filter @goutou/mobile exec expo start --android --localhost --clear
```

Alternatively configure the emulator host gateway `http://10.0.2.2:8000` for an
AVD, or a trusted explicit LAN server origin. These addresses are configuration,
never a hardcoded developer IP. LAN use requires an intentional local server bind
and firewall rule, not a public deployment. Cleartext HTTP is restricted to this
controlled development session; deployment transport requires HTTPS. No global
production TLS or cleartext policy was disabled.

On-device steps: Settings → manually validate the developer credential → Resource
page → create/read Person → explicitly create Relationship → create/select bound
and generic Conversation → background/resume before and after expiry → logout →
restart and confirm removal → connect User B and confirm no A resource or cursor.
Do not capture a screen/clipboard/adb dump during token entry. Verify actual
PostgreSQL rows independently, and keep all private credentials off logs.

This host's Pixel_10 AVD launched twice and logged boot completion, but exited
and never established a stable adb device; localhost:5555 refused connection.
Android connected network/storage/background/logout execution is **NOT RUN**.
Android JS export and 21/21 Expo Doctor checks passed independently. The prior
user-reported Phase 7 Demo check is not Phase 8B connected evidence. Final Phase 8
acceptance still requires actual Android connected proof.
