# Phase 6C acceptance

Date: 2026-10-08 (Asia/Shanghai).

PHASE: Phase 6C — Memory Retention, Expiry and Backup/Deletion Policy

STATUS: PASS

ROADMAP PREFLIGHT: Started at `completed_phase=5`, `completed_subphase=6B`,
clean worktree, HEAD `4c72a6f`. Read AGENTS, MASTER_PLAN, ARCHITECTURE,
SKILL_CONTRACT, MEMORY/API/DELETION, ADR 0015/0016/0026/0027 and Phase
3G/3H/6A/6B acceptance. Only Phase 6C was implemented.

EXISTING IMPLEMENTATION AUDIT: Public undo/delete already used 6B expected
operation IDs, confirmation snapshots and durable owner/key receipts. Both
AgentService transports set guarded undo, after safety routing; no user-accessible
unguarded destructive path was found. Direct standalone Python undo/delete remain
trusted programmatic contracts, not public endpoints. MemoryRecord had no expiry,
and recall did not filter by time. Challenges already had expires_at/consumed_at;
receipts had performed_at/created_at and no cutoff. Physical record deletion
already cascaded its associated operation. Delete-person matched structured
Person IDs across Relationships, excluding user-level text and Person entities.

RETENTION INVENTORY: MEMORY_RETENTION.md is authoritative for all nine requested
categories: records, controls, undo history, receipts, challenges, operation
metadata, logs, backups and external copies. Each has purpose/storage/owner,
trigger/duration, expiry/deletion, backup boundary and implementation status.

ACTIVE MEMORY POLICY: Finite creation-based default 180 days, configurable
prospectively, plus user deletion at any time. Ordinary recall and duplicates
do not renew. This is a product decision, not a legal-compliance claim.

RETENTION CONFIGURATION: Server Settings validates MEMORY_RETENTION_DAYS
(180, integer 1–3650 days), MEMORY_CHALLENGE_CLEANUP_GRACE_HOURS
(24, integer 1–8760 hours), MEMORY_CLEANUP_BATCH_SIZE (100, integer 1–1000).
CLI max-batches is integer 1–10000. Invalid configuration cannot execute cleanup.
Receipt retention is a fixed durable-owner-lifetime rule with no unsafe cutoff.

EXPIRATION MODEL: Non-null indexed PostgreSQL timestamptz expires_at;
aware UTC Python contract, separate creation/update/expiry timestamps.
Exact expiry is excluded (`expires_at <= now`). Injectable clocks prove
before/at/after boundaries for both SQL and standalone recall.

LEGACY RECORDS: Migration 20261008_01 grants existing records migration
transaction time + 180 days. An actual year-2000 record migration test verifies
unchanged creation time and a full future grace, without immediate cleanup.
Settings changes do not rewrite existing expiration dates.

QUERY-TIME EXPIRY: SQL list/recall queries exclude expired records immediately;
MemoryService repeats the gate for non-SQL stores. Physical removal is separate.
Already loaded or sent in-flight context cannot be remotely retracted.

USER-FACING EXPIRY CONTRACT: Additive expires_at/state/retention_policy_summary
fields on public Memory views. Empty lists still carry the summary. Default
lists show active records. Owned GET-by-ID can show expired records until cleanup;
foreign IDs remain 404. Inspectability never enables Agent recall.

CLEANUP SERVICE: Deterministic MemoryRetentionService, typed counts/result,
aggregate dry-run and bounded execute. No Agent, provider, router or relationship
analysis is invoked, and no maintenance HTTP endpoint is exposed.

CLEANUP BATCHING: Default one committed batch, maximum batch-size Memory rows
and batch-size challenges per transaction; repeated invocation resumes from DB
state. No unbounded content load or distributed worker is introduced.

CLEANUP TRANSACTION SAFETY: Discover bounded IDs, lock owners in sorted order,
recheck eligibility, delete and cascade atomically. Real PostgreSQL divide-by-zero
after deletion proves rollback of an uncommitted batch while earlier committed
batch counts remain. Abrupt subprocess exit proves rollback and safe retry.
Concurrent maintenance and mixed save/revoke/user-delete tests complete without
deadlock or pseudo-success. Counts publish only after transaction commit.

