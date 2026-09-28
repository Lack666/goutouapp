# Persistent import jobs — Phase 5B

`ChatParseResult → ImportJobService → chat_import_jobs + chat_import_speakers`
is an application workflow, independent of FastAPI and AgentRuntime. The caller
supplies a Phase 4 `AuthenticatedActor` and owns the SQLAlchemy transaction.
No upload route exists in this phase.

## Lifecycle and ownership

The service rejects fatal or incomplete parse results; it does not create a
failed row. A successful result creates `awaiting_binding`, a durable metadata
row, and one inventory row per exact raw speaker label. It does not create a
Person, Relationship, Conversation, Message, Memory, or AgentRun. `ready` means
the job can enter Phase 5C; no transcript message has been imported.

Phase 5C extends the status vocabulary with transaction-local `importing`
and durable `imported`. The imported Job records actual imported, ignored and
system message counts and import time. Its bindings are frozen; a new
ImportJob is required for rebinding. See [Imported Messages](IMPORTED_MESSAGES.md).

Every inspect and mutation filters by the authenticated owner's ID. Unknown and
other-owner jobs both return `job_not_found`. The service checks owner-scoped
Person and Relationship records before binding. Composite database foreign
keys independently reject a speaker's Person from another owner, a job's
Relationship from another owner, and a speaker attached with a mismatched job
owner. A `self` binding stores no arbitrary User ID: it means the authenticated
owner of this job. The service never infers `self` from `我`, or `person` from a
matching display name, a two-speaker transcript, or an LLM.

The service accepts only a label in that job's inventory. It exposes typed
`unbound`, `self`, `person`, `system`, and `ignore` bindings. Binding changes are
serialized by locking the job row, increment `binding_revision`, update
`updated_at`, and move a formerly ready job back to `awaiting_binding`.
Callers may supply `expected_revision` to detect stale UI edits. A cancelled
job retains its metadata but cannot be rebound or marked ready. Cancellation
does not delete unrelated product data.

## One-to-one readiness

`mark_ready` requires exactly one explicitly bound `self`, exactly one
explicitly bound primary `person`, no unbound labels, a bound Relationship owned
by the actor, and equality between the Person binding and the Relationship's
Person. Additional labels must be explicitly `system` or `ignore`. Two bound
external persons produce `unsupported_group_binding`; group chat is retained
but cannot become a one-to-one import. The service returns stable readiness
issue codes. It checks parser metadata completeness. Fatal output cannot enter
this workflow.

## Metadata, fingerprints, and privacy

The job stores parser/schema versions, source format/timezone, SHA-256 source
and transcript fingerprints, message/speaker counts, source-order time bounds,
warning/error totals, truncation count, and at most 20 distinct sampled issue
codes. The parser itself retains at most `max_issue_records` issue objects;
total warning counts still grow accurately. No raw source, full parse-result
JSON, chat content, or imported Message rows are stored in job metadata.
`ImportJobView` contains metadata, inventory, bindings, and readiness issues,
not ORM objects or message content. Ordinary logs should use job IDs and counts
rather than nicknames.

Equal transcript fingerprints for one owner produce a
`possible_duplicate_job_id` hint on creation. Both jobs remain separate; this
is not a Message deduplication guarantee. A message fingerprint identifies
canonical content, **not an occurrence**. Phase 5C must use at least job ID +
source index + message fingerprint or an equivalent source occurrence key; a
message fingerprint alone cannot be the imported Message unique key. Phase 5C
must also verify that staged or reparsed input matches the job's parser/schema
versions, source/transcript fingerprints, counts and inventory before merge.

## Local demo

With an isolated PostgreSQL `_test` namespace configured:

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked python apps/server/import_job_demo.py
```

The demo creates a disposable database, parses the synthetic fixture, creates
a job, prints the speaker inventory, binds `我` to the authenticated user and
`怡宝🥰` to a synthetic Person, binds an existing Relationship, marks ready,
closes the Session, then inspects in a new Session. It asserts zero formal
Message rows and drops the disposable database.

See [ADR 0023](adr/0023-persistent-import-binding.md) for decisions and
[Phase 5B acceptance](PHASE_5B_ACCEPTANCE.md) for validation evidence.
