# Settings / Memory UI — Phase 7C

All Memory controls are **local UI demonstrations** using anonymous synthetic
ViewModels. No Memory API, authentication, saved preference, challenge, receipt
or database mutation exists in Mobile. Feedback says **本地演示状态已更新**.

## Contracts and consent semantics

`src/contracts/settings.ts` defines MemoryControlViewModel, MemoryRecordViewModel,
MemoryUndoPreviewViewModel, MemoryDeleteConfirmationViewModel and RetentionSummary-
ViewModel. `ShellDataSource.readSettings()` injects fresh read-only templates.
These retain Phase 6 semantics without duplicating ORM tables or inventing wire IDs.

Consent and pause are separate dimensions. Grant enables consent while preserving
pause; revoke disables consent and sets pause, retaining all inspectable records.
Pause blocks recall/write; resume clears pause only if consent is enabled, never
grants revoked consent. Effective-switch preview is consent AND not paused. This
is display state and does not invoke the server or actually recall/store anything.

Inspect expands summaries, user/object/relationship subject and structured scope,
historical creation/expiry and active/expired state. Fixture states are an explicit
synthetic snapshot for 2026-10-08, not live server expiry calculations. Inspection
works while revoked/paused. It warns that historical information may be outdated;
no raw evidence, operation internals or hidden reasoning is exposed.

## Undo and delete boundaries

Undo Preview displays the latest reversible insertion sample, explains Expected
Operation matching and Guarded Undo, and disables formal execution. There is no
fabricated operation ID/receipt. Real operation ID plus operation_key must come
from the authoritative server. Expired/stale targets never fall back to an older
record; Undo cannot restore hard deletion.

Delete-one starts from the inspected record; delete-person names a structured
Person scope; delete-all covers all demo Memory including expired rows. Read-only
confirmation displays scope, affected count and consequences. For all, users
explicitly choose preserving current consent or revoking/pausing after deletion.
That selection is required before local acknowledgement. Changing target/choice
resets acknowledgement. Cancel dismisses the preview. Formal delete is always
disabled, even after acknowledgement. No sample or server record is removed.
The `review/acknowledged` UI stage is not server `confirm=true`, a challenge, or
authorization. Phase 8 must prepare a real server-owned challenge, display its
snapshot/count/expiry and execute with operation_key, receiving a durable receipt.

The disclosure limits deletion to scoped primary Memory and associated undo
history, excludes relationship entities, AI chats and imported history, and explains
backup/log/metadata boundaries. It does not promise erasure of all mentions of a person.

## Retention, appearance, lifetime and failures

Display **示例保留策略：180 天**, explicitly deferring real duration to server
policy. Expiry immediately stops new recall; physical cleanup may happen later.
Primary-store deletion does not instantly clear backups/logs; necessary operation
metadata has its own policy. The UI does not offer a server retention editor.

Existing system/light/dark theme remains root-session scoped across pages, resets
on restart and truthfully says so. Version 0.1.0, local Demo and Backend not
connected are displayed, with no fake login/account state. Consent/inspection/
undo/delete previews live only in the mounted Settings controller; reset/unmount/
reload/restart clears them. Loading/error/empty/retry use the shared presentation
seam. Theme remains independent of Memory reset. Feedback supports polite live
announcements; selected/disabled buttons expose semantic state and 48-unit targets.

Phase 8 maps authenticated Phase 6 control/inspect/policy/undo/challenge/receipt DTOs
through async adapters with owner/scope validation remaining server-side. No API,
client, JWT/SecureStore, persistence or mutation is started here. Jest/browser tests
cover controls, inspect/expiry, guarded boundaries, all deletion scopes/choices,
reset, substitution, themes, state errors and zero business network/log calls.
Historical 7C Android native smoke/TalkBack: **NOT RUN**. Phase 7D adds complete
cross-page/reset/reload/confirmation-choice regression; its report distinguishes
the user's later manual smoke from Codex's incomplete native attempts.
See [final acceptance](PHASE_7_FINAL_ACCEPTANCE.md).
See [acceptance](PHASE_7C_ACCEPTANCE.md), [Memory API](MEMORY_API.md),
[deletion](MEMORY_DELETION.md) and [retention](MEMORY_RETENTION.md).
