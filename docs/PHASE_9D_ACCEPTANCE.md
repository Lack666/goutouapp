# Phase9D — Data Deletion, Retention and Backup/Restore Consistency

PHASE: Phase9D — Data Deletion, Retention and Backup/Restore Consistency.

STATUS: PASS (controlled local synthetic scope; production acceptableFALSE).

ROADMAP PREFLIGHT: clean60f12d64250f2bca23c24a993f66264eb2066b78,
codex/phase9c-resource-admission, one worktree, completed8/9C. Current task branch
codex/phase9d-data-lifecycle.9C original independent pre/post exit0/hash gates
validated in fresh baseline root exit0 (671 Backend,363 Mobile,67 repository).
No9D scope existed; this explicit instruction registers it in MASTER_PLAN and
adds a strict marker/evidence validator without completing Phase9.

DATA LIFECYCLE INVENTORY: DATA_LIFECYCLE_INVENTORY covers all17 application tables,
identities, primary Memory/import/Agent/private files, authorization/retry metadata,
logs/evidence/backups/future copies with ownership, sensitivity, retention, delete
capability/gaps, dependencies/copies and concrete test references.

DELETION CONTRACT: DATA_DELETION_CONTRACT defines actual guarded Memory deletion,
Undo, unfinished import cancel, physical TTL/terminal cleanup and recovery-point
scope. Exact structured IDs; no text matching or enlarged cascades.

RESOURCE DELETION COVERAGE: public Memory and unfinished Job/source lifecycle
implemented. Account/Person/Relationship/Conversation/Agent-history/external-message/
imported-dataset deletion **NOT IMPLEMENTED**; required future contracts/priorities
listed. No new public endpoint, OpenAPI/client change or user data erasure promise.

MEMORY DELETION: owner lock/challenge snapshot/expiry/revoke/receipt/key behavior
retained. Same-key replay cannot touch later records; foreign challenge/receipt
denied. Fresh current-primary exact-ID reconciliation covers Undo/delete-one/person/
all/retention without reconstructing broad scope from receipt count.

IMPORT DATA DELETION: cancel/finalize/expiry raw cleanup preserves formal imports;
exact duplicate same-scope Dataset retains canonical receipt/occurrences while
duplicate Job/source remains independent. RelationshipMessage delete API absent.

RETENTION POLICY: active180d/challenge expiry+24h grace/artifact72h/orphan1h defaults
unchanged; expiry excludes recall immediately; physical cleanup separate. Controls
and receipts stay owner lifetime, no cleanup. Real Agent recall/write regressions.

AUTOMATED MAINTENANCE: opt-in operator loop, real short cycles with counters/retry,
bounded Memory batches/keyset artifact scan, resumable scan cursor, root OS lock,
aggregate backlog/occupancy. Permission failure is failure, busy is skipped.
Production OS schedule/monitor/alert/supervisor NOT DEPLOYED.

ARTIFACT CLEANUP: Job then Artifact lock/recheck, actual unlink before final state;
all-state mismatch handling and failure retries. Worker death after actual unlink
before DB commit exercised in an owned spawned process; next scheduled pass repairs.

QUOTA RECONCILIATION:9C actual files/fences remain authority; errors/timeouts retain
charges while bytes exist; missing file releases physical charges and state repairs.
Unknown-owner files fail closed until grace cleanup, active sources protected;
concurrent upload/finalize/cleanup and multi-process maintenance contention tested.

BACKUP POLICY: BACKUP_RESTORE_POLICY distinguishes current synthetic temporary
unencrypted archives from future encrypted daily/35d rotated copies and key custody.
No raw Artifact/fence/spool files, secrets, roles, WAL or evidence in the DB archive.

BACKUP / RESTORE DRILL: actual local PostgreSQL16.15 native pg_dump/pg_restore,
migrated synthetic source and separate generated target, two owners, legal Memory,
Person/Relationship/Conversation, signed anonymous import. No real database restore.
Native/drill finalizers clean archives/targets. Final operator host scan removed
three first-failed-test fixtures outside their cleanup region; then0 native dumps
and0 disposable DBs remained. Only metadata/log evidence is committed; see
PHASE_9D_CLEANUP_INITIAL.json and PHASE_9D_CLEANUP_CHECK.json.

