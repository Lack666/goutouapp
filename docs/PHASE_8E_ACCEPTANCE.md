# Phase 8E — Memory Controls and Guarded Mutations Mobile Integration

PHASE: Phase 8E only. Phase 8F is not started; whole Phase 8 remains IN PROGRESS.

STATUS: PASS — applicable8E CODE/TEST/DOC/DEMO/REGRESSION complete; independent
pre-marker and post-marker full root process exits both0. Native Memory NOT RUN.

## Roadmap preflight and 8D evidence reconciliation

Started from clean HEAD1c64562 on codex/phase8d-import-history, marker7/8D.
Read AGENTS, MASTER_PLAN, ARCHITECTURE and requested Memory/Agent/auth/UI/API/
retention/deletion/idempotency contracts and Phase6/8 acceptance reports. Audited
actual services/store/retention/router/generated client/session/epoch/Settings/
Agent controllers/root verifier. No frozen knowledge or production Agent behavior
was changed. New working branch: codex/phase8e-memory-controls.

Before 8E business code, full `.\make.cmd verify` at marker7/8D returned
independent process exit **0**.
Complete output: `.cache/phase8e-preflight-8d-baseline.log`; independent exit file:
`.cache/phase8e-preflight-8d-baseline.exit`. It ends with all active0..7/8A..8D
PASS and whole8 IN PROGRESS. Backend556; repository33; Mobile298; focused Import77;
Demo Web22; Connected resources3, Agent3, Import4; Doctor21/21; generated3;
OpenAPI36 operations/26 retained baseline; Golden83; Alembic upgrade/downgrade,
secret boundary, Ruff, TS/lint/format, frozen install and all earlier demos passed.

Execution used the existing local PostgreSQL16 cluster on127.0.0.1:15434 and
TEST_DATABASE_URL/DATABASE_URL for disposable/test/development databases, existing
Chrome and a correctly qualified C:\Windows\System32 PATH. These are local
verification dependencies, not deployed services. No external account/key needed.

Failed/aborted earlier attempts remain evidence, not PASS: sandbox/local socket
stall was aborted and its wrapper recorded1; the process cleanup stall was
aborted without an independently captured exit. Subsequent full
logs recorded exit1 for late Person names, Expo legacy schema network, a Ruff
formatting race, Demo History pagination and Connected History pagination.
Resolved late Person-name enrichment without changing scope/cursor; added2
arrival-order tests. Doctor fallback is narrow GET-only, public SDK schema,
network-error-only, from official exp.host to official api.expo.dev; no offline
schema or skipped check. Added3 tests. Moved shared History pagination outside
the virtualized footer; original11 History tests and original Demo/Connected
browser flows each repeated3 times passed. Original assertions/tests retained.
The successful full run occurred after all repairs, before 8E implementation.

217→219: commit5083062 added exactly2 sessionIsolation tests for immediate logout
invalidation versus durable credential removal acknowledgement, and storage-clear
failure not falsely claiming complete logout. 8D added77:219+77=296. This preflight
added2 resource arrival-order cases:298. No old Mobile tests were removed.

ANDROID CLEANUP: CLEANUP DEFERRED. Initially emulator-5554 offline; one reconnect
left no online device. Later recheck again showed emulator-5554 offline.
No device file was read/deleted. Only the documented exact
anonymous fixture path `/sdcard/Download/phase8d-native-wechat.md` is eligible for
identity-verified cleanup when available.

## Engineering evidence

GENERATED CLIENT: existing36 operations unchanged;13 Memory endpoints reused.

MEMORY CONTROL / CONSENT / PAUSE / RESUME: shared JWT client, separate consent and
pause, explicit operations and authoritative GET; no optimistic state authority.

CONTROL OUTCOME RECOVERY: actual commit with dropped response re-inspected; failed
inspection stays unconfirmed. Unit tests also verify both-failure behavior.

MEMORY INSPECT / PERSON / RELATIONSHIP SCOPE: owned selectors, bounded50/200 cursor
window, actual IDs, known-ID detail, public adapters, explicit empty/error/retry.

RETENTION / EXPIRY: real server policy including37-day E2E configuration, default
active list and recall exclude expired before cleanup, known-ID expired detail.

GUARDED UNDO / UNDO IDEMPOTENCY: global latest preview, exact operation ID/key,
explicit confirm; response-loss retry does not undo newly exposed older record;
same-key changed payload409 and foreign receipts/details404.

