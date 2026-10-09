# Mobile POST SSE — Phase 8C

The installed Expo57.0.27 source was audited: `src/winter/fetch/fetch.ts`,
`FetchResponse.ts`, `src/winter/TextDecoder.ts`, Android NativeResponse/ResponseSink
and `expo/fetch` exports. The SDK supplies native ReadableStream and streaming UTF-8
decoding. The [official SDK57 documentation](https://docs.expo.dev/versions/v57.0.0/sdk/expo/)
documents streaming fetch and these APIs. No new streaming/native dependency or
Expo/RN upgrade is introduced. Web uses standard fetch; `.native.ts` explicitly uses
`expo/fetch` and adapts URL/method/headers/JSON body/signal. Installed-source support
is not an on-device result. Android Connected SSE remains separately verified.

`ApiTransport.streamAgent` sends POST JSON + current Bearer + Accept:text/event-stream
to the existing `/api/v1/conversations/{conversation_id}/agent-runs/stream`.
It shares baseURL validation, epoch,401 invalidation and cancelAll with resources
and generated REST/history. Cookies and redirects are disabled. The allowlist adds
only Agent REST/POST SSE/Agent History; Import and Memory remain inert. The default
transport remains resource-only unless explicitly composed with Agent enabled.

The 60-second Agent deadline covers headers and all body reads. Explicit rejection
races fetch and reader.read, including transports that ignore AbortSignal. Reader
cancel is fire-and-forget so a native cancel that never settles cannot trap the caller;
listeners/timers/controllers are released and stale events cannot update the UI.
The underlying native cancellation may settle later. HTTP errors are normalized
before stream parsing; unexpected Content-Type/body absence is rejected.

SSEParser is independent of UI/framework. TextDecoder fatal UTF-8 with stream:true
preserves arbitrary multibyte boundaries. It incrementally recognizes LF,CRLF and
CR, blank frame delimiters, multi-line data, comments and incomplete final buffers.
It never assumes a network chunk equals a frame. It caps each frame at128KiB and
the total stream at512KiB (including comments/unknown data). Invalid JSON/UTF-8,
unknown fields/events, extra internal fields and unsupported versions fail closed.
V1 has no id/retry extension or server heartbeat negotiation. Harmless comments
are accepted; an incomplete final event is rejected. A valid terminal frame ends
consumption without waiting for socket EOF. A nonterminal EOF is outcome unknown.

OpenAPI models SSE as string, so `agentEvents.ts` is a narrow manually audited
discriminated union from `app/schemas/stream_event.py`, not a duplicate REST DTO.
Every envelope requires exact schema_version,event,run_id,data; data fields and
bounded public vocabularies are validated. Unknown version/event policy is rejection,
with no reinterpretation as V1. Tests exercise all seven event types and all byte splits.

- run_started: persistent user Message/running AgentRun accepted; stores actual run ID.
- status: public progress only, before final answer; no token delta or node names.
- final_response: committed assistant Message ID and complete validated text.
- memory_status: read-only public receipt, after answer commit.
- pending_confirmation: read-only formal-confirmation instruction, after answer commit.
- completed: terminal success; assistant ID must match final_response and memory receipt.
- failed: terminal failed or running_unknown with safe public code; no fabricated answer.

All events must match one run ID, including retries. The controller checks sequence,
terminal state and assistant ID. Completed replay may contain only final_response and
completed without run_started/status. A final_response received without completed
keeps its confirmed answer but leaves operation completion unknown. History merges
that same Message ID rather than adding a second assistant bubble.

The server commits the user/run before streaming. Before assistant commit, disconnect
attempts to cancel runtime/mark failed, retaining the user Message. After assistant
commit, disconnect retains completed run/answer; unfinished optional memory may be
cancelled and already committed memory stays. Running metadata can remain unresolved.
Neither timeout nor client abort proves the server stopped. Same-key controlled retry
uses Phase4 replay semantics; no automatic fresh-key retry or live reattachment.

## Reproduce the actual Web/socket demo

Use a local PostgreSQL16 psycopg `_test` namespace, locked uv/pnpm and installed Chrome:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONUNBUFFERED='1'
$env:TEST_DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:15434/goutou_test'
$env:PLAYWRIGHT_CHROME_PATH='C:\Program Files\Google\Chrome\Application\chrome.exe'
$env:PATH='C:\Windows\System32;'+$env:PATH
pnpm --filter @goutou/mobile test:sse
pnpm --filter @goutou/mobile test:agent-chat
pnpm --filter @goutou/mobile demo:agent
```

The demo creates/migrates/drops a randomized PostgreSQL DB, signs actual CLI JWTs
over private pipes, composes actual LangGraph/AgentService with a deterministic
MockLLM and starts actual FastAPI8019/Expo Web8089. Three tests verify REST loss,
SSE completed-frame loss, cross replay/concurrency/ownership/persistence/history
and real browser Chat/reload/re-entry/logout. Reports contain only necessary status,
event categories, IDs/counts/assertions; traces/video/screenshots are disabled.
No JWT or signing secret is written to public configuration or fixtures.
The Mock fixture uses only the synthetic violence prompt; it is not a real provider.

## Android Studio manual acceptance

An emulator launch was attempted on this host; see the acceptance report for actual
adb evidence. Native fetch/SecureStore/Back/keyboard behavior cannot be inferred from
Web, Expo Doctor, TS checks or Android JS export. Final Phase8 requires native proof.

1. Start the configured Pixel_10 emulator or a physical Android device with an
   SDK57-compatible Expo Go/development build. Confirm `adb devices -l` is stable.
2. Reuse 8B local HTTP policy: `adb reverse tcp:8000 tcp:8000`, or use emulator host
   gateway `http://10.0.2.2:8000`; never assume emulator localhost is the Windows host.
   Set only EXPO_PUBLIC_API_BASE_URL, then restart Metro. Production remains HTTPS.
3. Start the interactive disposable backend below in one terminal, leaving it open.
   It prints only owner IDs/readiness and writes private server CLI settings to an
   ignored `.cache` env file, removed on stop. In another terminal, invoke the actual
   development CLI with that file and owner ID. Its15-minute token is for manual
   hidden input only; never put it in a report, screenshot, trace or public env.
4. Manually enter the CLI credential in Settings, verify server probe, create/select
   owned generic and bound Conversations, open Chat and send the synthetic prompt.
5. Verify POST SSE reaches the actual device, body reader yields multiple frames,
   run_started/safety status appear, Chinese text renders correctly, final_response
   and completed agree on IDs, loading ends and DB has one user/assistant pair.
6. Test same-key REST/SSE retry, offline/timeout, Android Back/page switch/background,
   then history refresh/restart, credential restoration/expiry, logout and OwnerB.
   Verify stale frames are rejected and no old messages survive identity replacement.
   Test keyboard visibility and a real 360px touch flow. Do not expose the token.
7. Record command/device/build, observed frame types/IDs/counts, native SecureStore
   behavior and manual UI results separately. Mark unexecuted items NOT RUN.

These steps require real native execution; automated Web success is not an Android PASS.

```powershell
# Terminal1, with TEST_DATABASE_URL from the Web reproduction section:
uv --cache-dir .cache/uv --no-managed-python run --locked python apps/server/mobile_agent_native_demo.py
# Terminal2: use the owner_a or owner_b UUID printed by Terminal1:
uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .cache/phase8c-native-server.env python apps/server/dev_auth_cli.py token --user-id <printed-owner-UUID>
adb reverse tcp:8019 tcp:8019
$env:EXPO_PUBLIC_API_BASE_URL='http://127.0.0.1:8019'
pnpm --filter @goutou/mobile exec expo start --clear
# Open on the actual Android device; use the synthetic violence prompt above.
# Enter stop in Terminal1 after manual acceptance to remove the DB/private env.
```
