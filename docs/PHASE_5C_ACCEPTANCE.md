# Phase 5C acceptance — Imported Message Persistence and Idempotent Merge

Date: 2026-09-28. **Status: PASS.** Preflight state was the clean Phase 5B
commit `27f0f75`. This checkpoint stops before Phase 5D upload/API work.

## Message model audit and architecture

Phase 4 `Conversation`/`Message` has `user`, `assistant` and `tool` roles and
its history repository reads by Conversation. External relationship chat would
have different sender and timestamp semantics. We chose a separate
`relationship_messages` table, documented in [ADR 0024](adr/0024-relationship-message-merge.md).
The Agent history query was not changed; an integration test imports external
chat, then runs `AgentService` with Mock LLM and confirms its input history is
empty while formal relationship messages remain queryable.

## Code and invariants

Alembic revision `20260928_04` adds RelationshipMessage and extends Job status
and durable receipt fields. It enforces owner/Job/Relationship and
Person/Relationship scope with composite foreign keys, exact occurrence
uniqueness on `(import_job_id, source_index)`, and an imported-dataset partial
unique index on owner/Relationship/transcript fingerprint.

`ImportMergeService` takes an `AuthenticatedActor`, ready Job ID, expected
binding revision and a fresh `ChatImportSource`. It reparses through the trusted
Phase 5A parser, stages canonical messages in PostgreSQL batches of 500,
checks parser/schema versions, timezone, source/transcript fingerprints,
counts, timestamps and complete speaker inventory, then promotes in one
transaction. Mismatch, stale revision, cancelled/awaiting status and invalid
bindings fail before formal Message writes. It rechecks owner and Person /
Relationship compatibility under a Job row lock. A failed promote rolls back
all rows and leaves the Job ready.

Sender mapping uses only explicit 5B bindings. `ignore` skips messages and
increments ignored count; `system` persists as system sender and increments
system count. The original normalized content, canonical UTC time,
source-local timestamp/timezone, source index, line range, raw label and
fingerprint are retained. Imported Job bindings are frozen. The Job stores
actual imported/ignored/system counts and `imported_at`; typed results expose
the same receipt without ORM objects.

Same-Job replay validates the source and returns the original receipt with
zero new rows. An identical transcript under a different Job for the same
owner and Relationship also yields zero new rows; a different Relationship is
an independent explicit scope. Advisory locking serializes that dataset key,
and the unique index is the database arbiter. Real repeated messages with
equal canonical fingerprint remain separate because source indexes differ.

**CROSS-FILE PARTIAL OVERLAP DEDUP: DEFERRED.** Different exports with partly
overlapping date ranges are not deduplicated by content. This avoids deleting
real repeated messages without a reliable cross-file occurrence identity.

## Tests, PostgreSQL and demo

Tests used the isolated local PostgreSQL 16 cluster on `127.0.0.1:15433`.
`TEST_DATABASE_URL` named a disposable `_test` namespace, separate from the
development URL. The existing ignored workspace cluster was used because the
Docker Desktop daemon was unavailable; test/demo databases were dropped.

- `uv ... pytest -q apps/server/tests/test_import_merge.py` → **8 passed**.
  Cases cover repeated identical occurrences, sender mapping, ignore/system,
  timestamp and provenance, new-Session persistence, same-Job replay,
  duplicate Job and different Relationship scope, transcript mismatch,
  stale revision, cancelled/awaiting Job, owner and tampered Relationship,
  database owner constraint, strict raw-source and parser-version metadata,
  injected third-row failure with full rollback,
  actual AgentService history isolation and a 10,000-message PostgreSQL
  import/replay with count/order/time/occurrence assertions.
- `uv ... python scripts/check_db_migrations.py` → **PASS**: isolated
  upgrade head → downgrade base → upgrade head → Alembic check; twelve tables.
- `uv ... python apps/server/import_merge_demo.py` → **PASS**: synthetic
  four-message transcript imported, reopened in a new Session and queried;
  imported count **4**, ignored **0**, Agent Message count **0**. Same-Job
  replay produced **0** duplicate writes.
- `.\make.cmd verify` → **PASS**: full backend suite **361 passed**; Golden
  annotation validation **81 cases**; Phase 0–5B regression, Phase 4 API,
  migration cycle, frozen upstream validation, secret boundary, Ruff check
  and format passed. The verifier reports Phase 5A, 5B and 5C PASS.

No file upload API, Mobile client, Agent analysis of imported chat, automatic
Memory, RAG or LLM speaker inference was added. See
[Imported Messages](IMPORTED_MESSAGES.md) for the data and query contract.

**Next:** Phase 5D — Import API, Upload Pipeline and Phase 5 Final Acceptance,
only after a separate explicit instruction.