DELETE-ONE / DELETE-PERSON / DELETE-ALL: real server prepare then confirm execute;
one actual record scope, Person structured across relations, all explicit
retain/revoke choice. Changing choice invalidates challenge; server count includes
expired primary records. Person and conversation identities/history retained.

SERVER CONFIRMATION / CONFIRMATION EXPIRY: real action/target/scope/count/consent/
issued/expiry/notice review; local timer plus server stale/expired guards; no bypass.

MUTATION RECEIPT / UNKNOWN DESTRUCTIVE OUTCOME: durable formal receipt projection,
GET versus POST replay semantics, original key/path/body only, no auto prepares,
no list-based fake success, verified old receipt retained on optional replay failure.
Session-only recovery intentionally loses key on restart and discloses this limit.

SESSION / OWNER ISOLATION: existing epoch/cancellation/logout, A→B clear all state
and attempts; late non-cooperative responses tested. Scope/background clear record
UI and unexecuted challenges. Foreground GET only; active/unknown operation blocks
new target changes until safe recovery.

AGENT MEMORY INTEGRATION / IN-FLIGHT CONTROL SAFETY: real AgentService/LangGraph
with established Phase6Mock. Consent/pause/resume affect actual recall and writes,
REST/SSE exercise same persistence. Existing32 Phase6 E2E cases remain in root,
including in-flight control changes, expiry, safety and concurrency. No production
reasoning or inference behavior was changed; Golden corpus stays unchanged.

DEMO MODE: existing synthetic Settings/controls retained, no business network;
Connected never synthesizes records. Chat Memory entry navigates only.

PRIVACY / DELETION COPY: primary memory/undo deletion versus retained metadata,
Agent/RelationshipMessages/identities, backup/log/provider copies and historical
uncertainty stated accurately. Not “all personal data deleted”.

REAL JWT HTTP / REAL POSTGRESQL: CLI issuer, disposable migrated actual PostgreSQL,
real FastAPI sockets and real Memory services; no auth override or fake HTTP store.

EXPO WEB CONNECTED E2E: Chrome actual Settings, Agent SSE, control/Undo/one/Person/
all confirmation, durable receipt/replay, new records surviving old replay, A→B
and committed-response-loss recovery. Final counts/results recorded below.

ANDROID NATIVE MEMORY E2E: NOT RUN; unavailable existing device. No native PASS
inferred from Web; native procedure in MOBILE_MEMORY_INTEGRATION. Deferred to8F.

## Final gates (filled only from completed processes)

MOBILE TESTS:346/346 full,48/48 Memory focused;20 suites. Retained298 + new48.
BACKEND REGRESSION:556/556, including32 Phase6 E2E; repository36/36.
ROOT VERIFY: complete pre-marker and post-marker PASS; adds focused Memory and real Memory HTTP/Web gates, keeps all
prior gates and adds git diff --check. Expo Doctor remains full21 checks.
The first8E full pre-marker run exited1 at the old8B browser request allowlist:
it prohibited the newly legitimate Settings Memory GETs. The same existing test
now allows only control/list/preview paths and explicitly checks all Memory
requests are GET. No resource assertions or test cases were removed; counts stay
unchanged. Other gates in that run included backend556/Mobile346/focused48/Doctor21/
Demo22 PASS. This failed run is not used as final acceptance.
PRE-MARKER EXIT CODE:0 independently returned by process and stored in
`.cache/phase8e-pre-marker-final.exit`; full output `.cache/phase8e-pre-marker-final.log`.
Counts:556 backend,346 Mobile,48 Memory focused,36 repository,Doctor21/21,
Demo22,resource3/Agent3/Import4/Memory5 (3HTTP+2Chrome),OpenAPI36/generated3,
Golden83/Alembic/secret/diff/frozen dependencies and all prior gates PASS.
Final type-only reuse of existing Settings ViewModels was then aligned before
marker update; typecheck and full346 Mobile tests passed again, with no runtime
behavior or count change (`.cache/phase8e-final-contract-tests.log`).
POST-MARKER EXIT CODE:0 independently returned by process and stored in
`.cache/phase8e-post-marker.exit`; full output `.cache/phase8e-post-marker.log`.
Final marker7/8E run passed the same556/346/48/36,Doctor21/21,Demo22 and
Connected resource3/Agent3/Import4/Memory5 (3HTTP+2Chrome), all prior gates,
OpenAPI36/generated3/Golden83/Alembic/secret/diff/frozen dependencies.
It includes final Settings ViewModel reuse and the specified changed-target
message for both stale_undo and undo_unavailable. Empty preview remains empty;
no expired/deleted target ever triggers automatic fallback to an older operation.
PROJECT PHASE MARKER:7/8E after pre-marker root0 and final type validation.
Whole Phase8 stays IN PROGRESS; post-marker full root has completed0.

