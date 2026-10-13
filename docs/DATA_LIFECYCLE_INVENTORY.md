# Data lifecycle inventory — current Phase9E

Current schema:19 application tables, migration20261013_02. The dated9D inventory
below describes the original17-table baseline. Current overrides are authoritative:

- Conversation/Agent Message: guarded exact Conversation deletion physically removes
  Messages, hides tombstone from owned lists/detail/history/run access, preserves
  Conversation UUID/scope and AgentRun ID/status/key/fingerprint. Run message pointers
  become null; outcome warnings/memory status cleared. No running/unresolved run force.
- RelationshipMessage/Dataset: guarded exact canonical imported Job deletion removes
  formal occurrences and canonical speakers/bindings, keeps Job dedup/import metadata
  and deleted_at. Imported status/unique index preserves the same-transcript fence.
  Cancel remains unfinished-Job-only. Historical inspect is not proof of live messages.
- Erasure confirmations (`erasure_confirmations`): signed owner, exact domain/target/
  Relationship/snapshot/counts, five-minute validity; expiry+24h bounded cleanup.
  RESTRICT owner FK; no private body; all invalidated during controlled recovery.
- Erasure receipts (`erasure_receipts`): signed successful transaction, unique owner/key,
  fingerprint/challenge/domain/target/scope/count/time. RESTRICT owner FK; no private
  body; durable owner lifetime fence, no time cleanup. Current receipts replace old
  backup state after integrity comparison. Missing history blocks restore release.
- Person/Relationship/account: no self-service erase, including empty resources;
  audited RESTRICT dependencies and UUID retry contracts prohibit inferred cascade.
  Account lifecycle/identity/all-copy erasure remains formally unfinished.
- Every table is in logical DB backups; erasure affects current primary only. Old
  dumps remain private/quarantined until exact target reconciliation. Raw artifacts
  stay on existing9D physical cleanup/retry/accounting path, separate from history.
- Mobile cache: existing History open/focus/refresh loads server truth; leave/logout/
  epoch clears state. App has no chat erasure controller; disclosure added to Settings
  and History. Generated39-operation client/allowlisted errors are not a mobile flow.

All ten capability dimensions are in DATA_DELETION_MATRIX.json; execution evidence
is PHASE_9E_ACCEPTANCE/MATRIX and test_erasure.py plus all retained tests.

## Historical9D baseline inventory

All entries describe actual repository storage. Sensitivity: restricted means
private relationship/authorization data; confidential means pseudonymous metadata.
DB means server PostgreSQL (17 application tables, migrated through20261013_01).
Every DB entry enters a full logical DB backup, including indexes/FKs and deletion
metadata. Neither a primary delete nor expiry rewrites an older backup. Evidence
references identify tests; execution authority is PHASE_9D_ACCEPTANCE/MATRIX.

## User / development identity

- Content/sensitivity: UUID/timestamps, confidential; signed subject maps to User.
- Owner/creation/location: development bootstrap or trusted repository; `users`.
- Relations: Persons, Relationships, Conversations, runs, imports, Memory and receipts.
- Retention/deletion/trigger: owner lifetime; no public account erasure. RESTRICT
  links prevent assuming full cascade; raw DB privileges are not a product API.
- Retained metadata/copies: all rows retained; short JWT lives in client SecureStore
  or volatile Web session. DB backup includes User, not a secret signing key.
- Evidence: test_auth_jwt.py, test_authorization_security.py, test_resource_api.py.

## Person

- Content/sensitivity: display name/UUID/owner/times, restricted.
- Owner/creation/location: signed subject, resource service POST; `persons`.
- Relations: Relationship, scoped Memory, import speaker/message references.
- Retention/deletion/trigger: indefinite; Person delete API absent. Delete-person
  Memory removes only Memory, preserving the Person and other Persons.
- Retained metadata/copies: entire row, DB backup; client read models are session scoped.
- Evidence: test_resource_api.py, test_memory_mutation.py, test_phase6_e2e.py.

