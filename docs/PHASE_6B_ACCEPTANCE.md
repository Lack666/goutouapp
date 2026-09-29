# Phase 6B acceptance — Memory Undo, Deletion and Confirmation Boundary

Date: 2026-09-29. **Status: PASS.** `project-phase.json` records
`completed_phase=5`, `completed_subphase=6B`. Phase 6 remains in progress.

## Roadmap preflight and existing undo/delete audit

Read `AGENTS.md`, the master plan, architecture, Skill contract, memory/API
contracts and Phase 3G/3H/6A reports. Phase 3 already had a bounded latest-
insertion undo and hard delete methods over the authoritative MemoryStore.
Those methods had no network retry receipt or public confirmation challenge.
Phase 6A's signed controls and Agent shared the same PostgreSQL records and
consent row. Phase 6B preserves that store; only challenge/receipt metadata is
new. No Phase 6C retention policy, Phase 6D final acceptance or Phase 7 Mobile
implementation was started.

## Code and behavior

- **Undo preview:** GET is read-only and exposes only the current reversible
  operation ID, record ID, scope and timestamp. The test confirms unchanged
  operation IDs/timestamps.
- **Guarded undo and idempotency:** POST requires expected operation ID and a
  valid operation key. It removes exactly that latest saved record and writes
  the receipt atomically. A same-key retry from a new service instance replays
  the receipt; the older record survives. A new key with stale expected ID
  fails, and a new preview/key can intentionally undo the next insertion.
  Two concurrent keys for one expected operation produce one `undone` and one
  `stale_undo` outcome.
- **Delete one/person/all:** A server-side challenge binds owner, action,
  target, scope, expected count, snapshot and five-minute expiry. Prepare
  leaves Memory untouched. Execute accepts no caller-selected action/target.
  A changed snapshot fails; an expired challenge fails; a consumed challenge
  cannot start another mutation. Same-key retry replays the first durable
  receipt. Delete-person removes owned Person-scoped object/relationship
  memory across its Relationships, not the Person or other Person's memory.
  Delete-all removes all owned memory, not conversation, messages, imported
  relationship messages, import jobs or identity/scope entities.
- **Consent and history:** Revoke keeps records; delete-all explicitly
  preserves or revokes consent. A preserved opt-in permits a later valid save;
  revoked consent blocks one. Record FK cascade clears deleted records' undo
  history. Hard deletion cannot be undone. Failure injected at receipt write
  rolls back record deletion/undo and challenge consumption.
- **Runtime and ownership:** A fresh Agent+MockLLM run no longer recalls
  deleted Person memory. Another Person's memory survives Person deletion.
  Signed-JWT HTTP tests check unauthenticated/foreign access, OpenAPI security,
  inspect after deletion and that control routes do not create an LLM provider.
  Public Agent sync/stream text undo returns `pending_confirmation` without
  mutation; a self-harm request containing undo words still takes the safety
  route first.
  Error responses are content-minimal and do not expose SQL or saved content.

The receipt says `primary_store_only=true`: deletion covers app-owned active
primary PostgreSQL memory. No claim is made about immediate backup or external
copy erasure. [ADR 0027](adr/0027-guarded-memory-mutations.md) records the
owner-lock, snapshot, key and transaction decisions. The dedicated mutation
routes are the guarded user controls. The Agent Service marks conversational
undo `pending_confirmation` on both public transports, after safety routing,
and directs clients to the preview/undo route. The standalone Phase 3 graph
retains its Python contract.

## TEST, DEMO and REGRESSION

Commands ran in PowerShell with `TEST_DATABASE_URL` set to a local disposable
PostgreSQL 16 `_test` namespace on port 15433, and `DATABASE_URL` to a separate
development namespace. No real model key or external account was used.

- `uv --cache-dir .cache/uv --no-managed-python run --locked pytest apps/server/tests/test_memory_mutation.py -q`: **10 passed**. Covers preview,
  expected-operation undo, retry, changed-key conflict, concurrency, challenge
  expiry/staleness/owner binding, all delete scopes, rollback, signed JWT and
  Agent/import isolation.
- `uv --cache-dir .cache/uv --no-managed-python run --locked python scripts/check_db_migrations.py`: **PASS**, Alembic upgrade → downgrade → upgrade →
  check with no pending operations.
- `.\make.cmd verify`: **PASS**, all active Phase 0–5, 6A and 6B gates; full
  backend **388 passed**, 81 Golden cases validated, frozen upstream validator,
  secret boundary and Ruff checks passed. It also reran the migration cycle,
  focused tests and both new demos.
- `apps/server/memory_destructive_control_demo.py` via verify: **PASS**,
  two saves → preview → undo → same-key replay with older record intact →
  confirmed delete → zero inspection and zero Agent recall.
- `apps/server/memory_destructive_http_demo.py` via verify: **PASS**,
  real Uvicorn socket and signed development JWT through preview, undo,
  same-key retry, delete-one confirmation, execute and empty inspection.
- `git diff --check`: **PASS**. `ruff check` and `ruff format --check` via
  verify: **PASS**.

## Files and limits

Code: `app/services/memory_mutation.py`, memory API/error routes, Agent input,
state, intent and service guard, two ORM rows, Alembic revision
`20260929_01`, SQL MemoryStore owner locks, test and demos.
Contracts: `MEMORY.md`, `MEMORY_API.md`, `MEMORY_DELETION.md`, architecture,
database/server docs, master plan and ADR 0027. Gates: `scripts/verify.py`,
`scripts/check_db_migrations.py`, `project-phase.json`.

Known limits: direct standalone Phase 3 conversational undo is not a previewed
mutation; public Agent transports return `pending_confirmation` for it.
Receipts/challenges are durable
without a production cleanup schedule. Retention, expiry cleanup
and backup/deletion policy belong to Phase 6C. Phase 6 final acceptance is
6D; Mobile is Phase 7. Work stops at Phase 6B.
