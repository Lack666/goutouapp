# Phase 8D acceptance — 2026-10-10 (Asia/Shanghai)

PHASE: Phase 8D — Chat Import and History Mobile Integration

STATUS: PASS — applicable8D CODE/TEST/DOC/DEMO/REGRESSION gates, including
complete accepted-marker root verification. Android core import/history PASS;
remaining native matrix PARTIAL.
Whole Phase8 remains IN PROGRESS / NOT YET COMPLETE.8E not started.

ROADMAP PREFLIGHT: clean HEAD5083062, marker7/8C. Required plan/architecture/
handoff/8A–8C and Import/History/client/resource documents read. Actual code,
OpenAPI, session/transport/generated contracts, UI/controller and Android
configuration audited. See PHASE_8D_API_AUDIT.md for exact discrepancies.

EXISTING IMPORT API AUDIT: Existing Phase5 transport/services unchanged. Ready
and cancel have no revision body; PUTs/finalize require expected_revision. Inspect
only has receipt summary and bounded issue samples. No upload recovery lookup.

GENERATED CLIENT: Same36-operation authority/client, narrow binary FormData
serializer and additional existing-route allowlist. Memory operations disabled.

FILE PICKER: SDK57 official picker57.0.3/filesystem57.0.7, actual Web File/native
cache File, explicit selection/upload/cancel/reselect, size/MIME/name, no base64.

ANDROID FILE URI: SDK57's automatic picker copy is in Expo Go's unreadable host
cache. Android keeps the user-granted content URI and immediately copies it with
FileSystem into owned Paths.cache; only readable owned binary is uploaded.
Original content URI is never used as source text or deleted. Grant/read/copy/
eviction failures require explicit reselection. iOS device verification NOT RUN.

MULTIPART UPLOAD: Binary file plus explicit IANA source_timezone and actual
wechat_markdown_v1, shared JWT and library-generated boundary. No fake progress.

UPLOAD UNKNOWN OUTCOME: Upload response loss blocks repeat upload, preserves
known selected metadata, and explicitly states a Job may already exist.

IMPORT JOB: Formal inspect after creation, on return/foreground and known UUID
recovery. Server status/revision/artifact/summary/inventory/issues displayed.

PARSER SUMMARY: Historical UTC bounds/source zone, counts and raw labels;
warning/error/truncation totals plus at most20 issue-code samples accurately labelled.

SPEAKER BINDING: Explicit self/person/system/ignore, actual owned Person UUIDs.
No nickname/self inference. Person creation uses existing resource screen.

RELATIONSHIP BINDING: Actual owned UUID, explicit confirmation and compatibility
precheck; authoritative permission/readiness remains on server. Changes invalidate
all speaker confirmations.

REVISION HANDLING: Last server revision only. Conflict inspect updates state,
invalidates confirmations and requires user resubmission. No local revision increment.

SERVER READINESS: Explicit existing ready API; no finalize before confirmed ready.
Extra human/group issues remain server-owned and editable system/ignore selections.

FINALIZE: Existing server endpoint, original Job/revision, no second file.

IMPORT RECEIPT: Full finalize receipt or explicitly distinguished inspect summary,
actual counts/Job/dataset/scope/historical bounds/import time/replay status.

FINALIZE IDEMPOTENCY: Known Job inspect before controlled retry, imported summary
recovery, explicit same-Job replay and exact-dataset duplicate semantics unchanged.

CANCEL: Client stop does not claim server cancellation. Actual cancel response
or inspect must confirm cancelled. Imported Jobs cannot be cancelled as editable.

HISTORY API: Separate generated RelationshipMessage and Agent Message APIs.

CURSOR PAGINATION: Opaque100-row pages, serialized More, stable server IDs, no
content deduplication, service order/equal timestamps, finite2,000-row collection.

OWNER / RELATIONSHIP ISOLATION: Shared epoch/generation/cancellation lifecycle,
scope/domain/route/logout clears records/cursors/source metadata and stale responses.

AGENT HISTORY SEPARATION: Imported Person/system/self never become assistant/user.

PRIVACY: No app logging of content/files/JWT, third-party upload or real private
fixture. Browser trace/video/screenshots are off; credentials are injected through
private process pipes. One ignored native automation helper initially exposed a
disposable test JWT in a TimeoutExpired traceback. Its isolated fixture was torn
down and the helper now suppresses private arguments on all timeout paths. No
production credential or user chat was involved; this failed attempt is not
counted as a privacy PASS. Artifact/backup policy is unchanged.

