# Phase 8C acceptance — 2026-10-09 (Asia/Shanghai)

PHASE: Phase 8C — Agent Chat REST / POST SSE Integration

STATUS: PASS — CODE, TEST, DOC, actual Web/socket DEMO and REGRESSION passed.
Full root verification exited0 both before and after advancing to7/8C. This is
Web engineering acceptance; ANDROID CONNECTED SSE: NOT RUN, whole Phase8 incomplete.

ROADMAP PREFLIGHT: HEAD5b14f11, clean worktree, marker7/8B. Read required plans,
architecture/contracts/handoffs/7-final/8A/8B acceptance and actual source/tests.
Existing signed SSE/Disconnect/Idempotency33 and retained Mobile143 actually passed
with new parser/controller tests in the full207-case run. Initial preflight used a
nonexistent test filename; corrected33-case execution is the acceptance evidence.
No Agent behavior, upstream snapshot, provider core contract or future-phase change.

EXISTING AGENT / SSE AUDIT: Actual routes/schemas/AgentService/persistence/auth,
operation fingerprint/replay/conflict/disconnect and public Agent History checked.
V1 is POST JSON/Bearer progress plus a complete committed answer, not token deltas.
Expo57.0.27 installed fetch/reader/TextDecoder source and official SDK57 docs audited.

GENERATED CLIENT: Existing unchanged36-operation authority/client reused for REST,
Conversation verification and History; SSE string has a separately audited V1 union.

CONNECTED CHAT: Shared composer/FlatList/theme/navigation; real resource selector,
states/draft/keys/IDs/read-only receipts and actual committed text. Demo retained.

REAL CONVERSATION SCOPE: Owned GET first, UUID validation, nullable generic/bound
scope and relationship assertion; foreign/missing404 neutral, invalid scope fail closed.

AGENT REST: Generated body/response, real JWT, actual run/Conversation/assistant IDs,
memory/warnings, safe auth/validation/conflict/recovery and uncertain completion.

POST SSE TRANSPORT: Native expo/fetch adapter/Web standard fetch, shared8B session,
origin/epoch/401/cancel, JSON POST,60-second deadline through reader and explicit race.

SSE PARSER: Independent incremental parser, blank delimiters/LF/CRLF/CR/multiline
data/comments/EOF/invalid JSON/version/event,128KiB frame/512KiB total bounds.

UTF-8 / CHUNK BOUNDARIES: Every two-part byte split and single-byte Chinese/emoji,
partial JSON and CRLF tested; incomplete/illegal UTF-8 fail closed.

EVENT V1 MAPPING: All seven public event types validated/mapped; status separated
from answer, committed text before completed, failed/unknown and read-only memory.

RUN ID: One immutable server run per logical operation; mismatch/old event rejected.

OPERATION KEY: Crypto UUIDv4 reserved with immutable payload before send; duplicate
click guard; per-Conversation retry, new explicit messages get new keys only after
known terminal outcome. Keys are session-memory, bounded20 attempts, no durable outbox.

IDEMPOTENT RETRY: Actual postcommit REST response loss and SSE completed-frame loss,
same-key recovery, concurrent attempts; DB run/user/assistant counts and provider calls
unchanged on replay. Memory counts unchanged; positive Memory replay also remains
covered by retained Phase4 PostgreSQL tests, not inferred from the zero-memory fixture.

UNKNOWN OUTCOME RECOVERY: No automatic new key; original REST/SSE retry or History.
Running/busy/unresolved explicit; History cannot prove a run's final metadata status.

REST/SSE CROSS-REPLAY: Both directions preserve run and Message IDs with no execution.

DISCONNECT / CANCEL: Reader cleanup/page blur/scope/background/logout/expiry isolation;
actual Phase4 socket pre/postcommit cases retained. Client stop never claims rollback.

SESSION / OWNER ISOLATION: Shared8B token only, guarded navigation stack reset;
old HTTP/events rejected, all state cleared on OwnerA→B. Actual foreign404/emptyB UI.

AGENT HISTORY: Generated public Message pages, bounded cursor continuation/refresh,
timestamp+UUID order/equal timestamps/empty/error/retry/scope reset and reload recovery.

MESSAGE DEDUPLICATION: Server Message ID only, identical bodies remain distinct.
Pending submission shown as status, not an optimistic formal user bubble. Confirmed
SSE/REST assistant shares actual History ID; refresh never adds a duplicate reply.

MEMORY STATUS: Read-only receipt/pending explanation; no formal Memory HTTP mutation.

FIU / SAFETY PRESENTATION: Only committed text/public progress; no inferred FIU DTO,
node state, hidden reasoning, prompt or synthetic fallback in Connected Chat.

DEMO MODE REGRESSION: Original seven previews/local composer/fixtures remain unchanged;
full Demo browser regression is included in root verify.

REAL JWT HTTP: CLI15-minute signed JWT, actual production verifier/HTTP/PostgreSQL.

REAL SSE SOCKET: Actual FastAPI POST SSE/MockLLM/AgentService/LangGraph in3 integration
scenarios; no mock-fetch substituted for server execution/authentication.

POSTGRESQL PERSISTENCE: Completed run/user/assistant IDs/owner/Conversation and exact
counts checked after real loss/replay/concurrency, formal History recovery and isolation.

