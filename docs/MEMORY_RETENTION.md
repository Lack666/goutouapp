# Authoritative Memory Retention Policy — Phase 6C

Current9D supplement: the opt-in operator loop in RETENTION_MAINTENANCE composes
this same service with Import cleanup and9C reconciliation. Actual short-interval
execution/retry and multi-process competition pass locally. No production OS task,
supervisor, collector or alert schedule is installed. All180d/24h/owner-lifetime
policies below remain; older automatic-scheduling absence refers to production/6C.

Policy version: 1, 2026-10-08. This product decision supplements the Skill
memory contract without changing consent. See ADR 0028 and
[backup/deletion policy](MEMORY_BACKUP_DELETION_POLICY.md).

## Inventory

For each category below, storage, ownership, trigger, duration, enforcement,
deletion and backup coverage are explicit. Primary database tables are covered
by any full PostgreSQL backup; physical primary removal does not erase copies.

- **Active Memory Records:** purpose is compact consented historical context;
  `memory_records`, owner + optional Person/Relationship scope. New records
  expire at creation + configured 180 days by default. `expires_at <= now`
  excludes them from recall and default lists immediately. Maintenance removes
  expired records, cascading their undo history. Owners can explicitly inspect
  expired records by ID until removal and can delete them at any time. CODE.
- **Consent/Pause Controls:** purpose is durable authorization;
  `memory_controls`, per owner. Retained for owner lifetime, independent of
  record expiration, including owners with zero memories. Only explicit control
  actions change consent/pause. No retention cleanup. Account deletion is
  outside 6C. Included in full DB backups. CODE, existing 6A.
- **Undo Operation History:** purpose is bounded latest insertion undo;
  `memory_operations`, owner + record ID, maximum 20 operations per owner.
  Pruned on newer saves, cascaded when its record is physically removed. Expired
  latest targets are unavailable; never fall back to an older target under the
  same expected-operation request. Included in DB backups. CODE.
- **Mutation Receipts:** purpose is durable destructive-operation replay and
  key fencing; `memory_mutations`, owner/key. Retained for owner lifetime with
  no time cutoff: **durable_owner_lifetime**. Retry horizon is the lifetime of
  the owner and intact primary metadata. Same key/payload returns the original
  receipt indefinitely; changed payload conflicts. No receipt expiry or physical
  cleanup is implemented. No saved content, only IDs, timestamps, counts and
  fingerprints. Included in DB backups. CODE, growth cost accepted.
- **Confirmation Challenges:** purpose is five-minute confirmation;
  `memory_confirmations`, owner + action/target/snapshot. Pending challenges are
  valid before expiry, expired at the exact expiry instant; consumed challenges
  cannot be reused. All become cleanup eligible at `expires_at + grace`, default
  24 hours. Consumed challenges also wait until that threshold, so valid
  challenges are never removed. There is no persisted invalidated/stale status;
  snapshot-stale challenges fail execution and age out like pending challenges.
  Deleted UUIDs are not regenerated, and missing challenges fail closed.
  Receipt lookup precedes challenge lookup, preserving retry after cleanup.
  Included in DB backups. CODE.
- **Deletion/Operation Metadata:** purpose is safe operation accountability;
  receipt/challenge tables above, not a second content store. Same respective
  lifecycles. Cleanup returns counts only; it creates no content-bearing deletion
  ledger. No automatic backup-deletion replay can be reconstructed from this
  metadata alone. CODE; external recovery ledger is NOT DEPLOYED.
- **Application Logs:** purpose is diagnostics; current Python logging goes to
  process output with generic errors, no persistent app log database. Memory
  bodies, raw evidence/chats, JWTs, credentials and hidden reasoning must never
  be emitted. Planned deployed log rotation: 7 days from emission, operator
  controlled, restricted access. No production collector or automated rotation
  is deployed. Test/maintenance output contains aggregate counts only; generated
  local `.cache` validation output is developer-owned. NOT DEPLOYED production.
- **PostgreSQL Backups:** purpose is recovery; no production backup service is
  deployed or configured here. Planned encrypted daily backups with maximum
  35 days from creation, daily rotation, including these tables. Deletion does
  not rewrite existing backups. See the separate restore runbook. DESIGN ONLY.
- **External Copies:** no external memory-copy store or production model account
  is configured/verified in 6C; tests use MockLLM. A future external LLM can
  receive recalled context; local DELETE cannot retract a completed transmission.
  Provider retention must be documented and approved at deployment, never assumed
  equal to primary expiry. Operator-made exports must obey the backup policy;
  untracked copies are not guaranteed erasable. DESIGN ONLY.

RelationshipMessages, import jobs, original chat artifacts, Agent conversations
and Messages are separate data domains. They are not cleaned by this service.
Artifacts retain Phase 5 expiry/cleanup rules; memory cleanup is not transcript
or account deletion. Person deletion uses structured IDs and cannot search
arbitrary user-level text for mentions of that person.

## Record and configuration contract