## Relationship

- Content/sensitivity: structured Person/type/status/owner, restricted.
- Owner/creation/location: signed POST; `relationships`, composite owner/Person FK.
- Relations: Conversations, Memory, Jobs, external messages.
- Retention/deletion/trigger: indefinite; no public delete; RESTRICT references.
- Retained metadata/copies: entire row, DB backup, session read models.
- Evidence: test_resource_api.py, test_import_merge.py, test_database.py.

## Conversation

- Content/sensitivity: UUID/owner/optional Relationship/times, confidential.
- Owner/creation/location: signed POST; `conversations`.
- Relations: Messages CASCADE but AgentRun RESTRICT; not a complete erasure cascade.
- Retention/deletion/trigger: indefinite; no Conversation delete API.
- Retained metadata/copies: entire row; DB backup and client history models.
- Evidence: test_resource_api.py, test_agent_service.py, test_phase6_e2e.py.

## AgentRun / Agent operation metadata

- Content/sensitivity: status/key/fingerprint/message IDs/public outcome, restricted
  metadata (caller keys are untrusted; never logged).
- Owner/creation/location: signed AgentService, `agent_runs`.
- Relations: owned Conversation; user/assistant Message pointers SET NULL.
- Retention/deletion/trigger: indefinite; no Agent history/run deletion or TTL.
- Retained metadata/copies: key fence lasts with row; full DB backup. After restore,
  interrupted runs fail conservatively; operations after recovery point are lost.
  Missing current issued Agent key/run fences block restore release; newer runs
  are not synthesized. See9D-01 and test_backup_restore.py.
- Evidence: test_phase4_idempotency.py, test_agent_stream_disconnect.py.

## Agent Message

- Content/sensitivity: private input/public assistant answer/tool content, restricted.
- Owner/creation/location: inherited through Conversation; AgentService, `messages`.
- Relations: Conversation CASCADE; run pointers SET NULL. Hidden reasoning not saved.
- Retention/deletion/trigger: indefinite; no public message/history delete.
- Retained metadata/copies: full message, DB backup, bounded client history/context.
- Evidence: test_agent_service.py, test_resource_api.py, test_phase6_e2e.py.

## Imported RelationshipMessage / dataset

- Content/sensitivity: private external chat, speaker label, time/provenance, restricted.
- Owner/creation/location: signed finalize, explicit bindings; `relationship_messages`.
- Relations: owner/Job/Relationship/Person/speaker composite FKs; occurrences use
  Job + source index. Distinct text repetitions are preserved.
- Retention/deletion/trigger: indefinite; no message/dataset deletion API. Cancel
  cannot erase imported data. Duplicate exact transcript in same owned Relationship
  reuses first dataset; other Relationships have independent imports.
- Retained metadata/copies: full formal rows and original Job receipt; DB backup;
  raw Artifact deleted separately. Never fed to Agent/Memory/provider automatically.
- Evidence: test_import_merge.py, test_import_api.py, test_phase6_e2e.py.

## ImportJob / speaker bindings / import receipt

- Content/sensitivity: fingerprints/counts/time bounds plus raw labels/bindings,
  restricted metadata; does not contain chat bodies.
- Owner/creation/location: signed upload or trusted parser service;
  `chat_import_jobs`, `chat_import_speakers`.
- Relations: unique owner/Artifact, Relationship; formal messages RESTRICT Job removal.
- Retention/deletion/trigger: metadata indefinite; cancel unfinished Job through signed
  service; expiry cancels unfinished artifact-backed Jobs. Imported cancel rejected.
- Retained metadata/copies: bindings/counts/receipt retained, full DB backup;
  parser TEMP staging drops on commit/rollback/worker death.
- Evidence: test_import_jobs.py, test_import_merge.py, test_import_api.py.

## Import Artifact / multipart spool / crash residuals

