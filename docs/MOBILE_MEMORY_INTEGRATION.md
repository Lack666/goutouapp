# Connected Memory integration — Phase 8E

Connected Settings uses the existing DevelopmentSession, generated client and
ApiTransport. FastAPI MemoryControlService/MemoryMutationService and PostgreSQL
remain authoritative. No Mobile MemoryStore, consent database, receipt table,
JWT manager, confirmation token or local destructive journal is introduced.
The Phase 7 Settings Demo remains a separate local demonstration.
The decision is recorded in [ADR0035](adr/0035-mobile-memory-guards-and-session-recovery.md).

## Public contract audit

The existing generated 36-operation client already includes all 13 operations.
OpenAPI and generated output remain unchanged; root verifies both for drift.
The transport explicitly enables Memory only in Connected composition, checks
the exact method/path family, uses the current JWT, omits cookies, rejects
redirects, enforces timeout/cancellation and rejects late epoch responses.
Public error codes are allowlisted; raw messages and validation bodies are not
stored or shown. A 401 invalidates the shared session.

- GET `/api/v1/memory/control`: independent consent, pause, effective read/write,
  nullable aware update time. POST `/memory/consent` requires `enabled`; POST
  `/memory/pause` and `/memory/resume` have no body. All return MemoryControlView.
- GET `/api/v1/memories`: owned person_id/relationship_id, limit 1–50, opaque
  cursor; MemoryListResult supplies active records and real policy/notices.
  GET `/memories/{memory_id}` returns owned detail, including expired records
  until physical cleanup. There is no include_expired query parameter.
- GET `/memory/undo/preview`: available and nullable latest operation ID, memory
  ID, type, scope and created time. It is owner-global, not scoped to a Person.
  There is no preview expiry field. POST `/memory/undo` requires the preview's
  expected_operation_id and the immutable operation_key.
- POST `/memory/deletions/one/prepare`: actual record memory_id and its nullable
  person_id/relationship_id. POST `/person/prepare`: owned person_id. POST
  `/all/prepare`: explicit revoke_consent_after_delete boolean, with no default
  client choice. Prepare returns MemoryConfirmationChallenge.
- POST `/memory/deletions/{confirmation_id}/execute`: operation_key only; action,
  target, scope, count and consent choice cannot be overridden at execution.
- GET `/memory/mutations/{mutation_id}`: owned durable MemoryMutationReceipt.
  All these Memory operations return 200 on success. Server 400/422 validation,
  owner-neutral 404, 409 guard conflicts and 503 persistence failures stay errors.

Adapters project generated DTOs into public ConnectedMemory ViewModels. They
reuse the existing Settings control and compatible summary/date/state contracts;
Demo-only provenance and non-executable preview flags are not relabelled as server
data. The final inheritance alignment changes types only, not runtime behavior.
Records show compact saved fact, ID/type/subject, scope, public source/provenance summary,
creation/update/expiry/state, retention and historical notice. UI never consumes
ORM fields, raw evidence, snapshot hashes, token-like confirmation secrets or
receipt operation_key. Type remains the server's string rather than invented UI
classification. Receipt target_id for Undo is the Memory ID, not operation ID.

## Controls and inspection

Grant/revoke/pause/resume are explicit buttons; no local optimistic authority.
Every submission is followed by GET control. A response lost after commit is
reported as uncertain and current authoritative controls are re-inspected. If
reinspection also fails, control stays unconfirmed instead of restoring an old
toggle. No automatic POST retry occurs.

Revoke keeps existing records and pauses. Grant preserves pause. Resume without
consent never grants. Pause prevents later recall/final persistence but cannot
retract context already loaded in an in-flight run. Existing owner-row locking
and final persistence recheck enforce the latter write boundary.

The owned selectors reuse ResourceController's bounded Person/Relationship
pages and explicit More/Refresh. Selecting Person includes all its relationships;
selecting Relationship supplies matching Person and Relationship IDs. User scope
lists all own records, including user-level records. Server validates ownership
and scope on every request. Scope change cancels old reads, clears detail,
records/cursor, preview/challenge and keyed lookup inputs. Active/unknown mutation
locks scope changes until safe recovery; it never silently discards a retry key.

Memory pages request 50 records and retain at most 200 per window. Opaque cursor
and IDs come from the server; records merge by ID, never by content. Refresh
starts a new window. Empty/error/loading and retry are explicit; Connected never
falls back to synthetic records. Known-ID detail remains owner/scope checked.

UI displays server retention_policy_summary even on an empty list. The E2E
fixture configures 37 days to prove the client does not assume 180. Expired
records are excluded from default list/recall before physical cleanup; known-ID
detail may show expired. Stored expiry is not renewed by recall. Historical
information may be inaccurate now; it is not fresh user evidence.

## Guarded mutation state and recovery

