# ADR 0026: One authoritative memory control plane

Status: Accepted for Phase 6A, 2026-09-29.

## Context

Phase 3 already stores consent, pause state and memory records, but its Python
methods are not a signed user API. The SQL store's earlier control setter read
then wrote the row, which did not serialize concurrent control requests.

## Decision

The authenticated application service uses the existing MemoryStore adapter
and tables. The SQL adapter locks the owner User row for control changes,
including initial creation, and updates the same MemoryControl row used by the
Agent. Runtime grant, pause, resume and revoke call the same atomic operation.
The SQL record insertion takes this lock and rechecks the control before
commit, closing the check/write race when a run overlaps pause or revoke.
The public read models omit internal evidence and hashes. Inspection uses a
bounded keyset query, not the unbounded runtime `list_for_user` method.

Phase 3's revoke-and-keep behavior is retained: consent is false, pause is
true, records remain inspectable. Resume with revoked consent is a no-op.
Historical records are presented as dated information, not current truth.

## Consequences

The HTTP layer contains only authentication, validation and service calls.
No new consent table, migration, model provider or Agent dependency is needed.
The application service makes separate read-only queries for owner/scope
validation. A concurrent control change may occur between an API mutation
and its returned state read; the response represents the most recently
observed durable state, while every mutation is serialized by PostgreSQL.
Retention, undo and deletion APIs remain later Phase 6 work.
