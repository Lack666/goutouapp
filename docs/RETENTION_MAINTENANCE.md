# Retention maintenance — Phase 9D

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
