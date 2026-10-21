# Retention maintenance — current Phase9H

## Current9H authority

Current9H maintenance additionally cleans expired lifecycle confirmations using
the existing owner-serialized expiry/grace policy. Immutable lifecycle/recovery
receipts and original key/UUID/dedup fences survive cleanup for the owner fence
lifetime. Existing artifact/Memory controls remain; no supervised production
scheduler or independent disaster-recovery authority is added. Dated baseline
sections below remain historical; see the Current9H supplement.

## Historical phase-specific contracts

### Retention maintenance — current Phase9E

9E extends existing bounded challenge cleanup to erasure_confirmations:5min validity
plus24h grace, at most configured batch_size per challenge domain per transaction,
sorted owner locks and post-lock eligibility rechecks. Receipts/tombstones are never
removed. Existing Memory expiry, all-state Artifact cleanup, retry, cursor, OS root
lock and admission reconciliation remain. CleanupCounts.confirmation_challenges
includes both domains; successful erasure replay survives challenge cleanup.

Local isolated scheduled execution, worker crash/restart, competing processes/root
contention, cleanup failure/retry and capacity recovery are rerun in test_data_lifecycle
and test_resource_admission. Independent erasure_demo schedules three actual local
cycles and native dump/restore. This is opt-in local loop execution, not an installed
production scheduler. OS registration, host supervision/alerts/backlog monitoring
and production deployment remain NOT DEPLOYED.

## Retained9D bounded maintenance procedure

Memory expiry, access exclusion and physical deletion are separate events.
New Memory defaults180d; SQL/standalone recall and default lists exclude expiry
at the exact boundary even with maintenance stopped. Explicit owned inspection
can still show expired data. New saves recheck consent/pause and expired collision
under owner lock, create a new UUID/expiry/undo, and cannot renew active duplicates.
Challenges cleanup at expiry+24h grace; receipts/controls never age out. Artifact
TTL72h; orphan grace1h; terminal finalize/cancel attempts immediate primary unlink.

The9D operator-only loop composes existing ResourceAdmission reconciliation,
bounded MemoryRetentionService and ImportWorkflow cleanup, followed by an actual
occupancy snapshot. It has no HTTP route, Agent/provider call or external scheduler
dependency. Multiple loop instances use a private OS advisory fence keyed to the
canonical artifact root. Process death releases that lock; a live slow worker is
not evicted on elapsed time. PostgreSQL statement/lock deadlines bound DB waits;
an OS unlink can hang and requires a supervisor to stop the worker. No thread is
abandoned while pretending its files were deleted.

Each scheduled iteration reports only status, committed counts, eligible backlog,
safe error category and aggregate physical/accounted bytes. A failed iteration
increments a failure counter and is retried on the next interval; earlier committed
batches are preserved. A competing instance reports skipped, never success for
work it did not execute. Terminal DB metadata is not evidence of physical deletion.
Cleanup scans all Artifact states in bounded keyset pages, cancels/rechecks Jobs
under their usual Job lock, attempts unlink before publishing final Artifact state,
and retries failed/old inconsistent states. Live reservation keys are protected
from orphan sweep. Fresh unknown-owner remnants continue charging/blocking admission
until grace elapsed or operator review; count-only reconciliation remains available.

Scheduling defaults60s in the opt-in CLI. Memory batch100/max10, Artifact page100
with one locked transaction per Artifact, max10 pages (1000 metadata rows) per
scheduled pass; the compatibility one-shot defaults100 pages (10000 rows). A
resumable loop cursor covers larger metadata sets across scheduled passes. File
inventories still follow9C's fail-closed10000 limit. Production
must tune interval/load, protect root/fence ACLs, monitor backlog/receipt growth,
alert on failure/missed schedules/unattributed bytes and supervise hung processes.
No unattended startup, OS task registration, alert collector or production SLA
is installed by9D. Local short-interval and controlled-clock tests prove the loop.

Command (private server environment; explicit operator execution):

`uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env python apps/server/retention_maintenance.py --interval-seconds 60`

`--iterations N` bounds a controlled run; interrupt stops between iterations.
The existing one-shot CLIs remain available. Test execution uses only newly migrated
synthetic databases and temporary roots. No raw file, JWT, password, body, Owner,
Memory or exception string is printed. Count-only operator output is not public API.

Evidence: test_data_lifecycle.py (short periodic execution, failures/retry, race,
physical mismatch, quota, lock competition), retained test_memory_retention.py,
test_resource_admission.py (real worker deaths/live DB-loss/upload races),
test_backup_restore.py (restore physical/metadata policy). Production scheduling:
**NOT DEPLOYED**.


## Current Phase 9H

The existing bounded MemoryRetentionService also removes LifecycleConfirmation after
expiry plus the existing24h grace, under sorted owner locks. It never expires
LifecycleReceipt/RunRecoveryReceipt or original Agent/import anti-resurrection keys.
Owner clearing preserves these minimal owner-lifetime fences. Active upload and
unresolved Agent writer proof cannot be bypassed by maintenance or elapsed age.
The existing supervised scheduling/alerts/encrypted rotation production gaps remain;
9H adds no unattended service or automatic run reset.