`MEMORY_RETENTION_DAYS=180` accepts integer 1–3650 days.
`MEMORY_CHALLENGE_CLEANUP_GRACE_HOURS=24` accepts integer 1–8760 hours.
`MEMORY_CLEANUP_BATCH_SIZE=100` accepts integer 1–1000 rows per category per batch.
The server Settings validates these before composing runtime/store/maintenance.
Fractional, boolean, negative, zero and invalid values fail closed. There is no
receipt retention-days setting: durable receipts are a fixed safety decision.
No dependency or lockfile change is required.

Each new service save fixes aware UTC creation and expiration timestamps.
Recall never refreshes expiry, creation, update or last-used time. Settings
changes affect only subsequent saves; they do not shorten existing dates or
reinterpret legacy records. Duplicate saves do not renew expired records:
until primary cleanup, the unique content key still reserves that row. After
physical removal, a new explicitly requested eligible save is a new record.
Expired rows continue counting toward the 200-record storage limit until removed.

Migration `20261008_01` adds a non-null, indexed UTC-aware `expires_at`.
Existing records, even very old ones, receive migration transaction time +
180 days, rather than creation + 180 days. This fixed one-time grace avoids
instant mass deletion and unexplained permanent legacy retention. The migration
does not change creation/update dates or controls and does not read environment
configuration. Existing Python MemoryRecord construction defaults to creation +
180 days for compatibility; trusted synthetic callers may supply explicit dates.
Production writes go through MemoryService with the configured policy.

## Recall, inspection and in-flight semantics

The SQL query excludes expired rows and MemoryService repeats the date gate
for standalone stores. Scope, consent and pause gates remain required. Expiration
and physical cleanup are independent. Default paginated inspection lists active
records, but owned GET-by-ID can show `state=expired` before cleanup. Public views
add `expires_at`, `state` and `retention_policy_summary` to existing fields; even
an empty list carries the policy summary. Expired does not mean recallable.

A recall takes a UTC time snapshot. A record valid at that boundary may already
be in an in-flight runtime's context when it later expires or is deleted. The
system does not remotely retract already loaded/sent context. Every newly
started recall checks current time. No new LLM analysis or reasoning is added.

## Maintenance and failure recovery

`MemoryRetentionService.run` identifies/counts eligible rows using database
aggregates for dry-run. Execute discovers at most batch-size records and
batch-size challenges, acquires their owner locks in sorted order, rechecks
eligibility, and removes them in one transaction. Child rows are not locked
before owners. This reuses 6A/6B serialization with saves, control changes,
guarded mutations and legacy deletions. Receipts and controls are never removed.
Undo FK cascade clears only the deleted records' operations. Stale expected
operations cannot undo another record or create a success receipt.

Each invocation defaults to one batch, with `--max-batches` integer 1–10000.
Each category has its own row bound; undo rows cascade one per record. Results
give category counts, completed transaction count and generic failure status.
Counts describe only committed batches. A DB error rolls back that batch;
earlier commits survive. Process interruption before commit rolls back through
PostgreSQL connection termination; after commit a repeated invocation safely
continues. The DB is the resume source; no durable worker cursor is needed.
Concurrent invocations can select overlapping candidates, but owner locking
and rechecks make the second deletion count zero. A no-op committed batch may
end an invocation during a race; later invocation drains remaining eligible rows.

Run from repository root with server DATABASE_URL set privately:

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env python apps/server/cleanup_memory_retention.py --dry-run
uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env python apps/server/cleanup_memory_retention.py --execute --batch-size 100 --max-batches 10
```

Only trusted operators with database privileges run this CLI; it has no HTTP
maintenance endpoint and no owner override available to authenticated users.
Use Windows Task Scheduler/cron/systemd timer to run execute hourly, retry generic
failures, alert on a growing dry-run backlog and receipt-table size, and choose
batch limits for database load. Expired rows remain excluded even if scheduling
fails. This is an operational recommendation, not a deployed job.

**AUTOMATIC SCHEDULING: NOT DEPLOYED**

Durable receipts grow with successful mutations, beyond the 200-record memory
limit. Operators must budget storage and monitor growth. Future bounded receipts
require independently verified terminal-key fencing before removing any receipt.
No legal-compliance claim is attached to these product retention durations.

## Phase 6D expired duplicate decision

Expiry does not itself extend a record or release its unique content key. When
a fresh candidate passes provenance/scope validation and durable consent/pause
checks, the store takes the existing owner lock, examines the scoped content
collision, and removes it only if `expires_at <= current UTC time`. It inserts a
new ID, creation/expiry and undo operation in that same transaction. Old undo
cascades; rollback restores the original row and operation. Active duplicates
remain duplicates with unchanged dates. Unauthorized/paused requests cannot
remove the expired row. Concurrent resaves yield one save and one duplicate.
No schema, graph, background worker or new lifetime-refresh operation is needed.

This behavior is verified by signed Agent HTTP tests, SQL rollback/concurrency
tests and the standalone in-memory store. The expired Golden retention fixture
includes the resave expectation. Scheduler and production backup readiness remain
separate from these passing engineering gates; see the readiness checklist in
[backup/deletion policy](MEMORY_BACKUP_DELETION_POLICY.md).
