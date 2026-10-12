# Phase 8 Final Android Connected Demo

Status: **PARTIAL / BLOCKED**, not ANDROID END-TO-END PASS. All observations
here were Codex-executed on the actual Android App. User-manual execution:
NOT RUN. Web-only results are recorded separately in the final acceptance.

## Environment and local startup

Pixel_10 existing AVD, Android 17/API 37, Expo Go 57.0.9; device emulator-5560.
Existing local PostgreSQL 16.15 on 127.0.0.1:15434, disposable fixture databases.
No real contacts/chats, production API, external LLM or credential file required.

Original device emulator-5554 was offline. Cold boot recovered the same AVD
without deleting data, using `-avd Pixel_10 -no-snapshot -no-window -gpu
swiftshader -port 5560`. Use hidden Start-Process for helper processes. Verify
`adb devices -l` and `adb -s emulator-5560 shell getprop sys.boot_completed`.

Metro launch from repository root (Windows PowerShell):

```powershell
$env:PATH = 'C:\Windows\System32;' + $env:PATH
$env:EXPO_PUBLIC_API_BASE_URL = 'http://127.0.0.1:8022'
$env:EXPO_NO_TELEMETRY = '1'
$env:CI = '1'
pnpm --filter @goutou/mobile exec expo start --localhost --port 8092 --clear
```

On this machine Metro binds IPv6 ::1. A temporary Node `net` relay listens only
on 127.0.0.1:8093 and pipes connections to ::1:8092. It contains no product
logic, credential or proxy to a public endpoint. ADB reverse:

Create the temporary relay in another local terminal, then leave it running:

```powershell
@'
const net = require('node:net');
net.createServer(client => {
  const upstream = net.connect({host: '::1', port: 8092});
  client.pipe(upstream); upstream.pipe(client);
  client.on('error', () => upstream.destroy());
  upstream.on('error', () => client.destroy());
  client.on('close', () => upstream.destroy());
}).listen(8093, '127.0.0.1');
'@ | Set-Content .cache/phase8f-loopback-relay.cjs
node .cache/phase8f-loopback-relay.cjs
```

Configure the device's reverse mappings:

```powershell
$taskAdb = 'C:\Users\VOS-User\AppData\Local\Android\Sdk\platform-tools\adb.exe'
& $taskAdb -s emulator-5560 reverse tcp:8022 tcp:8022
& $taskAdb -s emulator-5560 reverse tcp:8092 tcp:8093
& $taskAdb -s emulator-5560 shell am start -a android.intent.action.VIEW -d exp://127.0.0.1:8092 -p host.exp.exponent
```

Do not expose the unauthenticated development source on LAN. Automatic approval
review rejected a LAN Metro start; the loopback alternative was used.

## Disposable fixture and private credentials

```powershell
$env:PYTHONUTF8 = '1'
$env:TEST_DATABASE_URL = 'postgresql+psycopg://postgres@127.0.0.1:15434/goutou_test'
uv --cache-dir .cache/uv --no-managed-python run --locked python scripts/phase8_android_demo.py --adb $taskAdb --serial emulator-5560 --report .cache/phase8f-native-evidence.json
```

The helper starts the real fixture using existing CLI-issued short-lived signed
JWTs. Credentials stay in anonymous pipes and hidden native input; never print
the fixture's initial protocol line or record password nodes. `login a/b` renews
through the real CLI, not a bypass. Do not run root Web gates concurrently:
their Memory fixture also needs port 8022.

Interactive commands: `seed` prepares owned anonymous resources through host
REST; `login a`, `state`, `tap ["exact accessibility label","up or down"]`,
`input ["input label","Synthetic ASCII text"]`, `save 一` through `save 五`,
`memory_id`, `evidence`, `stage`, `confirm_file`, `back`, `home`, `cleanup`, `stop`.
`open settings/import/history/chat/relationship` uses existing native routes;
`restart` force-stops Expo Go, reopens the same base manifest and then Settings.
`save` uses real **host Agent REST** for deterministic eligible Memory setup;
it is not native Agent input evidence. `--steps` accepts a JSON array of these
commands, never tokens. Every UI success requires server evidence corroboration.

## Executed observations

- Real hidden-input JWT verification, server-owned resources loaded and selected.
  Resources were host-prepared; no native create/update PASS inferred.