RESTORE DELETION CONSISTENCY: old backups visibly contain deleted rows before
reconciliation. Current primary write freeze → exact owner/ID survival + current
controls/receipts/valid Undo → invalidate old challenges → cancel pending restored
imports/empty new root → verify. Before/after/concurrent-snapshot delete, new post-
backup records, repeated receipts, other Person/owner, expiry and rollback verified.
Missing/incomplete current primary keeps recovery private; production disaster
recovery and access cutover NOT IMPLEMENTED. Post-backup new data is explicit loss.
Issued Agent keys also require matching restored run/scope/fingerprint; missing
post-backup keys reject release rather than treating an old request as new.9D-01/P1
was reproduced (1fail/1pass) and fixed (2pass); original logs/exits are retained.

OWNER ISOLATION: genuine signed A/B APIs, foreign Memory/challenge/receipt/Job
denials; no Artifact read endpoint exists. Restore composite FKs/owned Memory and
import/read/replay protect B from A scopes. Operator recovery has no public route.

MUTATION IDEMPOTENCY: durable known receipt and original key work after restore and
challenge cleanup; conflicting payload/key rejected, later records preserved.
Mobile unknown outcome/restart stays conservative; no durable outbox claimed.

CONCURRENCY / CRASH RECOVERY: formal deletion transaction vs frozen recovery,
concurrent upload/finalize/cleanup, held unlink physical budget, actual maintenance
process death and OS multi-process contention; retained9C real two-worker TCP and
live DB-loss fencing remain mandatory current-source regression.

PRIVACY / LOGGING: fixed count/error outputs; no exception/SQL/private content/token/
password in operator/native errors. Synthetic sentinels and read-only historical/new
credential screen; dump/raw files excluded from committed evidence. Pattern screening
is separate from reviewed synthetic provenance and cannot establish general PII absence.
Final screen256 files/zero hits; PHASE_9D_EVIDENCE_PRIVACY.json records inventory
SHA256 b5ba5d4f2c0067dad60df41adfd3c853c9ce2f1a80e46496e71afc15b7d088b1.

PRODUCTION DEPLOYMENT LIMITS: no installed monitored scheduling, encrypted backup
rotation/key platform, independent journal/WAL or production restore release; no full
erasure APIs, production identity, provider, RAG or public deployment certification.
Current local R-06/R-09 mitigations do not waive R-07/R-08/production prerequisites.

REAL POSTGRESQL E2E: all new lifecycle/recovery tests use migrated disposable real
PostgreSQL, actual native archives/restores; no SQLite substitution or real model key.

BACKEND TESTS: complete pre/post715 PASS each. Final new/retained focused122 PASS,
current-source9C27 PASS;9D adds44 actual PostgreSQL/maintenance/restore cases.
No old test deleted/skipped/weakened. Repository evidence gate adds7 cases.
The old future-stage assertion changes9D→9E only because9D is now explicitly
authorized; prior native/security requirements remain verified.

MOBILE TESTS: complete pre/post363 PASS each; source/dependencies unchanged, retain existing full suite
and all Web/native fingerprint gates. No fresh9D native run claimed.

ROOT VERIFY: baseline complete exit0; final-source independent complete pre/post
exit0 each,715 Backend/363 Mobile/74 repository/83 Golden; OpenAPI36, Doctor21/21,
Web22 plus connected3/3/4/5/1. All Phase0–8/9A–9C/native fingerprint gates retained.
Earlier attempts retained separately, not counted as final acceptance.

PRE-MARKER EXIT CODE:0 (independent complete final-source root,8/9C).

POST-MARKER EXIT CODE:0 (separate independent complete final-source root,8/9D).

SECURITY RISK REGISTER: PHASE_9D_RISK_ASSESSMENT supplements immutable9A/9B/9C;
no confirmed new open P0/P1 under controlled local topology. R-06/R-09 production open.