UNDO / EXPIRY INTERACTION: Expired latest preview is unavailable. A previewed
target expiring before undo yields unavailable; after cleanup a different latest
ID yields stale. Serial and concurrent tests verify no fallback to A when B
expires, no success receipt and no orphan operation for B. Only affected record
operations cascade; A survives.

CHALLENGE LIFECYCLE: Existing five-minute validity remains. Pending, expired,
consumed and snapshot-stale challenges clean at expires_at + configured grace.
No persisted invalidated state exists. Valid challenges are not removed; deleted
challenges fail closed. Deterministic tests cover expiry and cleanup boundaries.

RECEIPT LIFECYCLE: Strategy A: durable receipts for owner lifetime, including
indefinite same-key replay while metadata exists. There is no expired key or
physical receipt cleanup. Matching retries work after challenge removal and
changed payloads conflict. Far-future maintenance retains receipts. Storage
growth is an acknowledged operational cost; terminal-key fencing is deferred.

PERSISTENT IDEMPOTENCY REGRESSION: Confirmed delete → challenge cleanup →
same-key retry replays original receipt without a second delete or reconfirmation.
Same-key undo retry concurrent with maintenance preserves original receipt.
6B preview, undo, delete-one/person/all, stale/expired confirmation, conflicting
payload, concurrent mutation and receipt-write rollback tests all pass.

CONSENT INDEPENDENCE: Retention does not grant/revoke/pause/resume. Revoke-and-keep
continues aging and cleanup. Resume/grant cannot revive expired rows. Delete-all
still takes its explicit revoke flag, unchanged.

PERSON / RELATIONSHIP SCOPE: Existing owner and Person/Relationship isolation
and composite FKs remain. Person deletion uses structured associations and
cannot search arbitrary user-level text for mentions or clear all system domains.
Agent, Conversation, RelationshipMessage, import and identity data are outside
this cleanup scope.

BACKUP POLICY: MEMORY_BACKUP_DELETION_POLICY.md distinguishes actual capability
from design. No production backup infrastructure is deployed. Planned daily
encrypted backups have a maximum 35-day rotation, restricted operator access,
separate key custody and copy inventory. No automatic backup erasure is claimed.

RESTORE SAFETY: Old backups can resurrect deleted Memory and lose retry-key
metadata. The design runbook requires quarantine, a trusted post-backup source/
WAL or exact deletion journal, reconciliation, receipt/control verification,
synthetic recall and evidence before reopening. Receipt IDs/scopes cannot always
reconstruct exact bulk deletion sets. With incomplete evidence, keep Memory
closed; conservative purge/control reset and receipt recovery require operator
review. No restore replay automation or backup/restore exercise is claimed passed.

LOGGING / PRIVACY: Metadata holds IDs/scopes/time/fingerprints/counts, no additional
Memory content/evidence/chat/JWT/hidden reasoning. CLI stdout gives only counts
or generic failures; subprocess privacy checks exclude saved content and DB URL.
Logs, provider copies, artifacts and imported messages have explicitly different
boundaries. Planned production log rotation is 7 days, not deployed.

MAINTENANCE CLI: apps/server/cleanup_memory_retention.py supports required
--dry-run / --execute, --batch-size and --max-batches. Real subprocess tests and
the demo run against PostgreSQL. Operators can schedule hourly one-shot runs;
there is no public maintenance transport or deployed queue.

AUTOMATIC SCHEDULING STATUS: **AUTOMATIC SCHEDULING: NOT DEPLOYED**.

POSTGRESQL INTEGRATION: PostgreSQL 16.15 in a fresh localhost-only temporary
cluster on port 15434, with separate disposable goutou_test_* databases. Docker
was unavailable. Initialization used an ASCII binary-path alias to handle Windows
PostgreSQL's failure on the repository's Chinese path. No existing production
DB was used. The independent temporary cluster was gracefully stopped after
validation. The failed broad process-stop attempt was rejected by automatic
approval review; validation proceeded in an independent cluster instead.

RUNTIME INTEGRATION: Actual AgentService → standalone LangGraph runtime →
MockLLM + PostgreSQL; active recall, expired exclusion, pause/revoke and owner/
Person/Relationship isolation verified. Three standalone clock-boundary tests
also prove filtering without SQL. No real provider/API key was needed.