NO AUTOMATIC AI ANALYSIS: Import success only says records can be viewed in
History. No Agent invocation, imported-analysis input, FIU/Profile or Memory save.

DEMO MODE REGRESSION: Original local wizard/history retained, shared speaker
controls extracted without changing Demo behavior. All22 real Chrome Demo tests
passed (light/dark,320/360/412px, all6 surfaces and recovery).

REAL JWT HTTP: PASS,3 actual socket scenarios with dev_auth_cli-issued signed JWT,
no dependency/auth override. Generated binary upload, explicit revision PUTs,
ready/finalize, permissions and separate history verified.

REAL POSTGRESQL: PASS,PostgreSQL16.15 at127.0.0.1:15434 with disposable databases.
1,001 same-time/same-content occurrences persist as distinct IDs; all11 cursor
pages return them. Same-Job replay writes0, exact duplicate Job writes0 and can
be cancelled independently; Agent Message and Memory counts do not increase.

EXPO WEB CONNECTED E2E: PASS,actual Chrome/Expo Web FileChooser reads a physical
anonymous Markdown fixture, explicit bindings/relationship/readiness/finalize,
formal History100→200→refresh100, separate empty Agent History and logout/OwnerB.
Together with real HTTP tests `smoke:imports` passed4/4 in the latest complete
pre-marker and accepted-marker roots.

ANDROID NATIVE CONNECTED IMPORT: CORE PASS / PARTIAL MATRIX. Actual Pixel_10,
emulator-5554,Android17/API37,Expo Go57.0.9,SDK57; Metro8082 and disposable
FastAPI8021 via adb reverse, PostgreSQL16.15. Android DocumentsUI/Downloads
opened, cancelled, reopened and selected the physical anonymous67561-byte
Markdown. Granted content URI was copied to owned File; actual binary multipart
created a Job parsing1,001 messages/two unbound labels/Asia/Shanghai/historical
2024 UTC bounds. UI explicitly submitted self, actual Person UUID and owned
Relationship, then server ready/finalize. Native receipt showed imported/new1001;
private DB evidence confirmed Job357328b2-25a2-44e8-a66e-5db709f05b7b,
revision3/imported,RelationshipMessage1001,Agent Message0,Memory0,active artifact0.
Formal native History read the same owned scope and showed ready/100 records.

Native upload is PASS independently of Web. Native More100→200, complete scroll/
Back/foreground/OwnerB and network-fault matrix are NOT RUN to completion. The
More attempt was interrupted by the15-minute credential expiry; no native200
claim is made. Earlier expiry during the editable Job returned Settings and
cleared visible file/Job state. Earlier failed cache adapters and long automation
scroll searches are preserved as failed attempts. A bottom-anchored step needed
upward scrolling after its content shrank. Metro restart was needed after a
development reload stalled. VirtualizedList emitted a slow-update warning during
automated flings; this is not a native performance PASS. iOS/cloud providers NOT RUN.
Manual reproduction and remaining steps are in MOBILE_IMPORT_UI.md. Temporary
successful fixture databases/artifacts and Metro were stopped. Three animation
scales were restored to1 and the original anonymous device fixture removed,
verified by a bounded cleanup script. A later optional repeat was blocked by
execution policy on Metro startup; its preparatory backend was stopped. The
emulator subsequently reported offline, preventing removal of the newly re-staged
anonymous file. After reconnecting, remove only
`/sdcard/Download/phase8d-native-wechat.md`. No private user file or external model
was used. The blocked repeat adds no native PASS evidence.

MOBILE TESTS: Preflight219 retained PASS. Focused `test:imports`77 PASS:
controller/adapters, Web/native binary/cache picker, UI, safe errors, unknown
outcomes, revision conflicts, foreground/leave, scope/owner/logout and delayed
conflict recovery, Android granted content-URI copy and read denial. Latest full
Mobile296/296 PASS; strict TypeScript,lint(no warnings),format,frozen offline
install,SDK compatibility/peer audit and Doctor21/21 PASS. Final display review
also hides replay for cancelled duplicate Jobs and labels real unscoped Agent
history as a conversation. Those files passed a subsequent formatting check;
accepted-marker root rechecked the final complete tree. Loaded8B resource pages
and selections are reused on Import/History entry.

BACKEND REGRESSION: PASS,556 full backend tests including retained Phase0–8C
contracts, Import/Memory and the new local PUT preflight test. No parser/merge/
Agent/Memory behavior or upstream snapshot change.