FILES CHANGED: maintenance/recovery services and CLIs/demo, cleanup/retention,
real lifecycle/restore tests, strict verifier/privacy/evidence gates, inventory/
delete/retention/backup contracts, ADR0039, risk/threat/architecture/roadmap/handoff.
No database migration or dependency/lockfile/client/Runtime/knowledge changes.

ARCHITECTURE DECISIONS: ADR0039; existing PostgreSQL/local storage/services/fences;
authoritative-primary recovery barrier avoids inaccurate scope replay. No new
infrastructure or exact-ID ledger; disaster recovery without primary stays blocked.

PROJECT PHASE MARKER:8/9D after final-source complete pre-marker exit0;
independent complete post-marker exit0. Phase9 remains IN PROGRESS;10–12 PENDING.

NEXT: subsequent reliability/security final-acceptance scope requires explicit user
instruction under current MASTER_PLAN/handoff. Stop after9D; no10/11/12 or real LLM.

Commands: `.\make.cmd verify` separately for baseline/pre/post; locked uv pytest
focused and full; locked uv Python backup_restore_demo; current-source entire9C
pytest. Environment: TEST_DATABASE_URL uses loopback127.0.0.1:15434/goutou_test,
PYTHONUTF8=1, Chrome path, System32 PATH and unique basetemp/cache directories.
No secrets supplied in argv or committed. Original process outputs/exits retained
and SHA256 linked by PHASE_9D_MATRIX; prior matrices/evidence not overwritten.
The first complete pre-marker attempt exited0/713 Backend and all old/new gates,
but was superseded while the additional Agent-key reproduction/guard was added;
it is intermediate evidence only, not the final pre-marker acceptance. A fresh
complete current-source root is required after that fix.

Invocation history: baseline attempt1 exit1 used unavailable development template
port; attempt2 exit1 completed670+1 sandbox symlink skip but Expo compatibility
network EACCES blocked. Approved host attempt3 complete root0/671 and all gates.
New focused attempt1 exit1 (32pass/3fail) exposed test fixture attempting a save
while delete-all had revoked/paused Memory; corrected by explicit regrant/resume,
preserving safety guards. Demo attempt1 exit1 lacked initial consent; corrected by
formal consent grant before Agent save. Focused attempt2 exit0/71 and demo attempt2
exit0/native recovery. Failed original logs/exits preserved; none counted PASS.

Final pre-marker attempt exit1 stopped in old9C admission regression (26pass/1fail):
second request expected429 but returned201. Minute rollover is a plausible inference,
not established by that failed run. The test now executes the actual PostgreSQL
clock query with a controlled returned minute; all original rejection assertions
remain, plus next-minute201. Production admission code unchanged. Entire current
9C suite27 PASS; failed pre-marker log/exit preserved separately.

A further complete pre-marker attempt passed separate9C27/9D44/demo gates, then
failed in the backend full suite (714pass/1fail): fourth real TCP upload returned503 instead
of429 in a minute-window test. Cause was not observable after fixture teardown.
All three TCP rate-window tests now use the same controlled minute in their spawned
workers, still execute actual PG SQL/transactions and preserve original status,
owner, privacy and cancellation assertions. No production time/rate code changed.
This independent failed log/exit is also retained and never counted as acceptance.

Next complete pre-marker exit0:715 Backend/363 Mobile/74 repository/83 Golden,
all Web/native/hash gates. Initial post-marker exit1 exposed an obsolete9A test
expecting now-authorized9D rejection.9D gates correctly accepted its complete
evidence. The future-stage assertion now rejects9E; native/old-security checks
remain, and9D source fingerprint also binds that changed test. Reverted marker
to8/9C and retained both processes; final source requires fresh full pre/post.

Final closure: fresh complete final-source pre-marker exit0; then8/9D marker,
74 repository tests and all actual marker/native/security gates rechecked;
independent complete post-marker exit0. PHASE_9D_MATRIX statusPASS/closed binds
current source, separate full process logs/exits and unchanged historical9C hash.