Log SHA256:8D baseline
`4AC5EFF464436AEAA6546F07B98497DFEBDFDD8B11844BE7F503684A57C16029`;
8E pre-marker
`4001DE69D1126C1B1C092EFE9DDA65FE78C383A81E34B61E448664D1888D6216`.
8E post-marker
`C65AC21199B44539E8B087BC346DFD05FC60221135CF3A838BCAA7145B6C4021`.

VALIDATION COMMANDS: `.\make.cmd verify`; `pnpm --filter @goutou/mobile run
test:memory`; `smoke:memory`; `typecheck`; `lint`; `format:check`; existing root
OpenAPI/generated/frozen knowledge/dependency/Golden/Alembic/secret checks.
Full outputs and explicit exit files retained in ignored `.cache`, no JWT in
reports or browser traces. Paths/exit/hash above refer to completed processes.

FILES CHANGED: public Memory adapter/errors/contracts/controller/Settings panel,
shared transport/composition, Chat navigation/Home copy,48 focused tests, real
HTTP/Web fixture/config/tests, verifier/gate tests, Memory and existing architecture/
Settings/API/Chat/handoff/readme docs, plus documented preflight repairs above.

ARCHITECTURE DECISIONS: reuse generated API/session/transport and server authority;
guard IDs and immutable attempts, no local security confirmation/journal/database;
server policy and receipts stay authoritative; no new dependencies/infrastructure.
See [ADR0035](adr/0035-mobile-memory-guards-and-session-recovery.md).

KNOWN ISSUES: app restart loses unconfirmed mutation key; cannot safely auto retry.
Android device unavailable. Existing production scheduler/backup restore replay is
not deployed. Authentication remains development CLI JWT, not production onboarding.

DEFERRED: native Memory/fault/keyboard/theme final evidence and full Mobile final
acceptance to8F. No Phase9 security project, RAG or new chat analysis.

NEXT: Phase8F — Full Mobile Integration and Phase8 Final Acceptance, only after
another explicit instruction. Stop after8E; never mark whole Phase8 PASS here.

## Changed files (43; logs remain local and ignored)

```text
apps/mobile/README.md
apps/mobile/connected/fixture.ts
apps/mobile/connected/web.spec.ts
apps/mobile/memory-connected/http.spec.ts
apps/mobile/memory-connected/support.ts
apps/mobile/memory-connected/web.spec.ts
apps/mobile/package.json
apps/mobile/playwright.memory.config.ts
apps/mobile/src/api/memoryAdapter.ts
apps/mobile/src/api/memoryErrors.ts
apps/mobile/src/api/transport.ts
apps/mobile/src/components/HistoryList.tsx
apps/mobile/src/contracts/connectedMemory.ts
apps/mobile/src/data/memoryController.ts
apps/mobile/src/data/resourceController.ts
apps/mobile/src/features/ConnectedChatScreen.tsx
apps/mobile/src/features/ConnectedMemoryPanel.tsx
apps/mobile/src/features/HomeScreen.tsx
apps/mobile/src/features/SettingsScreen.tsx
apps/mobile/src/session/ConnectionProvider.tsx
apps/mobile/tests/connectedMemory.test.ts
apps/mobile/tests/connectedMemoryUI.test.tsx
apps/mobile/tests/memorySupport.ts
apps/mobile/tests/resourceNames.test.ts
apps/server/mobile_connected_fixture.py
docs/ARCHITECTURE.md
docs/MASTER_PLAN.md
docs/MOBILE_AGENT_CHAT.md
docs/MOBILE_API_CLIENT.md
docs/MOBILE_ARCHITECTURE.md
docs/MOBILE_HISTORY_UI.md
docs/MOBILE_MEMORY_INTEGRATION.md
docs/MOBILE_SETTINGS_UI.md
docs/PHASE_8D_ACCEPTANCE.md
docs/PHASE_8E_ACCEPTANCE.md
docs/PHASE_8_MOBILE_INTEGRATION_HANDOFF.md
docs/adr/0035-mobile-memory-guards-and-session-recovery.md
project-phase.json
scripts/check_mobile.py
scripts/expo_doctor_fetch.cjs
scripts/verify.py
tests/test_expo_doctor_network.py
tests/test_mobile_phase_gate.py
```