- Native keyboard sent a synthetic Chat message over default POST SSE. Actual
  Chinese reply and completion rendered. Server: one completed run, two formal
  messages, no Memory. Native current-run streaming reader/event probe failed
  at Runtime.evaluate; incremental chunks/failure matrix remain unproven.
- Credential naturally expired; UI reported expiry and cleared current scope.
  Native REST replay attempt did not finish before expiry.
- Native Memory grant/resume/pause/revoke/re-grant, inspect, guarded latest Undo,
  delete-one, structured Person delete and delete-all preserve choice executed.
  Formal receipts and database counts demonstrate actual deletions while Agent
  history survives. Host REST created each deterministic Memory, separately.
- Native same-key all-delete replay left a newly saved Memory untouched:
  Memory=1, receipts=4, Agent messages=10. This is actual no-repeat evidence.
- Memory scripted tail failed finding the next choice; log exit 1 preserved.
  That does not invalidate earlier formal receipts or prove unexecuted steps.
- Separate lifecycle sequence exited 0: acknowledged signed login, SecureStore
  restoration/revalidation after force-stop, background/foreground, explicit
  B login, logout and cleared-storage restart. SQL control sequence enabled/
  unpaused→enabled/paused→revoked/paused kept Memory=1; native confirmed
  delete-all with revoke produced Memory=0, receipt=1, Agent history=2 retained.
  Evidence `.cache/phase8f-native-lifecycle.log`, `.json`, `.exit`.
  The first restart attempt was inconclusive (launcher/Demo), exit 1; the helper
  now waits for authenticated storage acknowledgement and reopens the base
  manifest before routing. No product storage change was made.

Evidence paths: `.cache/phase8f-native-memory.log`,
`.cache/phase8f-native-memory-evidence.json`,
`.cache/phase8f-native-memory.exit`; native Import results added below.
No screenshots, tokens or private chat are committed. Sanitized UI state includes
only synthetic content; known credentials are redacted and password nodes omitted.

## Import and history procedure

`stage` creates 301 anonymous Markdown occurrences with equal timestamps and
repeated body, transfers the exact hashed file to
`/sdcard/Download/phase8f-synthetic.md`, and refuses to overwrite a different
existing file. Open actual Android picker; cancel once; reopen and select it.
Confirm picker selection if Android requires it. Native upload uses URI binary
Multipart, not path JSON. Bind self and anonymous person explicitly, select the
real Relationship, rebind if scope change invalidates speakers, request server
Ready, Finalize, then verify real receipt and 301 RelationshipMessages.

Navigate to relationship history; verify real 100→200→300→301 cursor pages,
repeated body with different IDs, Refresh to 100, scrolling and Back. Verify
Agent History independently, not by treating imports as Agent output.
Native attempt 3 completed with independent exit 0, evidence in
`.cache/phase8f-native-import-attempt3.log` and
`.cache/phase8f-native-import-attempt3.json`. Actual cancellation/reselection,
URI upload, binding, Ready and Finalize produced job
`cdb496e0-847c-4bdf-ab45-e82499264cb1` (imported, revision 5),
301 RelationshipMessages and zero active artifacts. All three More actions,
Refresh and empty AI Conversation were executed. The 200/300/301 count headers
were offscreen in those captures; they did not alone certify each count.
Cleanup and logout
completed. For parallel root checks, `--port 8024` uses a separate loopback
fixture; point only the device's `tcp:8022` reverse mapping at host `tcp:8024`.

Final pagination sequence **PASS**, independent exit 0. Each actual native header
was revealed and captured: 100→200→300→301, Refresh→100, separate AI Conversation→0.
Server retained 301 RelationshipMessages/zero active artifacts; exact staged
file was hash-verified and removed; session logged out. Evidence:
`.cache/phase8f-native-pagination.log`, `.json`, `.exit`.
Sanitized pagination JSON SHA-256:
`B3151CDAC4E8D38DC9485B501A27C09A6B2DF8496704CD33912D726E251B296E`;
lifecycle JSON SHA-256:
`4F48DF03395A400C032B178412E7E0CB94F12DD0C9F10D61B0EDF802146EC1BA`.

Reproduce the successful native subsets with
`--steps scripts/native/phase8f_import_steps.json` or
`--steps scripts/native/phase8f_memory_steps.json` added to the helper command.
Each starts its own database; these are separate runs, not proof of a complete
same-session six-surface native E2E. Run sequentially on the same device and port.
The commands contain only synthetic labels/placeholders, no credentials.