EXPO WEB CONNECTED E2E: Actual Chrome/Expo sends POST SSE, displays completed answer,
replays REST, reloads/re-enters volatile credential and recovers History, logs out/B clears.
Browser revealed empty-stack dismissAll error; canDismiss guard fixed it. First recovery
test incorrectly used full document navigation after credential entry; SPA navigation
now exercises the intended volatile Web lifecycle. Failed attempts are not PASS evidence.

ANDROID NATIVE CONNECTED E2E: ANDROID CONNECTED SSE: NOT RUN. Actual Pixel_10
launch with no-snapshot/no-boot-anim/no-audio/software GPU did not produce an adb
device;127.0.0.1:5555 connection refused10061. Captured launch/crashpad logs under
`.cache/phase8c-android-launch.*.log`; no app/reader/UTF-8/native credential/Back/
keyboard PASS. Explicit local native Mock backend/CLI/network steps provided;
whole Phase8 must still obtain actual Android evidence.

MOBILE TESTS: Pre-marker full216, then final expiry case and focused parser28/
controller42/UI4 passed (74 new total); prior143 retained. StrictTS, lint, formatting,
offline frozen install, clean peers, SDK/Doctor21/21 and generator3 passed. Android
JS export passed independently. Accepted-marker full217 passed (143 retained +74 new),
including parser28 and controller42/UI4. No failed or unexecuted check is counted.

BACKEND REGRESSION: Retained555, all Agent/Import/Memory, Golden83, repository27,
actual migration cycle/check, frozen knowledge and Ruff170 passed. No runtime/provider/
schema/contract/lock resolution changes.

ROOT VERIFY: Pre-marker full PASS exit0 at7/8B, `.cache/phase8c-verify-pre-marker-clean.log`.
Earlier attempts failed a retained8B resource-only path assertion (Chat now legitimately
GETs formal Agent History), then one test-file formatting gate. Updated the assertion
to allow only that scoped History route, retaining all3 cases/no Agent POST/Import/
Memory; fixed formatting. Those failed logs are retained and not counted as PASS.
Accepted-marker full rerun at7/8C PASS exit0, `.cache/phase8c-verify-final.log`:
backend555, repository27, Golden83, Mobile217, Demo Web22, resources3 and Agent Chat3.

VALIDATION COMMANDS / OUTPUT: Actual commands and final results are recorded below.

ARCHITECTURE DECISIONS: ADR0033; shared authenticated transport, narrow V1 validation,
explicit unknown outcomes, ID-based History reconciliation and per-page consumption.

FILES CHANGED: Mobile transport/event/parser/platform adapter/controller/Chat UI,
shared composer/list/session/navigation and retained8B browser expectations; new unit/UI/
real socket/browser suites; optional Mock composition in disposable fixture and an
executable native manual backend/CLI entry; root gates, docs/ADR/scripts.
Knowledge/contracts/uv/pnpm resolution/Agent/Import/Memory untouched.

KNOWN ISSUES: Android native execution NOT RUN; pending keys lost on process restart,
no durable outbox/reconciliation/reattachment; public History lacks run association and
SSE final answer lacks timestamp. Cursors are live views. These limits are visible;
no automatic resend, invented time/status or production/provider quality claim.

DEFERRED: 8D Import/RelationshipMessage history;8E Memory controls; production auth,
real provider smoke/quality, FIU/Profile DTO and final Android verification.

PROJECT PHASE MARKER: completed_phase=7, completed_subphase=8C, advanced after all
applicable engineering gates passed. Whole Phase8 IN PROGRESS / NOT YET COMPLETE.

NEXT: Phase 8D — Chat Import and History Mobile Integration. Stop after8C, do not start8D/8E.

## Executed commands and evidence

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONUNBUFFERED='1'
$env:TEST_DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:15434/goutou_test'
$env:DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:15434/goutou_dev'
$env:PLAYWRIGHT_CHROME_PATH='C:\Program Files\Google\Chrome\Application\chrome.exe'
$env:PATH='C:\Windows\System32;'+$env:PATH
uv --cache-dir .cache/uv --no-managed-python run --locked pytest -q apps/server/tests/test_agent_stream_contract.py apps/server/tests/test_agent_stream_api.py apps/server/tests/test_agent_stream_disconnect.py apps/server/tests/test_phase4_idempotency.py
pnpm --filter @goutou/mobile test
pnpm --filter @goutou/mobile test:sse
pnpm --filter @goutou/mobile test:agent-chat
pnpm --filter @goutou/mobile smoke:agent
$env:PYTEST_ADDOPTS='--basetemp=.cache/phase8c-pytest-pre-marker-clean -o cache_dir=.cache/phase8c-pytest-pre-marker-clean-cache'
.\make.cmd verify # exit0, marker7/8B; full216 plus focused46, parser28
# Advance only to7/8C after gates; mandatory accepted-marker rerun:
$env:PYTEST_ADDOPTS='--basetemp=.cache/phase8c-pytest-final -o cache_dir=.cache/phase8c-pytest-final-cache'
.\make.cmd verify # exit0, marker7/8C; Mobile217, backend555, Demo22/resources3/Agent3
pnpm --filter @goutou/mobile exec expo export --platform android --output-dir ../../.cache/phase8c-android-export
```

Actual focused74 and socket/Web3 pass. The native manual backend/CLI was also
executed over actual HTTP/PostgreSQL: completed REST and2 formal messages, private
configuration removed on stop. It is not native-device proof. Credentials travel through internal
pipes; no tracing/video/screenshots. Evidence under ignored `.cache` is never staged.
