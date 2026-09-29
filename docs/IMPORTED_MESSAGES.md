# Imported relationship messages — Phase 5C

## Separate message model

`RelationshipMessage` is a separate PostgreSQL table from Phase 4
`Conversation`/`Message`. The latter retains only Agent user/assistant/tool
history; `AgentService` and `records.recent_messages()` still read only that
table. Imported external chat cannot become an Agent role by accident.
Each RelationshipMessage belongs to an owner, Relationship and ImportJob and
has an explicit `self`, `person` or `system` sender. Composite foreign keys
enforce the owner/Relationship/Job relationship and Person compatibility.

Each occurrence stores the parser-normalized content, canonical UTC
timestamp, original source-local timestamp string and timezone, source index,
line range, raw speaker label, message fingerprint and content type. `created_at`
records database import time, not historical chat time. Relationship queries
are owner-scoped and order by UTC timestamp, Job ID and source index. Source
index fixes order among equal timestamps within a Job; the Job ID is a
deterministic tie-breaker across Jobs.

## Merge contract and integrity

`ImportMergeService.merge(actor, job_id, expected_revision, source)` accepts a
one-pass `ChatImportSource`, not caller-built `ImportedMessage` objects. It
locks the owner-scoped Job, requires `ready` (or an imported Job for replay),
checks the revision, and reruns Phase 5A's trusted parser. It compares parser
and schema versions, timezone, source and transcript fingerprints, message
count, first/last timestamps and the complete speaker inventory/counts with
the Job before any formal Message insert. Any mismatch fails with
`transcript_mismatch` and rolls back. Readiness, Relationship ownership and
Person compatibility are checked again under the lock.

The parser sends canonical messages to a PostgreSQL temporary staging table
in batches of 500. Python keeps only the parser's current bounded message and
one batch; the Job never stores raw source or a transcript JSON dump. The temp
table is private to the transaction and is not product history. A single
`INSERT ... SELECT` promotes validated, nonignored rows into formal
RelationshipMessages. The Job goes `ready → importing → imported` inside the
same transaction and stores imported, ignored and system counts plus
`imported_at`. A persistence failure rolls the transaction back to `ready`
with no partial formal dataset. No LLM, Agent, Knowledge or Memory operation
occurs in this path.

`ignore` discards its messages from formal history and increments ignored
count. `system` is preserved with sender kind `system` and increments system
count. Neither is mapped to a human or assistant. The durable Job summary and
typed `ImportMergeResult` report actual imported count, ignored count, system
count, timestamps, fingerprint and import time.

## Idempotency and limits

The unique occurrence key is `(import_job_id, source_index)`; equal message
fingerprints can coexist as separate real occurrences. A repeated merge of
the same imported Job validates the provided source again and returns its
original receipt with zero new rows. A PostgreSQL partial unique index on
`(owner_user_id, bound_relationship_id, transcript_fingerprint)` for imported
Jobs prevents an identical transcript from being imported twice into the same
owner/Relationship. The service also serializes that scope with a transaction
advisory lock and returns the first Job's receipt when a duplicate ready Job is
submitted. The duplicate Job stays ready. The same transcript may be imported
to a different Relationship after explicit compatible binding.

**CROSS-FILE PARTIAL OVERLAP DEDUP: DEFERRED.** Different files covering
overlapping periods can contain indistinguishable real repeats. Phase 5C
does not discard their messages based on content fingerprints. Phase 5D adds
one-upload network transport and temporary artifacts; resumable upload remains
deferred.

In 5D, the HTTP workflow opens the Job-bound artifact and invokes this merge
service unchanged. After a successful formal import the raw file is deleted;
same-Job HTTP replay returns the durable receipt directly. A ready duplicate
Job continues to use the exact-dataset rule and retains its own artifact until
cancel or expiry. The 5C temporary staging table has `ON COMMIT DROP`, so no
permanent staging rows remain after success, rollback or a closed connection.
Relationship history is exposed through owner-scoped keyset pagination, at
most 200 rows per request. See [Import API](IMPORT_API.md).

## Local demo

With a disposable PostgreSQL `_test` namespace configured:

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked python apps/server/import_merge_demo.py
```

The demo parses the synthetic fixture, creates and explicitly binds a Job,
marks it ready, imports it, opens a new Session to query formal relationship
messages, then replays the same Job. It prints counts and timestamps but no
chat content. See [ADR 0024](adr/0024-relationship-message-merge.md) and
[Phase 5C acceptance](PHASE_5C_ACCEPTANCE.md).
