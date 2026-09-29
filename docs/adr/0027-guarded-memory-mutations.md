# ADR 0027: Guarded memory mutations and confirmation

Status: Accepted for Phase 6B, 2026-09-29.

## Context

Phase 3's `undo_last` intentionally advances through a bounded insertion
history. Repeating a network request could undo a second record. Python delete
methods require a trusted caller but did not expose an authenticated,
inspectable confirmation boundary. Phase 6A established one owner-locked
authoritative memory store and a signed API.

## Decision

Add a transport-independent `MemoryMutationService`. Its public undo first
previews the latest operation and then requires the expected operation ID and
an owner-scoped operation key. A durable receipt is inserted in the same
transaction as the record removal. Exact retries replay that receipt before
examining current undo state; a key reused for a different target conflicts.

Delete-one, delete-person and delete-all first create a five-minute server-side
challenge. It binds owner, action, target, scope, count and a hash of selected
record IDs/update times. The execute route takes only confirmation ID and
operation key. It locks the owner, verifies the challenge and current snapshot,
deletes the selected primary memory records, optionally revokes consent,
consumes the challenge and inserts the receipt atomically. Foreign/missing
targets use owner-neutral responses. PostgreSQL's record-to-operation foreign
key cascade clears affected undo history. Shared owner-row locking serializes
with Agent saves and legacy MemoryService undo/delete methods.

The mutation table's unique owner/key constraint spans actions. The key is
opaque and receipt metadata contains no memory content. Challenges and
receipts do not foreign-key target records so hard deletion does not erase
their retry evidence. Delete-person covers the current contract's Person ID
scope across owned Relationships; delete-all leaves non-memory domains intact.
The required delete-all flag makes consent preservation or revocation explicit.

## Consequences

The API is thin and does not call an LLM. Retry safety and rollback are
database-backed across processes. A stale snapshot requires a new user
confirmation; the service does not silently widen a bulk delete. Direct Phase
3 `undo_last` retains its earlier standalone contract; the Agent Service
sets a typed guard so conversational undo is pending after safety routing on
both public transports. The dedicated previewed API performs the mutation.
The `primary_store_only` receipt field limits
claims to the active database. Production retention, cleanup and backup policy
remain Phase 6C.
