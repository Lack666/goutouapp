# Import / Analysis UI — Phase 8D

Connected now uses real ImportJob/RelationshipMessage transport. The historical
7C Demo description below remains valid for Demo only. See [audit](PHASE_8D_API_AUDIT.md),
[ADR0034](adr/0034-mobile-import-and-relationship-history.md) and [acceptance](PHASE_8D_ACCEPTANCE.md).

## Connected file and workflow contract

User gesture → official DocumentPicker57.0.3 → explicit source IANA timezone →
explicit Upload → generated multipart POST → formal Job inspect → explicit
self/person/system/ignore PUTs → owned Relationship PUT → server Ready →
Finalize → formal receipt → separate History. Uses8B auth/transport/resources and
8C epoch/owner guards, existing theme/ImportStep/speaker controls. No local parser,
second token store, SQL connection or imported-analysis workflow.

Only .md/.markdown containing actual `wechat_markdown_v1` is offered. Client
extension/size100MiB is a precheck; server may configure less and validates bytes.
Shows name/bytes/original MIME and source format independently. Source timezone
defaults visibly to Asia/Shanghai and is explicitly editable; it describes file
timestamps rather than phone timezone or UTC storage. Picker cancellation,
reselection, read/cache failures and explicit local cancel are distinct. The
[official Web cancel caveat](https://docs.expo.dev/versions/v57.0.0/sdk/document-picker/)
means a browser may not resolve its picker promise; local cancel invalidates it
and releases any later selection. Choosing never automatically uploads.

SDK57 Android DocumentPicker's automatic copy uses host `context.cacheDir`,
which differs from Expo Go's experience-scoped `Paths.cache`; FileSystem rejects
that host path. Android therefore uses `copyToCacheDirectory=false` and the
user-granted content URI, immediately copying it with FileSystem57.0.7 into a
UUID-named owned cache File before returning selected state. iOS retains the
official automatic-copy setting (not device-tested here). Only the owned copy
is released; provider originals are never deleted. Grant/read/copy failures
fail closed, with no URI-as-text upload. FileSystem File is the binary body.
A disappeared/size-changed cache file
requires reselection. Web uses actual File with `base64=false`. The narrow
generated body serializer supplies FormData because OpenAPI binary currently
generates string; its placeholder is never sent. Fetch owns Content-Type/boundary.
[Official File/FormData support](https://docs.expo.dev/versions/v57.0.0/sdk/filesystem/)
and installed Expo source confirm bounded byte-buffer conversion on native:
no base64, percentage animation, resumable upload or streaming-memory claim.

State is idle/selecting/selected/uploading/job_created/failed/unknown_outcome/
cancelled. Upload says “正在上传和解析”, without fabricated progress. Upload has
a120-second timeout through response-body read. No recovery-by-operation-ID
endpoint exists; a lost201 before Job ID is unknown_upload_outcome, retains
selection summary and blocks repeat Upload. Only explicit “主动开始新导入” resets
it, with a visible warning that another Job may be created. This is distinct
from finalize replay/exact-dataset idempotency.

Successful upload is followed by inspect. Display only public Job counts,
historical UTC range/source zone, exact raw labels, format/parser/schema versions,
revision/artifact/status/readiness, possible duplicate hint and warning counts.
Issue codes are at most20 distinct samples, with truncated count; not a full
report. “我” starts unbound. Person options come from owned resource pages and
explicit resource creation. No label matching assigns identity.

Speaker/Relationship/finalize use current expected_revision. Ready and cancel
have no revision body. Conflict or uncertain binding inspect the original Job,
clear confirmations and require user submission. Relationship choice clears all
speaker confirmations; users return to submit them again. Readiness issues are
shown verbatim with one-to-one explanation, including unsupported group binding.
System/ignore choices are explicit. Finalize requires current server-ready and
explicit identities/relation. The server still authorizes and rechecks everything.

Full receipt has actual status/Job/dataset/relationship/counts/new rows/time bounds/
completion time. An imported inspect has only a summary, shown as imported_summary
and “inspect 摘要不提供” for absent new-row count. Explicit original-Job replay
retrieves a full receipt. A different exact duplicate can return the original
dataset while its own Job remains ready; cancelling that Job does not remove
the original dataset. No content-based deduplication. Completion says records
can be viewed in History and explicitly says no AI analysis was run.

Client Stop, route blur/background and AbortSignal never claim server cancellation.
Only formal cancel/inspect can confirm cancelled. Unknown finalize/cancel use
known Job inspect first; controlled same-Job finalize retry retains its revision.
Imported/cancelled/expired source and server400/401/404/409/413/415/422/503 have safe
messages. Raw exceptions/response bodies are not surfaced. Native picker activity
may change AppState; its epoch-guarded result survives that change. Foreground
checks credential expiry and inspects a known Job. Route changes clear scope;
return within a credential session re-inspects the retained Job. Process restart
has no durable client Job store; “读取已有 Job（不上传）” accepts a known UUID
and reads owned state without re-upload. Unknown IDs/foreign scope fail closed.
Logout/token replacement clears file summaries, labels/Jobs/receipts and aborts
stale requests. Cached copies are released on success/reselect/leave/reset/logout;
this is not a promise of immediate backup or OS-cache erasure.

## Android native import reproduction

1. Confirm actual device/AVD in `adb devices`; use SDK57-compatible Expo Go.
   Start the existing real development FastAPI/PostgreSQL and acquire a short
   development credential using dev_auth_cli.py; keep signing config server-only.
2. Configure explicit local networking:

   ```powershell
   adb reverse tcp:8000 tcp:8000
   adb reverse tcp:8081 tcp:8081
   $env:EXPO_PUBLIC_API_BASE_URL='http://127.0.0.1:8000'
   pnpm --filter @goutou/mobile exec expo start --lan --port 8081 --clear
   # Expo Go: exp://127.0.0.1:8081; --lan ensures IPv4 on this Windows host.
   ```

3. Put only anonymous synthetic Markdown in device Downloads (e.g. the versioned
   server test fixture). Settings → Connected developer credential → resources →
   explicitly create Person/Relationship → Import. Do not dump/screenshot token entry.
4. Open native picker, cancel once, re-open and select file from Android Files.
   Check displayed name/size/MIME, confirm historical source timezone, upload.
   Confirm actual persisted Job/inventory/revision, not just a local selected state.
5. Explicitly submit every speaker and real Person UUID, choose/confirm compatible
   Relationship, ask server ready, finalize and check formal receipt/DB counts.
   Return to verify original Job after background; do not automatically re-upload.
6. Open formal Relationship History, scroll/load More/refresh, inspect original
   timestamp/source zone/provenance. Switch relationships and AI Conversation;
   imported Person must never become assistant. Back must work.
7. Background/foreground before and after credential expiry; logout and connect
   another owner. Previous filename/labels/Job/history/cursor must be gone.
   Verify Agent Message and Memory counts unchanged by import.

Actual2026-10-10 native evidence: Pixel_10/Android17/API37/Expo Go57.0.9,
SDK57, Metro8082/FastAPI8021 via adb reverse and real PostgreSQL16.15.
Downloads provider selection/cancel/reselect and granted URI→owned File→real
multipart passed. Native explicit self/Person UUID/Relationship, ready/finalize
and receipt passed:1,001 new RelationshipMessages,Agent0,Memory0,active artifact0.
Formal native History showed ready/100. ANDROID NATIVE IMPORT CORE: PASS.
Native More100→200, full scroll/Back/foreground/OwnerB/fault matrix remain
NOT RUN to completion; a paging attempt reached credential expiry, so no native
200-record claim is made. Editable-Job expiry did return Settings and clear
visible scope/source. A development reload stall required Metro restart, and
automated flings produced a VirtualizedList slow-update warning. Step changes
can leave the viewport near the bottom; scroll upward to the next step's controls.
See the full [8D report](PHASE_8D_ACCEPTANCE.md). Web/export/Doctor do not replace
device proof; whole Phase8 final acceptance still needs the remaining native matrix.

## Historical Phase 7C Demo

This is an anonymous local Demo on the existing Expo Router/theme/provider.
There is no file picker, local parser, upload, ImportJob, database message,
Agent request or analysis execution. File selection, formal finalize and
analysis buttons are disabled. The page states **本地演示 · 未连接服务器**
and **真实文件上传将在后续版本接入**.

## Contracts and workflow

`src/contracts/import.ts` defines ImportWizardViewModel, source summary,
speaker inventory, discriminated SpeakerBindingDraft, RelationshipBindingDraft,
ImportPresentationState and ImportReadinessViewModel. These are UI contracts,
not copies of SQLAlchemy objects or authoritative backend statuses.
`ShellDataSource.readImport(kind)` supplies fresh synthetic pair/group/empty
templates from the data layer. Screens do not import fixtures.

Five explicit steps are source → speakers → relationship → readiness → result.
Next/Back, return-to-edit and Reset Demo operate on route-local React state.
Source starts unloaded; the separate **体验导入流程（演示数据）** action loads
only metadata. Group and empty sample actions exercise those paths. Empty sources
block Next. Phase 7D also blocks Next until every speaker is explicitly handled,
exactly one self/selected Person exists, and the relationship step is confirmed.
Intermediate errors remain visible at their own step; group and final compatibility
checks cannot be bypassed. There are no timers, automatic advances or simulated server receipts.
Readiness must pass before the result step; no enabled formal-import action exists.

The summary includes source format, message/speaker counts, first/last historical
timestamps, source timezone, warning explanation and a possible-duplicate hint.
Dates are fixed fixture dates, never the current clock. A warning is not a fatal
parser error; a duplicate hint does not mean content deduplication.

Each speaker preserves raw nickname, Emoji, source label and count. All bindings
start absent/unbound, including `我`. Users explicitly choose self/person/system/
ignore; choosing person additionally requires an explicit Person ID selection.
Person choices come from supplied relationships, never nickname inference.

Readiness checks one self, one selected Person, no unbound speakers, explicitly
confirmed existing Relationship and Person compatibility. More than two explicitly
bound humans gives **当前版本的一对一关系导入不支持多人群聊**. Extra labels
must be explicitly system/ignore, as in the Phase 5B contract; they are never
silently merged into the primary person. Local readiness is not server `ready`.

## Scope, lifetime and failures

Relationship entry passes `relationshipId`. Missing or repeated/ambiguous scope
parameters fail closed with **关系不可用**; no fallback to A/B occurs. A known
incoming ID preselects the relationship draft but does not confirm it or bind any
Person. Choosing another relationship clears all speaker bindings/confirmation
and returns to the speaker step. Changing the route scope remounts the whole
wizard, removing its source, bindings, step and preview. Reset, route unmount,
reload and app restart clear the demo. Stack push/back retains a still-mounted
wizard. Page loading/error/empty previews use the existing StatePreview/Retry seam.

Result reports **演示预检已完成，真实导入将在连接服务器后启用** and offers
scoped History/Chat navigation. It never reports uploaded/imported/analyzed.
Analysis overview explicitly labels independent synthetic fact/provenance,
tentative inference/alternative and unknown teaching content. It is not analysis
of the source or user input; no automatic Memory save exists.

## Phase 8 adapter coordination

The future authoritative flow remains the Phase 5D single multipart upload,
server parser/Job view, explicit speaker/relationship mutations with revision,
server ready and server finalize. Map sampled warning codes and artifact/revision/
duplicate metadata through an adapter; do not reuse local `loaded` or `ready`
as wire success. Real Person/Relationship resource acquisition also needs an
owner-scoped public contract. Imported-history analysis is not an existing
finalize side effect. Current public Agent answer DTO lacks full structured
FIU/Profile; coordinate a public mapping before showing real analysis fields.
No server contract changed in this phase.

Jest tests cover navigation, raw labels, explicit bindings, incompatible scopes,
unbound/group/empty/missing paths, result boundary, reset and source substitution.
Real Expo Web validates the wizard at 320/360/412px in both themes, with zero
business requests. Historical 7C Android native smoke and TalkBack: **NOT RUN**.
The user subsequently reported manual Android smoke passed. Phase 7D validates
the full Web journey and documents incomplete Codex native attempts without
changing that history. See [7C acceptance](PHASE_7C_ACCEPTANCE.md) and
[final acceptance](PHASE_7_FINAL_ACCEPTANCE.md).