STANDALONE DEMO: memory_retention_demo.py grants explicit consent, saves active
and synthetic expired records, recalls only one, runs CLI dry-run unchanged,
removes one expired row and undo operation, verifies through new sessions,
repeats cleanup with zero removals, cleans one consumed challenge, and replays
the original receipt while a new saved record survives.

TESTS: Focused retention **26 passed**; Phase 6A **7 passed**; Phase 6B
**10 passed**; full backend **416 passed**. Two new synthetic Golden retention
fixtures bring inventory/routing/schema coverage to **83** cases; existing
24/30/38/14 Mock replay subsets and all earlier gates remain unchanged.
The focused set covers policy/settings, SQL and standalone time boundaries,
existing-row migration, public expiry, Agent recall, isolation/control, dry-run,
batching/idempotency, rollback/interruption, cleanup races, undo races, challenges,
durable receipt/replay/conflict, CLI privacy and documentation consistency.

VALIDATION: .\make.cmd verify **PASS**, exit 0: all active Phase 0–5, 6A, 6B
and 6C gates. Alembic cycle/check, 83-case Golden/routing, all Mock replays,
frozen upstream, secret boundary, Ruff check/format and git diff --check **PASS**.
Full backend **416 passed**, focused retention **26 passed**, real CLI/runtime
demo **PASS**. Commands used:

```powershell
$env:TEST_DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:15434/goutou_test'
$env:DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:15434/goutou_dev'
$env:PYTHONUTF8='1'
$env:PYTHONUNBUFFERED='1'
$env:PYTEST_ADDOPTS='--basetemp=.cache/phase6c-pytest-final -o cache_dir=.cache/phase6c-pytest-cache-final'
.\make.cmd verify
git -c safe.directory=F:/狗头军师app化/goutouapp diff --check
```

All Python commands use uv --cache-dir .cache/uv --no-managed-python run --locked
with the ignored .env; process DB variables override its development URLs.
Alembic upgrade/downgrade/upgrade/check, Golden/replays, frozen upstream, secret
boundary and Ruff check/format are in the full gate. Logs are local ignored
.cache/phase6c-verify-final.log. Early verification failures were environment
tmp ACLs/project-triggered pnpm download, then verifier formatting; they were
resolved without changing library/package versions or masking test failures.

ARCHITECTURE DECISIONS: ADR 0028 accepts fixed finite expiry, legacy transition,
query-time exclusion, bounded owner-lock cleanup, challenge grace, durable
receipts and honest backup/scheduling boundaries. No new dependency was added.

FILES CHANGED: .env.example; server README; MemoryRecord contract, MemoryService,
SQL MemoryStore, ORM rows, Settings, API/runtime composition, public Memory view,
guarded mutation expiry check; new app/retention.py, services/memory_retention.py,
Alembic 20261008_01, cleanup CLI, retention demo and focused tests; 6A public-field
and Golden count tests; Golden fixture JSONL/evals README; docs MEMORY_RETENTION,
MEMORY_BACKUP_DELETION_POLICY, MEMORY/API/DELETION, DATABASE, ARCHITECTURE,
MASTER_PLAN, ADR 0028, this acceptance; verifier and final phase marker.

KNOWN ISSUES: Durable receipts can grow beyond the bounded Memory record count.
Expired rows reserve duplicate keys and storage capacity until maintenance;
in-flight context cannot be retracted. Production scheduling/backup rotation,
encryption, independent deletion journal and restore reconciliation are not
deployed or verified. Installed pnpm is 11.7.0 versus the future JS workspace
pin 11.25.0; doctor checks installed versions outside the project to avoid an
unrequested auto-download. No JS dependency/build gate is active before Phase 7.
Windows sandbox tmp ACLs require an accessible isolated pytest base directory
and unsandboxed verification here; no unsupported check is recorded as passed.

DEFERRED: Phase 6D, Phase 7 Mobile, RAG, queues, real model quality, complete
account/all-chat deletion, backup service, automatic scheduling and restore replay.

PROJECT PHASE MARKER: completed_phase=5, completed_subphase=6C, updated only
after the full gate passed. Phase 6 remains in progress; 6D is pending.

NEXT: Phase 6D — Memory Controls End-to-End and Phase 6 Final Acceptance.

Stop after this acceptance. Phase 6D and Phase 7 have not been started.