ROOT VERIFY: First full run stopped at8B browser regression. It exposed premature
Conversation navigation and a new Import resource refresh clearing shared
selection. Fixed by awaiting formal detail and reusing loaded owned resources;
8B3/3 and focused72 passed. Complete earlier pre-marker reruns exited0, with
Mobile291/293,focused72/74,backend556,Demo22,8B3,8C3 and8D4. The subsequent
latest294-test run passed backend/Mobile but a later Node process exited
3221226505 in test:agent-chat; that complete run is FAIL. After native URI fixes,
focused77 passed. Newest complete pre-marker root exited0:
`.cache/phase8d-verify-pre-marker-accepted.log`,backend556,repository30,
Mobile296,focused77,Demo22,8B3,8C3,8D4. Accepted-marker complete root PASS:
`.cache/phase8d-verify-post-marker.log` contains the same counts, all previous
stage gates and final all-active-phase PASS. Its polling handle was unavailable
after the permission-context change; no separate exit-code observation is claimed
for that run. The full completed verification output is the acceptance evidence.
Marker advanced only after the applicable engineering gates passed.

VALIDATION COMMANDS: Commands actually executed:

- `uv run --locked pytest apps/server/tests/test_mobile_dev_cors.py -q`:11 PASS.
- `pnpm --dir apps/mobile test:imports`:77 PASS(latest).
- `pnpm --dir apps/mobile typecheck`, `lint`, Prettier:PASS.
- `pnpm --dir apps/mobile smoke:imports`:4 PASS(real HTTP3,Chrome1).
- `pnpm --dir apps/mobile smoke:connected`:3 PASS after fixes.
- `.\make.cmd verify`: first8B failure fixed; two earlier complete pre-marker
  reruns PASS(exit0). A later run failed with Node exit3221226505. Latest full
  pre-marker run exited0. Accepted-marker full output PASS. Both include
  repository30,backend556,Mobile296,focused77,Demo22,8B3,8C3,8D4,locked offline
  install,SDK dependency/peer checks,TypeScript/format,Doctor21/21,Golden83,
  Alembic roundtrip/check,OpenAPI36 drift,Ruff and frozen Skill/secret boundaries.
- Android: `adb devices`, explicit8021/8082 reverse, SDK57 Expo Metro, native
  DocumentsUI and UI actions through adb input/uiautomator, private-pipe CLI JWT,
  real HTTP/PostgreSQL evidence. Synthetic screenshots only; no token-entry dump.
- `pnpm --dir apps/mobile exec expo-doctor`:21/21 PASS, no issues.
- `git -c safe.directory=... diff --check`:PASS under repository Windows
  autocrlf configuration. A check with invocation-only autocrlf=false incorrectly
  classified CRLF as whitespace; no global Git configuration was changed.

Initial failed attempts: sandbox pytest temporary directory ACL, registry timeout
while installing the official picker, an import fixture pipe branch placement,
Web PUT CORS preflight,8B selection/fixture races and native host-cache permission.
These were corrected and rerun; none is labelled PASS merely from prior reports.
Automatic approval interruptions(usage limit/proxy502) did not execute the
affected action; reviewed retries resumed it. No approval check was bypassed.

ARCHITECTURE DECISIONS: ADR0034; shared session/client/presentation, binary picker,
explicit uncertain outcomes and separate bounded history. No server semantic change.

FILES CHANGED: Mobile platform file adapter, generated DTO adapters, controllers,
shared selectors/rows, Connected pages/composition; tests/real fixture/gates;
docs and SDK-compatible pnpm lock. Frozen upstream/Agent/Memory unchanged.

KNOWN ISSUES: No upload operation lookup, production auth, durable client outbox,
full issue report, snapshot paging or resumable upload. Native Expo fetch buffers
the bounded multipart. App restart requires known UUID for Job recovery. Native
large-list performance, full lifecycle/fault/provider matrix and iOS are open;
Web/socket coverage is not substituted for these device results.

DEFERRED: 8E Memory HTTP/mutations, imported-chat analysis/public FIU/Profile,
RAG and whole Phase8 final acceptance. Native lifecycle evidence is separate.

PROJECT PHASE MARKER: completed_phase7/completed_subphase8D after applicable
CODE/TEST/DOC/DEMO/REGRESSION gates and complete pre-marker root PASS.
Accepted-marker complete root PASS. Whole Phase8 not complete.

NEXT: Phase 8E — Memory Controls and Guarded Mutations Mobile Integration.
Stop after8D. Do not begin8E or complete whole8.
