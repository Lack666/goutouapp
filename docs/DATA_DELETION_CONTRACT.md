# Data deletion contract — current Phase9H

Signed `/api/v1/lifecycle-erasures` Prepare/Execute/Receipt supports exact Person
and Relationship erasure. Person includes all structurally linked relationships;
Relationship preserves its Person and other relationships. Owner Owned Data uses
the private signed development/test operator command, not account closure. Every
domain requires a five-minute dependency/content snapshot, explicit confirmation,
active owner/domain barriers and immutable key/payload. Changed dependencies need
fresh preparation. Outside/unbound Person speaker references reject widened scope.

AI/import messages, speaker/profile labels, raw artifacts, scoped Memory and Undo
are deleted or scrubbed. UUIDs, Run keys/fingerprints, canonical import dedup hashes,
count-only receipts and timestamps remain for the owner fence lifetime. Owner also
includes general Conversations, unbound imports, controls and inactive reservations;
unknown raw-file attribution blocks preparation. Its terminal tombstone rejects
old local JWT protected reads/writes and UUID recreation. Text mentions and unrelated
same-owner/Owner B domains never expand the exact structured scope.

Unresolved or unproved live writers block deletion. Original-writer completion or
matching OS-proof recovery receipt is required. Raw unlink cannot roll back with
SQL; any failure yields no receipt and same-key retry completes cleanup. Scope is
current primary/registered raw store; backups, external/provider/export/collector
copies and production identities require separate handling. Restore stays quarantined
until exact authoritative fences/receipts/tombstones have been reconciled.

Connected App uses formal selected details, server counts, explicit Execute,
receipt GET and authoritative refresh. All affected caches and late responses are
invalidated by scope/session epoch. One volatile original-key unknown attempt can
be replayed; restart/identity change never automatically sends an old deletion.
See ADR0043 and AGENT_RUN_RECOVERY for operational proof and limitations.

## Historical Phase9E/9F contract

The following earlier limited-scope text is retained for history. Statements that
Person/Relationship deletion is unavailable are superseded by the exact 9H scope above.

## Current Phase9F integration

Phase9F exposes the existing 9E exact Dataset/Conversation erasure contracts through Connected Mobile self-service. Memory remains separate; account/Person/Relationship erasure is unavailable. Canonical Dataset discovery is owner-scoped and survives restart. Confirmation, immutable key, durable Receipt and authoritative refresh are mandatory; unknown outcomes and lost keys cannot become inferred success. See MOBILE_DATA_ERASURE. Earlier Backend-only statements describe 9E acceptance.

## Current9E contract (supersedes dated9D absence claims below)

Backend-only guarded canonical Dataset and Conversation erasure is implemented:
see [API](ERASURE_API.md), [ADR0040](adr/0040-guarded-dataset-and-conversation-erasure.md)
and machine-readable [capability matrix](DATA_DELETION_MATRIX.json). Three signed
operations use strict exact structured target/Relationship, five-minute server
challenge and canonical UTC snapshot, explicit caller execution, durable receipt
and authoritative refresh. No confirm boolean, fuzzy body matching or SQL cascade
can replace this service. Owner row and existing domain locks serialize writes.
Pending/running/completed-unresolved runs block Conversation deletion.

Primary formal messages are physically removed; target tombstones, Run operation
keys and canonical import dedup/receipt metadata remain. Dataset speaker labels
are removed with its messages. Other Conversations/Relationships/Datasets and all
Memory survive. Same-key exact replay returns the old receipt before target lookup;
changed payload conflicts. Tombstones cannot be recreated via the public resource
creation path. Old Agent REST/SSE keys return404; original/duplicate/new identical
same-scope import finalize returns409 dataset_deleted. Different transcripts/scopes
remain valid. Historical Job imported summaries are receipts, not surviving data.

Person/Relationship self-service deletion is unavailable even when empty; associated
Memory, import/provenance and multiple Relationship FKs are not silently enlarged.
Full Owner/account erasure remains a formal unfinished R-09 prerequisite: requires
production identity/revocation, run barriers, dependency enumeration, retained
key policy, caches/exports/provider/copy handling and backup reconciliation. Do not
claim App can delete all personal data. App has no chat erasure controller; current
Settings/History explain the boundary. Known external API deletion is reflected by
fresh/focused History reads; existing lifecycle clears models/cursors on leave/logout.

Erasure challenges expire after5min and are physically cleaned in bounded existing
maintenance batches after expiry+24h. Erasure receipts/tombstones remain owner lifetime
(no account erasure policy yet); they contain identifiers/counts/hashes/time, never
another body. Memory retention and mutation controls remain unchanged. Canonical raw
artifacts already undergo terminal finalize cleanup; failures still retry under9D.
Formal-message erasure receipts do not certify physical raw-source/backup deletion.

Controlled native PostgreSQL restore freezes a complete current primary and checks
exact immutable Conversation/Dataset IDs and scope; propagates tombstones and
removes only their restored formal bodies/speakers; copies immutable current erasure
receipts and invalidates restored challenges. All current Agent keys must still match.
Missing/mismatched primary/receipt/target/key, missing post-backup tombstone fences or
any error means NO RELEASE. Repeated application preserves other owners and Memory.
No independent journal is implemented; main-database loss still blocks production
disaster recovery. Production copy encryption/35d rotation/key custody/scheduler
installation remain undeployed. Old private backups are not rewritten by DELETE.

## Historical9D contract (retained context)

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
