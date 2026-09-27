# ADR 0016: Bounded owner-scoped memory undo

Status: accepted for Phase 3H (2026-09-27)

## Source and decision

`SKILL_CONTRACT.md` §8 marks “撤销最近更新” as MUST. The frozen upstream
`references/practical/长期记忆与关系档案.md` §用户控制 describes `undo` for the
most recent update and `undo --op-id` when an operation ID was retained. The
frozen `scripts/memory_store.py` `command_undo` reverses the latest apply
operation, `MAX_OPERATIONS` bounds history at 20, and `forget-object` removes
records and clears operation history. Undo is therefore part of the Phase 3
runtime contract; the Phase 3G deferral is closed here.

The current app runtime persists new user/object/relationship facts but has no
general update operation. Its minimum correct undo reverses the latest
new-record insertion for an authenticated owner. A duplicate does not create
an operation. An in-memory list and PostgreSQL `memory_operations` table keep
at most 20 owner-scoped operation IDs; the SQL save and operation insertion are
one transaction. Undo removes the memory record and its operation together.
The PostgreSQL implementation works after a new session. The operation row
has an owner/record composite foreign key; a hard delete cascades to affected
history. Delete-all clears all of that owner's operations.

The upstream single-user `forget-object` clears its entire operation table
because its JSON before-snapshots could restore deleted data. This runtime's
operation rows contain only record IDs and the database cascades each deleted
record's operation row. Other persons' operations can remain without a path
to restore the deleted person's content.

## Semantics and limits

`undo_last(user_id)` is owner-wide: the latest inserted memory across that
owner's subjects is selected. It is available while memory is paused or
consent is revoked, as upstream `command_undo` does not call
`require_enabled`. A record already hard-deleted cannot be restored. The
first undo returns `undone`; with no remaining operation it returns
`nothing_to_undo`. Repeating an unkeyed `undo_last` when older operations
remain intentionally reverses the next one, so callers must not treat it as
an idempotent API retry. The graph understands a narrow explicit Chinese undo
request; Phase 4 must authenticate the caller and supply network idempotency.
The upstream optional `--op-id` variant is deferred until a public operation
identifier and transport control flow exist. No generic event-sourcing layer
is introduced.
