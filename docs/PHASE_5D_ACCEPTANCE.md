# Phase 5D acceptance — Import API, Upload Pipeline and Phase 5 closeout

Date: 2026-09-29. Status: **PASS** after CODE, TEST, DOC, DEMO,
REGRESSION and E2E verification. Project marker: `completed_phase=5`,
`completed_subphase=5D`. Phase 6 was not started.

## 5C preflight and staging audit

5C creates a PostgreSQL `TEMP` staging table with `ON COMMIT DROP` inside
the same transaction as reparse, integrity checks, final insert and Job
receipt. Successful commit drops it. Parser, binding or persistence failure
rolls the transaction back; a crash closes the PostgreSQL session. There is
no durable staging table and no orphan staging row to reconcile. Cancelling
an unimported Job has no staging table. Formal RelationshipMessage atomicity
and exact-dataset arbitration remain in 5C.

## Acceptance matrix

- **Upload API / authentication / ownership: PASS.** Signed Phase 4 JWT,
  one multipart file, timezone and optional format. The owner is derived only
  from the verified subject. Foreign Job inspect/bind/ready/finalize/cancel
  and relationship history return owner-neutral 404. A direct service test
  rejects another owner's artifact ID.
- **Artifact store / lifecycle / immutability: PASS.** Opaque random key,
  private fixed root, `.part` to completed `.bin`, no overwrite endpoint,
  metadata in PostgreSQL, unique composite owner/Job binding. No source blob.
  Success deletes raw bytes and retains receipt; cancelled/expired/failed
  uploads clean their files. Failed merge retains its source for retry.
- **Upload limit / streaming / path security: PASS.** Default exact file
  limit 100 MiB; 64 KiB endpoint reads and writes; ASGI body guard allows
  at most the file limit plus 1 MiB multipart framing and handles chunked
  requests without `Content-Length`. Oversize and interrupted reads leave no
  Job or partial artifact. Client filename cannot choose a path. Content-Type
  is only a hint; parser validity controls acceptance.
- **Import Job API / speaker / relationship binding: PASS.** Typed inspect
  includes summary, inventory, bindings, readiness issues and imported
  receipt summary. Mutation routes delegate to 5B `ImportJobService`; no
  automatic `我` identity inference.
- **Finalize / source integrity / replay: PASS.** A Job can use only its
  creation-bound artifact. Length and SHA-256 are checked before 5C reparses
  and compares parser/schema versions, source/transcript fingerprints and
  speaker inventory. Same imported Job replays its durable receipt after file
  deletion. Same owner/Relationship/transcript second Job inserts zero rows.
- **Failure / cancel / expiration / staging cleanup: PASS.** Triggered DB
  failure leaves the Job ready, zero formal rows and retriable artifact.
  Cancel and explicit expiration cleanup remove files without affecting
  formal messages. A simulated success-cleanup fault still returns the durable
  receipt; maintenance later removes its file without reimport. A one-hour
  grace orphan sweep covers crashed `.part` and unreferenced completed files.
  The operator CLI runs one cleanup pass.
- **Pagination / Agent isolation / no LLM or Memory: PASS.** History route
  enforces a 1–200 row limit and owner-scoped keyset cursor in historical
  timestamp/source order. Imported history remains outside Agent messages;
  HTTP Agent run after import receives empty prior Agent history. Import
  composes no Agent/LLM and writes no Memory record.
- **10k HTTP import / concurrent finalize: PASS.** A real localhost Uvicorn
  socket receives a 10,000-message multipart body, binds, finalizes into
  PostgreSQL and exposes paginated history. Two concurrent finalize calls
  create one 1,000-message formal dataset and one durable receipt.

## Phase 5 full E2E mapping

1. JWT → upload → parser → Job: `test_full_http_workflow_replay_duplicate_pagination_and_agent_isolation`.
2. Raw `我` unbound cannot ready: same test.
3. Explicit self/person/Relationship binding → ready: same test and local demo.
4. Finalize → formal rows: same test.
5. Agent history isolation: same test with HTTP Agent endpoint and spy runtime.
6. Same finalize retry → zero new rows: same test.
7. Second identical Job → zero new rows: same test.
8. Tampered artifact → zero formal writes: `test_rejections_cleanup_tamper_cancel_expire_and_failure_retention`.
9. 10k real HTTP upload/import: `test_real_socket_ten_thousand_http_import`.
10. Cross-user access denied: full workflow and chunked-read tests.
11. Cancel → artifact removed, no formal messages: rejection/cleanup test.
12. Persistence failure → artifact retained, atomic rollback and later retry:
    rejection/cleanup test.

## Validation record

The final `TEST_DATABASE_URL` used a disposable PostgreSQL 16 `_test`
namespace; `DATABASE_URL` pointed to a different development namespace.
No external model key was used.

```powershell
$env:TEST_DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:15433/goutou_test'
$env:DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:15433/goutou_dev'
.\make.cmd verify
git diff --check
```

`make verify` passed the isolated Alembic upgrade/downgrade/upgrade/check
cycle, inherited repository and frozen-upstream checks, Phase 4 full API
regression, Phase 5A parser, 5B binding, 5C merge, 5D artifact/API/security
tests and real socket demo, full backend suite, Golden validation, secret
boundary, Ruff lint and format. Focused 5D suite: **10 passed**; full backend
suite: **371 passed**. The full backend suite includes the 10k HTTP test.
Local socket demo output confirmed upload
201, two speakers, ready, two imported messages, a one-row first page and
zero raw artifacts remaining. `git diff --check` exited 0 after the final
changes; Git printed only its Windows LF-to-CRLF working-copy notices.

## Architecture decisions and known limits

ADR 0025 selects private local artifact storage behind a replaceable protocol,
separate metadata, creation-bound owner-scoped Job reference, and explicit
cleanup. `python-multipart` is locked for FastAPI multipart parsing. The
receive guard bounds request bytes before Starlette completes form spooling;
the exact file limit remains in the endpoint. Automatic cleanup scheduling,
distributed reconciliation, production object storage and cross-file partial
overlap deduplication are deferred. Chat analysis, Memory extraction from
imported history, Mobile and RAG are deferred.
