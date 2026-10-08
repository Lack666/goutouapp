# Import / Analysis UI — Phase 7C

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
block Next. There are no timers, automatic advances or simulated server receipts.
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
business requests. Android native smoke and TalkBack: **NOT RUN**. Phase 7D
still owns overall MVP integration/final acceptance. See [acceptance](PHASE_7C_ACCEPTANCE.md).
