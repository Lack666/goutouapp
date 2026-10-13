# Data deletion contract — Phase 9D

Authority is the authenticated signed subject and structured IDs. API absence is
a product gap, not implicit authorization for raw SQL.9D adds no public endpoint,
OpenAPI DTO or client action. Public operation count stays36. Safety/Agent nodes,
frozen knowledge and Memory consent guards are unchanged.

## Actual supported operations

Memory follows Prepare → user Confirm → Execute → durable Receipt. Delete-one
binds exact Memory UUID + Person/Relationship; delete-person binds an owned Person
and its Memory snapshot; delete-all binds the owner's full Memory snapshot and
explicit revoke option. Undo names the preview's latest insertion operation.
Owner lock serializes with saves and controls; challenge expires at5min and a
changed snapshot rejects. Same original key/target replays before challenge lookup.
Reusing a key with another request conflicts. New records after a successful
delete are preserved on retry; HTTP response loss is unknown until known receipt
or same-key replay. Restart reloads authoritative state and never executes an
old delete. The current Mobile has no durable pending outbox.

Memory deletion removes only scoped primary Memory and associated undo targets.
Agent History, imported RelationshipMessages, Person, Relationship, Conversation,
other owners and other Persons remain. Confirmation metadata ages out after
expiry+grace; mutation receipts remain for owner lifetime. The deletion receipt
does not claim all copies have vanished. Saved context already loaded by a run
or delivered to a future provider cannot be retracted.

Import cancel is owner-scoped and Job-serialized; imported/importing Jobs reject
cancel. It cancels only unfinished Job, then attempts its own raw Artifact unlink.
Expiry cancels unfinished artifact-backed Job, prevents finalize and retries raw
unlink. Successful finalize keeps formal imported occurrences and Job receipt,
but removes the raw source. A merge error rolls back formal rows and keeps source
for explicit retry until TTL. A fatal upload creates no Job; leaked sources become
grace-period orphans. Already imported history is never removed by cleanup.

## Dependencies and absent contracts

- Conversation / Agent History / Message delete: **NOT IMPLEMENTED**, future P1
  product privacy prerequisite before a real-data erasure promise. Conversation
  has Messages CASCADE but AgentRun RESTRICT; formal service must resolve both,
  running work, operation keys and client caches under confirmation.
- Imported RelationshipMessage / dataset delete: **NOT IMPLEMENTED**, future P1
  prerequisite before import-history erasure promise. Scope must be owned canonical
  imported Job + Relationship, never body-string matching. Exact same-scope duplicate
  Jobs share the first formal dataset receipt; cancelling a duplicate's private
  source must preserve the canonical dataset. Other Relationships remain independent.
- Relationship delete: **NOT IMPLEMENTED**; Memory/Conversations/Jobs/history have
  RESTRICT references. Future prepare must enumerate all dependencies and require
  explicit confirmation for each enlarged scope, or reject while references exist.
- Person delete: **NOT IMPLEMENTED**; Relationship/import/memory references require
  the same explicit dependent-resource contract. Delete-person Memory is not this API.
- Account data erasure: **NOT IMPLEMENTED**, future P1 product admission prerequisite.
  User has mixed RESTRICT/CASCADE children; deleting User cannot mean full erasure.
  Requires identity revocation, running-work barrier, cache/export/provider policy,
  durable erasure metadata and backup reconciliation. No production account exists.
- Audit/receipt erase: **NOT IMPLEMENTED**; premature key removal can allow old
  requests to execute again. Any bounded policy needs independent durable terminal
  key fencing. Logs/provider/backup erasure are operator/vendor contracts.

Future public deletion APIs require signed owner, exact server challenge/snapshot,
expiry/stale handling, immutable operation_key, atomic durable receipt, cross-resource
enumeration, rollback/crash tests, restore policy, OpenAPI/client implementation
and explicit stage authorization. Nothing in9D silently expands deletion scope.

## Controlled restore semantics

Current primary must remain authoritative and intact. The synthetic-only offline
coordinator freezes its current lifecycle tables while collecting exact surviving
owner/Memory IDs, current controls, valid undo operations and durable receipts.
Restored Memory absent from that set is removed by exact UUID/owner pair. It does
not replay delete-person/all scopes and does not use current textual content.
Current receipts replace older receipt state, preserving original-key replay;
old restored confirmations are invalidated. The backup recovery point determines
which nondeleted records were present: post-backup new records are not recovered.
This loss is reported, not presented as complete disaster recovery.
Current issued Agent operation keys must also exist unchanged on restored AgentRun
rows for restored owners. Missing post-backup run/key/fingerprint fences reject
release; copying newer run/message history is outside this minimum recovery path.
A keyed old request must never become a new execution after restore.

Raw Artifact/fence files are excluded from the drill backup. Restore sets Artifact
metadata deleted and cancels unfinished Jobs; imported formal history/receipts stay.
An empty private restore root must be used. Current admission rows are discarded
for that root; running Agent runs become failed. Restore remains quarantined until
all reconciliation commits and integrity/owner/recall/receipt checks pass. Any failure
keeps it private and the disposable target is dropped. No current primary means
**NO RELEASE**: production disaster recovery needs independently durable exact-ID
journal/WAL, controls and key fences; this implementation cannot invent them.

Evidence: test_memory_mutation.py, test_phase6_e2e.py, test_data_lifecycle.py,
test_backup_restore.py, Mobile connectedMemory/authPrivacy/native8F retained gates.
