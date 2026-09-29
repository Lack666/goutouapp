# Phase 6A acceptance — Memory Control Service and Public Contracts

Date: 2026-09-29. **Status: PASS.** This is a Phase 6 subphase; Phase 6 is
still in progress. `project-phase.json` remains `completed_phase=5` and marks
`completed_subphase=6A`. Phase 6B, 6C, 6D and Phase 7 were not started.

## Preflight and existing memory audit

Read the master plan, architecture, memory/runtime/service/auth contracts and
Phase 3G, 3H and 4D acceptance before implementation. The Phase 3
`MemoryService` already offered consent, pause/resume, scoped recall, list,
undo and delete in Python. The Phase 4 authenticated API did not expose user
memory controls. `memory_enabled` only enables a run; it is not durable
consent. The existing revoke-and-keep operation disables recall/write and
retains inspectable records. The existing Agent can grant anew on an explicit
save-consent phrase; a revoked run without that phrase cannot write.

## CODE and contract

- `MemoryControlService` accepts only `AuthenticatedActor`; its public
  Pydantic contracts expose consent/pause/effective state and timestamp,
  or a bounded page of saved records with historical-accuracy notice.
- The API and Agent use the same `SQLAlchemyMemoryStore`, `memory_controls`
  and `memory_records`; there is no second consent state. The store now locks
  the owner row for grant/revoke/pause/resume, including runtime operations.
  Record insertion reacquires that lock and rechecks consent/pause, so an
  in-flight Agent run cannot commit after a completed pause or revoke.
  Repeated changes remain safe and create at most one control row.
- Signed Bearer routes expose inspect control, consent change, pause, resume,
  paginated inspect and owner-scoped single-record inspect. Request body cannot
  set owner ID. Foreign and
  missing scope IDs use owner-neutral 404. No undo/delete endpoint, retention
  policy, model call or mobile code was added.
- Memory pages use `created_at DESC, id DESC` with a strict keyset cursor and
  1–50 item bound. Person and Relationship filters are exact. Public views
  omit internal hashes, raw evidence, operation history and hidden analysis.

## TEST, DEMO and REGRESSION

Validation ran against disposable PostgreSQL 16 databases on localhost port
15433, with process `TEST_DATABASE_URL` set to a separate `_test` namespace.
No external model key or account was used.

| Command | Result |
| --- | --- |
| `pytest -q apps/server/tests/test_memory_control.py` | 7 passed; real signed JWT, service/DB, Agent+MockLLM, scope, cursor, control/write races, OpenAPI and error tests |
| `python apps/server/memory_control_demo.py` | PASS: grant → Agent save → inspect → pause → resume → revoke, with retained record |
| `python apps/server/memory_control_http_demo.py` | PASS: real Uvicorn socket and signed JWT GET/POST/GET controls |
| `.\make.cmd verify` | PASS: Phase 0–5 and 6A gates; full backend 378 passed; 81 Golden cases validated |
| `scripts/check_db_migrations.py` via verify | PASS: upgrade/downgrade/upgrade/`alembic check` |
| Frozen upstream, secret boundary and Ruff via verify | PASS |
| `git diff --check` | PASS |

The tests show HTTP grant/revoke/pause/resume changing a later `AgentService`
run's recall/write behavior through the same PostgreSQL store. An Agent-saved
record is visible through HTTP. Paused/revoked inspection remains read-only.
Equal creation timestamps paginate without duplicate or missing IDs.
Concurrent opposite control operations leave a single valid durable row.

## Architecture decision and known limits

[ADR 0026](adr/0026-memory-control-plane.md) records the shared store,
serialization and public read-model decision. `updated_at` is null before a
control row exists. A control response may reflect a later concurrent durable
change after its own mutation, as it rereads the row. The record view returns
the saved content to its owner; it does not recertify that historical content
as current fact. Undo and destructive deletion APIs are Phase 6B; production
retention and backup policy are Phase 6C. Phase 6D final acceptance and
Phase 7 mobile remain deferred.