## Still required before native final PASS

Native create/update, REST/SSE exact same-key continuity and incremental reader
events, full six-domain B isolation and pending-mutation force-stop, relationship switch,
history lifecycle, controlled network/database/timeouts/response-loss/SSE-failure,
expired/stale confirmation and safe kill/restart reconciliation; Light/Dark,
multiline/long input and longer-list interaction. TalkBack NOT RUN. No FPS claim.

## Cleanup

Use `cleanup` only after the helper verifies the exact synthetic device file's
SHA-256 against the current local fixture. Never delete arbitrary Downloads.
Historical `/sdcard/Download/phase8d-native-wechat.md` requires its own original
fixture hash verification before exact removal. This session's hash check did
not match the retained original file, so nothing at that path was deleted.
Disposable database cleanup is
performed when the fixture stops; preserve failed logs and independent exits.
Remove only this session's ADB reverse mappings and temporary loopback helpers.
Do not wipe the existing AVD or kill unrelated user processes.

## Closeout procedure — 2026-10-12

The historical missing-evidence list above records the first 8F run. The
Closeout Addendum and `PHASE_8F_CLOSEOUT_MATRIX.json` record subsequent independent
executions without changing those historical results.

Use the existing Pixel_10/API37/Expo Go57 device. The closeout used
`emulator-5554`; no AVD wipe, Downloads deletion or production API changes.
Native reverse mappings are device8022→host8024 and device8092/8093→host8093,
with a loopback-only IPv4→IPv6 relay to Metro8092. Keep native fixture8024
separate from the Connected Memory Web fixture8022.

Enable `EXPO_PUBLIC_NATIVE_ACCEPTANCE_OBSERVER=1` only in the local Metro
environment. `__DEV__` and Android checks additionally disable the observer
in release builds, iOS and Web. It records accepted client parser events,
Reader calls, relative milliseconds, actual React-committed phase/progress,
Run consistency and terminal state. Snapshots never expose IDs, bodies, JWT,
Memory, prompts or provider keys; event/UI arrays each have a64-entry bound.
The compact accessibility-labelled panel exposes metadata to the native helper
without moving controls as observations grow. Reader calls and events are
counted separately. Progress is held before `final_response` by a fixture-only
MockLLM barrier, and verified in the visible Android viewport before release.
No CDP Runtime.evaluate or simulated token deltas are used.

`scripts/phase8_native_closeout.py --adb <absolute-adb.exe> --serial emulator-5554
--batch <new-name>` runs every independent scene; `--scenes` selects full
individual scenes. Run it through `uv run --locked python` with the existing
`TEST_DATABASE_URL`. Each scene force-stops/reopens Expo Go, uses a disposable
database and freshly issued signed CLI JWT, waits for SecureStore acknowledgement,
and writes a complete log, immutable step snapshot, metadata report and separate
exit file in `.cache`. Existing paths cannot be overwritten. Every execution
uses the real App, generated client, authorization and service/database paths.
Fault arms are private fixture-pipe commands, never public App endpoints.

`seed`, `save`, and `history_setup` are explicitly labelled host REST preconditions.
They do not count as native creation, Agent send or file picking. Resource-create
and Agent replay scenes use Android UI for their business mutations. Memory
scenes use real native Prepare/Execute/Receipt against synthetic host-prepared
Memory. Import regression retains the earlier actual picker/301-upload evidence
and adds scope, cursor, Back, Logout and background/foreground checks.

CI Metro does not hot-reload changed source. Restart only this task's verified
Metro process with `--clear` before testing an updated native bundle; inspect
the actual manifest's launch asset through the loopback relay. A DevTools
dotslash installation failure fell back to bundled DevTools and did not prevent
the native bundle from compiling. Do not mistake stale bundle behavior for
the latest implementation, or restart Metro during an active UI scene.

Failed scenes retain their logs and exits. Fix the cause and rerun the entire
independent scene with a new batch name. A selection of complete scene passes
closes individual matrix items; it does not turn a failed suite into exit0 or
claim one uninterrupted native six-surface journey. All artifacts are hashed
in the matrix; the Phase8 marker gate rejects incomplete execution transcripts.