- Content/sensitivity: original transcript or partial bytes, restricted.
- Owner/creation/location: verified upload admission; configured private
  CHAT_IMPORT_ARTIFACT_ROOT (`.cache/import-artifacts` default), random .part/.bin;
  `chat_import_artifacts` contains owner/key/hash/size/state/expiry only. Framework
  spools may roll to OS temporary storage; no raw-file HTTP read endpoint exists.
- Relations: Job and live OS-fenced upload reservation. Caller filename discarded.
- Retention/deletion/trigger:72h default; finalize/cancel immediately attempts unlink;
  failed upload aborts source; failed merge keeps retryable source until TTL. Old
  orphan grace1h. Active pre-registration worker keys are protected.
- Retained metadata/copies: DB artifact row/Job receipt retained; source excluded from
  controlled backup. Multipart handles close per request; OS process death releases
  anonymous spool handles. Physical deletion and accounted quota are distinct from state.
- Evidence: test_upload_security.py, test_resource_admission.py, test_data_lifecycle.py.

## MemoryRecord

- Content/sensitivity: compact consented content/evidence/scope, restricted.
- Owner/creation/location: explicit consent, MemoryService/store; `memory_records`.
- Relations: structured Person/Relationship owner FKs; undo targets CASCADE.
- Retention/deletion/trigger: default180 creation days; recall/default list exclude
  exact expiry immediately; owned direct inspection possible until physical cleanup.
  Guarded delete-one/person/all and Undo or retention physically remove primary rows.
- Retained metadata/copies: mutation IDs/counts retained, not content. DB backup
  retains older content until backup rotation; in-flight/provider transmissions
  cannot be withdrawn. Restore exact owner/record survival is checked before serving.
- Evidence: test_memory_retention.py, test_memory_mutation.py, test_backup_restore.py.

## Memory consent / pause

- Content/sensitivity: durable authorization booleans/time, confidential.
- Owner/creation/location: signed controls or explicit Agent consent; `memory_controls`.
- Relations: owner CASCADE; shared by Agent and API, owner-row serialized.
- Retention/deletion/trigger: owner lifetime; revoke/pause blocks recall/write, keeps
  records; confirmed delete-all can atomically revoke. No time cleanup.
- Retained metadata/copies: entire controls, DB backup; controlled restore uses current
  authoritative controls, default disabled when no current row, never old consent.
- Evidence: test_memory_control.py, test_phase6_e2e.py, test_backup_restore.py.

## Undo operations

- Content/sensitivity: owner/record ID/times, confidential; no content copy.
- Owner/creation/location: authorized new Memory insert; `memory_operations`.
- Relations: owner/record FK CASCADE, maximum20 per owner.
- Retention/deletion/trigger: bounded pruning, target deletion/expiry cleanup;
  expired latest Undo rejected, no fallback. Restore replaces with current valid targets.
- Retained metadata/copies: formal mutation receipt after guarded Undo; DB backup.
- Evidence: test_memory_undo.py, test_memory_mutation.py, test_backup_restore.py.

## Deletion confirmation

- Content/sensitivity: owner/action/target/snapshot hash/count/revoke flag, confidential.
- Owner/creation/location: signed prepare; `memory_confirmations`.
- Relations: owner CASCADE, receipt references challenge UUID without retention FK.
- Retention/deletion/trigger:5min valid; consumed/stale fail closed; cleanup after
  expiry+24h default grace. Restored challenges are all invalidated before release.
- Retained metadata/copies: grace-period metadata only; DB backup.
- Evidence: test_memory_mutation.py, test_memory_retention.py, test_backup_restore.py.

## Mutation receipt

- Content/sensitivity: owner/key/fingerprint/action/IDs/counts/time, confidential.
- Owner/creation/location: successful guarded transaction; `memory_mutations`.
- Relations: owner CASCADE only; no saved content nor exact delete-all/person ID set.
- Retention/deletion/trigger: owner lifetime, no time cleanup; owner GET receipt;
  original-key replay even after challenge cleanup. No public metadata deletion.
