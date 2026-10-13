# Backup / restore policy — current Phase9E

Current9E supplement: the current-primary SHARE write freeze also includes the
new erasure challenge/receipt tables and target tombstones. Exact restored resource
ID/owner/Relationship (and Dataset transcript fingerprint) must match current
primary. Deleted target message/speaker rows are physically removed, tombstone
timestamps applied and current immutable receipts copied. All restored erasure
challenges are invalidated. Missing current metadata or a post-backup tombstone for
a target absent from the backup blocks release; never drop a fence to release data.
Repeated reconciliation is safe. Current Agent key checks and Memory controls/
receipt/undo rules remain. New post-backup data still is not recovered.

No independent deletion journal/WAL authority is implemented. Primary missing,
unavailable, tampered receipt, lagging target or any restore error keeps released=false
and the disposable target inaccessible to API listeners. Tests include actual native
dump/restore, erasure receipt replay and Owner B/Memory preservation. No independent
authority means production full-primary-loss recovery remains unavailable.

Production policy remains future: daily encrypted copies, maximum35d verified
rotation, separate rotated/revocable key custody, least-privilege audited operators,
complete copy inventory, integrity validation, fail-closed cutover and error alerts.
Old copies after a deletion request stay inaccessible to normal users, expire by
copy policy and must be reconciled before serving; copied exports/provider/log data
have separate lifecycle obligations. None of this deployment is certified here.
Local unencrypted anonymous dumps are disposable test evidence, not safe production
backups. No public release or live cutover switch is introduced.

## Retained9D deployment boundary and procedure

Current capability: synthetic-only PostgreSQL logical dump, isolated restore and
authoritative-primary Memory reconciliation with real native PostgreSQL tools.
Production backup platform, encryption/key custody, rotation, independent deletion
journal/WAL recovery, scheduler installation and disaster recovery are NOT DEPLOYED.
Never use the drill on real user data or restore into a production/development DB.

## Contents, access and retention

The archive contains the migrated DB schema/data, private Agent/imported messages,
Memory/control/undo/challenge/receipt data and admission metadata. Raw uploaded
Artifact/fence/spool files, secrets, OS logs/evidence, roles/global settings and WAL
are excluded. It is a consistent database recovery point, not a transactionally
coordinated filesystem snapshot. pg_dump supports concurrent writers; an exported
snapshot lets tests deterministically place a deletion after the recovery point.
See [PostgreSQL16 pg_dump](https://www.postgresql.org/docs/16/app-pgdump.html).

Synthetic archives live in an ignored temporary `.cache` tree with developer/operator
access only. Drill/context finalizers remove their archives/targets; native dump
failure removes an incomplete archive. A test assertion before its cleanup region
can leave a synthetic fixture in ignored pytest cache: the final operator scan
must find/remove these remnants. Three original failed-fixture archives were
removed; final host scan reports zero in PHASE_9D_CLEANUP_CHECK.json. They are intentionally
unencrypted synthetic fixtures; this is no production encryption proof. Passwords
go through private process environment, never argv/logs; subprocess output/errors
are captured and discarded in favor of fixed error codes. Evidence contains counts,
test names, safe failures, independent exits and hashes, not dumps/raw chat files.

Future production: encrypted daily copies maximum35d from creation, daily verified
rotation and physical object/volume removal. Encryption in transit/at rest, separate
key custody/rotation/revocation, audited least-privilege operator roles, complete
copy inventory and restore integrity testing are mandatory. Keys and copies must
not share unprotected storage. Local DELETE cannot rewrite an older archive, and
provider/export/log copies have their own bounded policies. Receipts stay primary
owner lifetime while backup copies still expire after35d. No regulatory claim.

## Executable controlled recovery

1. Only accept separate loopback `postgresql+psycopg` synthetic `_test_<12hex>`
   namespaces. Target is freshly generated/created by the drill and never receives
   an API listener before reconciliation. Dump uses native pg_dump custom format;
   restore uses pg_restore no-owner/no-privileges/exit-on-error/single-transaction.
   [PostgreSQL16 pg_restore](https://www.postgresql.org/docs/16/app-pgrestore.html)
   documents transaction/error behavior. Restore errors fail and quarantine remains.
2. Keep current primary intact. Freeze its lifecycle tables against writes for the
   final authoritative snapshot and reconciliation. This waits for already-started
   deletion/save/control/import transactions to finish; later changes are blocked
   until the reconciliation completes. The tested scope is a controlled offline
   drill, not live cutover. Never expose restored data before this barrier.
3. Reconcile exact owner/Memory survival with current primary, remove restored IDs
   already removed there (Undo/delete/retention/expired replacement included),
   replace current controls and durable receipts, invalidate all restored challenges
   and restore only current undo operations whose target exists in restored Memory.
   Scope-only delete replay is forbidden. Every current issued Agent operation key
   for a restored owner must exist unchanged on its restored Run. Missing newer
   run/key/fingerprint fences reject release; this drill does not reconstruct newer
   Agent run/message history. If current owner scope/schema/key metadata is incomplete
   or mismatches, abort. Repeated reconciliation is safe.
4. Use a fresh empty private Artifact root. Cancel restored unfinished Jobs and mark
   all Artifact metadata deleted; keep formal imports/receipts intact. No raw source
   is resurrected, and users must explicitly re-upload a cancelled pending import.
   Discard restored admission/fence state; interrupted runs fail. Verify SQL FKs,
   actual zero files, available quota, migrations and owner-filtered history/Memory.
5. Run expiry cleanup and actual keyless Agent recall; verify deleted IDs absent,
   owner B nondeleted Memory/history intact, current revocation preserved, known
   receipt lookup/same-key replay and changed-key-request conflict. Report loss of
   post-backup new data separately. No API serving during recovery/failure.
6. Delete disposable target/archive after test. Only aggregated evidence is retained.

No fresh complete authoritative primary means no recovery release. The minimal
barrier deliberately cannot operate as production disaster recovery. A future
independent exact-ID deletion journal/WAL chain plus current controls/terminal-key
fences must be implemented/tested before real-user restore. Hosting an old DB
directly with FastAPI bypasses this operator contract and is explicitly prohibited.
No application-wide production cutover switch is claimed.

Evidence: test_backup_restore.py exercises pre/post/concurrent deletion, actual
dump/restore, exact-ID preservation/new writes, repeated receipt application,
rollback/failure, owner isolation, current controls, Agent recall and empty artifacts.
The command `apps/server/backup_restore_demo.py` runs an independent synthetic
drill and prints only fixed/count evidence. Binaries can be selected using
PG_BIN_DIR;9D tests use the existing local16.15 binaries matching the test server.

9E-01 (P1, fixed): a deleted Dataset must already be a canonical `imported`
Job in the backup. A pre-finalize `ready` Job lacks the partial unique-index
re-import fence; reconciliation refuses release rather than synthesizing newer
import history. Covered by `test_restore_cannot_drop_post_backup_imported_dataset_fence`.