States: idle, preparing, awaiting_user_confirmation, executing, completed,
stale_or_conflict, expired, failed, unknown_outcome. Preparation never executes.
Undo reads fresh global preview and displays the operation and Memory IDs, type,
scope and timestamp before explicit confirmation. If latest belongs outside the
selected scope, UI refuses to substitute an older operation. Server stale_undo
shows “操作目标已发生变化，请重新检查。” with no automatic fallback.

Delete-one prepares from an inspected/listed actual record and its real scope.
Delete-person uses structured Person scope across relationships, not text search.
Delete-all requires the user to explicitly retain or revoke consent. Changing
that choice invalidates the old challenge and requires a new prepare.
UI reviews actual challenge ID, action, target, scope, expected_count, consent
choice, issued_at, expires_at and deletion_scope_notice. A timer disables local
execution at expiry; the server always rechecks expiry, consumption and snapshot.
Stale/expired/consumed/conflicting challenges cannot be bypassed.

At explicit Execute, one random UUID-based key is bound to an immutable request:
Undo expected_operation_id or deletion confirmation_id. Timeout, offline,
background cancellation, malformed response or uncertain 5xx yields unknown
outcome, no synthetic success. New prepares and scope/control changes are disabled.
Refresh reads authority without resolving the mutation merely from disappearing
records. Safe Retry sends the same key/path/body; it never obtains a replacement
challenge or uses the new latest Undo. Server receipt replay precedes expiry
checks and cannot delete later records. Confirmed receipts survive a failed
optional replay/lookup; those failures are still shown.

Receipts show mutation ID, action/status, affected_count, target/scope,
undone_memory_id, performed_at, replayed, primary_store_only and server notice.
GET inspection is a receipt read with replayed=false; same-key execution replay
returns replayed=true. A known matching receipt can resolve unknown outcome.
Foreign-owner receipt IDs are 404. No client receipt is reconstructed from a list.

Recovery is deliberately session-memory only. Blur/background cancels reads,
clears private record/detail/confirmation UI, invalidates unexecuted preparation,
retains original submitted attempt, and never automatically re-executes.
Foreground performs GET refresh only. Logout/expiry/owner epoch reset clears
scope, control, records, attempts, receipts and lookup inputs. App restart loses
the key: UI explicitly says the lost operation cannot be safely auto-retried;
inspect authority or a known receipt ID. No durable journal stores Memory text,
private chat, JWT, key or confirmation metadata.

Primary deletion removes scoped Memory and its Undo history, including expired
primary records. Person/Relationship/Conversation, Agent messages and imported
RelationshipMessages remain. Confirmation/receipt metadata is retained by policy.
Primary deletion is not instantaneous backup/log/provider erasure and is not
deletion of all personal data. Production scheduling and backup restore replay
remain undeployed, as documented in Phase 6.

## Chat, verification and native steps

Chat preserves actual memory_status. “前往 Memory 控制与确认” is navigation only;
pending_confirmation never runs grant, Undo or deletion from Chat. No new Agent
reasoning, RAG, import analysis or public FIU/Profile contract is introduced.

Run `pnpm --filter @goutou/mobile run test:memory` and `smoke:memory`.
The smoke config starts real FastAPI on 8022, Chrome/Expo on 8091, a disposable
migrated PostgreSQL database, CLI-signed JWTs and the established Phase6Mock
through AgentService/LangGraph. It uses no auth/service override. Fixture-only
private pipe commands expire known synthetic rows and report counts, not content,
tokens or prompts. Trace/video/screenshots are disabled. Mock transport unit
tests remain distinct from real HTTP and visible browser acceptance.

Native manual procedure when the existing Pixel_10/Expo Go57 environment is online:

1. Check the exact adb device serial with SDK platform-tools `adb devices -l`.
   Before old fixture cleanup, inspect only `/sdcard/Download/phase8d-native-wechat.md`
   and verify it is the documented anonymous 1,001-message fixture. Never delete
   Downloads or an unverified file. If offline, CLEANUP DEFERRED.
2. Start the same Memory fixture using private pipes and GOUTOU_MEMORY_E2E=1;
   keep CLI JWTs out of files, screenshots and logs. Start Expo port8091, set API
   emulator host using the existing network/adb forwarding setup, open Expo Go57.
3. Connected login → Settings grant/resume → owned relationship Conversation →
   synthetic fact through REST and native POST SSE → Memory navigation. Check
   server status, list/detail, 37-day policy and matching PostgreSQL counts.
4. Pause/revoke/regrant/resume; verify no subsequent recall/write while disabled.
   Preview Undo, confirm target, check durable receipt; save new fact and verify
   retry never removes it. Prepare one/Person/all, change consent choice, inspect
   count/expiry, confirm, inspect/replay receipt and verify history is retained.
5. Verify background, timeout/unknown outcome, original-request retry, logout,
   expiry and A→B isolation; check small-screen keyboard and theme layout.

On this run adb had no usable online device. Native Memory E2E is NOT RUN and
cleanup is DEFERRED. Web evidence does not imply native PASS. Carry native and
whole Phase 8 final acceptance to 8F, and stop at 8E.
