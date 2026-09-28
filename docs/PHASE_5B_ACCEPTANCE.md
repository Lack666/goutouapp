# Phase 5B acceptance — Persistent Import Jobs and Speaker / Relationship Binding

Date: 2026-09-28. **Status: PASS.** The preflight state was a clean Phase 5A
commit (`ace16d0`). Only Phase 5B work was performed. Phase 5C final Message
merge, upload API, Mobile and RAG remain deferred.

## 5A preflight

The parser already increments issue totals independently of retained issue
objects. Its `issue()` helper appends only while `len(issues) <
max_issue_records`. The 10,000-message regression now asserts **9,999**
duplicate-time warnings, **1,000** retained samples and **8,999** truncated
issues. A separate 2,000-message job test with cap 7 confirms **1,999**
warnings, **7** retained samples, **1,992** truncated, and a one-code job
summary. Parser and database metadata are bounded. Message fingerprint is
canonical-content identity, never occurrence identity; see
[Import Jobs](IMPORT_JOBS.md).

## CODE

Alembic revision `20260928_03` and SQLAlchemy models add durable
`chat_import_jobs` and `chat_import_speakers`. The job stores versions,
timezone, source/transcript fingerprints, counts, source-order time range,
bounded issue codes, relationship binding, status and revision. Speakers retain
exact raw labels, first-appearance order and message counts. No raw chat or
full parse-result JSON is stored.

`ImportJobService` consumes `ChatParseResult` and Phase 4
`AuthenticatedActor`, rejects fatal/incomplete results, returns typed views,
and supports inspect, inventory, speaker binding, relationship binding,
readiness, mark-ready and cancellation. It never invokes Agent, LLM, Knowledge
or Memory. It never creates Person, Relationship, Conversation or Message.
No automatic self/person mapping exists. Ready requires exactly one explicit
self, one explicit primary Person, resolved extra labels, owner-scoped and
compatible Relationship, and complete transcript metadata. Two external
Persons return `unsupported_group_binding`. Binding changes lock the job,
increment revision, update timestamp and return ready jobs to
`awaiting_binding`. Fatal output is rejected without a failed row. Duplicate
transcripts create separate jobs and return a possible-duplicate hint.

The database uses composite owner-scoped foreign keys for job/Relationship,
speaker/Person and speaker/job. Service access to another owner's job yields
`job_not_found`; direct cross-owner inserts/updates fail with database
integrity errors. `self` denotes the actor owning the job; no other user ID
can be supplied.

## TEST, DEMO and REGRESSION

Validation ran against the isolated local PostgreSQL 16 cluster on
`127.0.0.1:15433`. `TEST_DATABASE_URL` used a disposable `_test` namespace,
separate from `DATABASE_URL`. Docker Desktop's daemon was unavailable, so the
existing ignored workspace cluster was started directly. No production or
development database was modified by tests or demo.

- `uv ... pytest -q apps/server/tests/test_import_jobs.py` → **6 passed**.
  Cases cover no automatic identity assignment, explicit binding, stale
  revision, ownership, relationship mismatch, three-speaker group policy,
  system/ignore, cancellation, fatal result, duplicate hint, issue cap,
  cross-owner database constraints and persistence across Sessions.
- `uv ... pytest -q apps/server/tests/test_chat_import.py` → **19 passed**,
  including the 10k warning/sample cap regression.
- `uv ... python scripts/check_db_migrations.py` → **PASS** for isolated
  upgrade head → downgrade base → upgrade head → Alembic check; eleven tables.
- `uv ... python apps/server/import_job_demo.py` → **PASS**. Parsed the synthetic
  four-message fixture, showed inventory `怡宝🥰:3` and `我:1`, explicitly bound
  both identities and an existing Relationship, then reopened a new Session:
  status `ready`, revision 3, formal Message count **0**.
- `.\make.cmd verify` → **PASS**. Full backend suite **353 passed**; Golden
  validation **81 cases**; Phase 3/4 E2E, REST/Auth, streaming and idempotency
  passed; repository secret boundary, frozen upstream validator, Ruff check
  and format, and all active phase gates passed. The verifier reports Phase 4,
  Phase 5A and Phase 5B PASS, with imported Message persistence deferred.

## Decisions and limits

[ADR 0023](adr/0023-persistent-import-binding.md) records fatal-result
rejection, explicit owner-scoped binding, one-to-one readiness, reversible
ready state, duplicate hint and occurrence identity. Phase 5C must verify
reparsed/staged transcript integrity before writing imported Messages and must
not use message fingerprint alone as uniqueness. Phase 5D may add upload
artifacts and explicit target creation. There is no real-model or live user
chat quality claim in this checkpoint.

**Next:** Phase 5C — Imported Message Persistence and Idempotent Merge, only
after a separate explicit instruction.
