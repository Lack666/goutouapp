# Phase 6B memory undo and deletion

The authenticated memory control API uses the Phase 3 MemoryStore's active
`memory_records`, `memory_operations` and `memory_controls` tables. The new
confirmation and mutation tables contain target IDs, snapshot hashes and
receipts, not saved content. All control logic is deterministic and has no
LLM, Agent or knowledge call.

## Revoke, undo and delete

Revoke disables future recall and writes while keeping records inspectable.
Delete removes selected records from the app-owned active primary PostgreSQL
database. Delete-one removes exactly one record in the supplied person and
relationship scope. User-scoped records require null scope IDs. Delete-person
removes this owner's object and relationship records whose `person_id` is the
specified owned Person, across its Relationships; it retains user-scoped
records. It does not delete the Person or any Relationship. Delete-all removes
all of this owner's memory records, including user-scoped records. It does not
delete Agent conversations/messages, RelationshipMessages, import jobs, Person,
Relationship or User. A zero-record delete-all is valid and produces a receipt.

Delete-all preparation requires `revoke_consent_after_delete`. When false,
consent remains as it was, so later eligible and explicitly requested saves
can succeed. When true, execution also revokes consent and pauses recall/write
in the same transaction. Deletion does not otherwise forbid future memory.

Undo reverses only the latest **new record insertion** still in the bounded
Phase 3 history. It cannot restore hard deletion. Duplicates create no undo
entry. The read-only preview returns the latest operation ID, record ID and
scope. The dedicated undo API requires that exact `expected_operation_id` and
an `operation_key`; a changed latest operation fails with `stale_undo`, and no
eligible operation fails with `undo_unavailable`. A new intentional undo needs
a new preview and key. Direct Phase 3 `undo_last` retains its original
standalone Python contract. The Agent Service sets a typed guard on both sync
and streaming runs. After safety routing, conversational undo returns
`pending_confirmation` without deleting a record; clients use the dedicated
API for guarded public undo.

## Confirmation and retries

Delete is a two-step flow: prepare a challenge, show its action, target/scope
and expected count to the user, then execute with that opaque confirmation ID
and an operation key. The server stores the authoritative owner, action,
target, scope, count and hash of record IDs plus update timestamps. The
challenge expires in five minutes and is consumed once. The execute route
accepts no client-supplied action or target, so a challenge for Person A cannot
be repurposed for Person B or delete-all. A changed target snapshot requires a
fresh preparation. Prepare never deletes or changes any memory record.

Each owner supplies a valid operation key for every execution. The database
enforces a unique owner/key pair; the receipt records a request fingerprint.
The same owner, key and request replay the original durable receipt after a
restart, even after the record is gone or a challenge expires. Reusing the key
for another request returns `mutation_conflict`. A successfully consumed
challenge with a different key returns `confirmation_stale`. A foreign or
unknown challenge returns `confirmation_required`, without confirming another
owner's data. A foreign mutation receipt is indistinguishable from a missing
one. HTTP errors use the standard content-minimal envelope; no raw SQL or
memory content is logged.

Undo and delete acquire the owner User row lock used by Agent saves and legacy
MemoryService mutations. Each execution validates current state, changes
records, lets the record FK cascade clear affected undo history, updates
consent when requested, consumes the challenge and writes the receipt in one
PostgreSQL transaction. A failed receipt write rolls back the entire mutation.
Concurrent different-key requests for the same target cannot both report
deleting or undoing that target.

Successful delete responses report `primary_store_only=true`. This means the
app-owned active primary PostgreSQL records are gone. It does not claim that
backups or external copies are immediately erased. Phase 6C adds expiration, challenge cleanup and a backup/deletion policy.
Receipts remain durable. The mobile client is Phase 7.

## Phase 6C lifecycle and scope clarification

Retention cleanup physically removes expired primary records and cascades only
their undo operations under the existing owner lock. Expired expected undo targets
fail unavailable; after cleanup, a changed latest operation fails stale. No fallback
undo or pseudo-success receipt is created. Mutation receipts are durable for owner
lifetime, so matching retries replay even after consumed/expired challenge cleanup.
Different payloads reusing the key conflict. Challenge cleanup waits until five-minute
expiry plus configurable 24-hour grace. Valid challenges are retained.

Delete-person relies on structured Person/Relationship associations; it does not
search arbitrary user-level text for mentions or remove Person entities, imported
messages, chats or all system data about that person. Delete-all includes expired
primary memory awaiting cleanup, with the original explicit revoke flag unchanged.
Revoke-and-keep stops future recall/write but does not pause the retention clock.
See [retention policy](MEMORY_RETENTION.md) and [backup/restore design](MEMORY_BACKUP_DELETION_POLICY.md).
Production backup rotation, restore-safe deletion replay and scheduling are not deployed.

## Phase 6D accepted semantics

Delete-one requires the exact memory/person/relationship scope from inspection.
Prepare alone never removes memory. Its stored snapshot binds owner, action,
target and selected records; execute rejects extra client action/target fields,
foreign/missing/expired/consumed challenges and widened snapshots. Completed
same-key retries replay the durable receipt even after challenge cleanup; changed
payloads conflict. Undo likewise matches one expected latest operation, never
falls back after expiry/cleanup, and preserves older memory on retry.

Challenge and receipt responses include `deletion_scope_notice`. Success means
the selected primary memory and its undo targets were removed. Necessary receipt
metadata stays durable; challenge metadata follows expiry+grace. Neither deletes
full Agent chat history, imports, Person/Relationship entities, logs, backups nor
provider copies. Both explicit delete-all revoke flag modes remain supported.

Replacing an expired duplicate during a fresh authorized save invalidates only
the old record's undo target. The old ID cannot be resurrected by guarded undo.
Removal plus new save/new operation is atomic; consent/pause failure or rollback
leaves the old row intact. See [Phase 6 final acceptance](PHASE_6_FINAL_ACCEPTANCE.md).