- Retained metadata/copies: entire receipt; DB backup; current receipts restored
  from authoritative primary to prevent old-key new execution.
- Evidence: test_memory_mutation.py, test_memory_retention.py, test_backup_restore.py.

## Shared admission state / reservation / fence

- Content/sensitivity: hashed root/policy, windows, owner/file attribution, confidential.
- Owner/creation/location: server-trusted policy + signed owner;
  `resource_admission_states`, `upload_reservations`, private sibling fence directory.
- Relations: OS file lock proves worker liveness; actual residual bytes retain charges.
- Retention/deletion/trigger: inactive reservation rows reconciled/pruned by inventory;
  dead worker slots reclaimed; live locks never stolen by time. Windows reset by minute.
- Retained metadata/copies: actual retained file attribution; DB backup includes rows,
  excludes fence files. Restore discards admission metadata for a new empty root.
- Evidence: test_resource_admission.py, test_data_lifecycle.py, test_backup_restore.py.

## Application logs / scheduler / operator reports

- Content/sensitivity: fixed messages, aggregate counts/status only, confidential.
- Owner/creation/location: server stdout, maintenance CLI count-only stdout, OS collector
  owned by operator. No persistent application logging table.
- Relations: no tokens, exceptions, chat/Memory/body/password/Owner labels permitted.
- Retention/deletion/trigger: production proposed7d rotation NOT DEPLOYED; developer
  redirected logs require manual removal; no user log-deletion endpoint.
- Retained metadata/copies: collector/copy inventory operator responsibility; excluded
  from DB backup; receipts have their separate durable policy.
- Evidence: test_privacy_logging.py, test_data_lifecycle.py, test_backup_restore.py.

## Test evidence / local cache

- Content/sensitivity: synthetic test statuses/IDs/counts/paths, confidential; no real chats.
- Owner/creation/location: developer-owned `.cache`, acceptance `docs/evidence/phase*`.
- Relations: hash matrices bind immutable executions; failures remain distinguishable.
- Retention/deletion/trigger: committed regression evidence retained; temporary synthetic
  dump/DB/file trees deleted by fixture finalizers; local caches have no scheduler.
- Retained metadata/copies: log/exit/hash summaries only committed, no dump/raw source/JWT.
  Git copies subject to repository access; DB backup excludes evidence.
- Evidence: audit_evidence_privacy.py, test_security_tooling.py, test_backup_restore.py.

## Database backup

- Content/sensitivity: entire PostgreSQL content including private chat/Memory, restricted.
- Owner/creation/location: operator-only pg_dump; controlled drill uses temporary isolated
  synthetic archive. No backup HTTP API and no production backup platform.
- Relations: roles/global settings/WAL/artifact files/signing keys excluded from logical DB dump.
- Retention/deletion/trigger: synthetic archive removed in finally; future encrypted daily
  backups maximum35d, verified daily rotation NOT DEPLOYED. Main deletion leaves old copies.
- Retained metadata/copies: count-only drill evidence; current-primary reconciliation
  requires complete trusted source. Without source/keys keep recovery quarantined.
- Evidence: test_backup_restore.py and BACKUP_RESTORE_POLICY.

## Future provider copies

- Content/sensitivity: possible transmitted context/chat/Memory, restricted.
- Owner/creation/location: explicit configured provider invocation;9D uses keyless Mock only.
- Relations: completed outbound context cannot be erased by primary SQL deletion.
- Retention/deletion/trigger: no provider erasure contract/deployment in9D; vendor policy,
  region, retention and erasure must be approved before real integration.
- Retained metadata/copies: unknown vendor copies; excluded from local backup, cannot claim erased.
- Evidence: import/Agent separation and LLM Mock tests; provider lifecycle NOT VERIFIED.
