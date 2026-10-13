# Upload reliability — Phase 9C

Normal flow: early rate/authentication → atomic full reservation/OS fence → bounded
Multipart receive → one private immutable artifact → bounded speaker preview →
transactional Job registration → response → slot release. The retained source
remains charged until actual deletion. Exact raw fingerprints, explicit bindings,
revision checks, merge locks and durable receipts retain Phase5 semantics.

On size/form/parser/write/registration failure, existing form cleanup closes spool
handles and the route aborts/deletes its source. Failure cannot create a successful
Job; transactional metadata rolls back. ENOSPC begin/write now return the existing
storage503 contract, without paths or native errors. Cleanup failure warns with
the existing fixed whitelist message and retains physical charges for retry.

Finalize capacity is separate from upload capacity; normal imported replay remains
server authoritative. A busy admission may refuse503 before service execution;
retry the same known Job/revision explicitly. Cancel is not charged an upload or
processing slot. Existing Job serialization yields imported+complete rows/receipt
or cancelled+zero rows; neither reconciliation nor maintenance edits committed receipts.

Connection-owned DB locks alone are insufficient crash proof: DB disconnect can
leave a process alive. The private OS fence remains authoritative even then. No
timestamp expiration reissues its capacity. Real worker termination during body
receive, partial write and completed-artifact-before-Job-commit releases the OS
handle. The next guarded reconciliation retains residual bytes and frees the slot.
An unresponsive living worker must be diagnosed and stopped by the supervisor;
do not steal its fence. Kernel/filesystem hangs and process supervision remain
deployment conditions, not application request-body timeout claims.

Privileged maintenance reconciles fences, invokes existing expiry/orphan cleanup,
then reports actual occupancy again. Active reservations protect pre-registration
.part/.bin even beyond the orphan grace. Unknown-provenance files remain visible
as aggregate charged/unattributed bytes, allowing maintenance while admission
fails closed. One-hour orphan grace and72-hour default source retention remain.
The CLI prints fixed/count-only output and suppresses exception chains on failure:

`uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env python apps/server/import_artifact_cleanup.py`

This is an explicit maintenance command, not an installed production scheduler.
R-06 still requires monitored scheduling/backlog drain, primary retention SLA and
backup/restore/deletion propagation. R-09 production identity and full-system
deletion remain separate. Never point maintenance at user transcripts or a different
server root. Test fixtures use newly migrated synthetic `_test_<random>` databases.

Client compatibility: existing413/429/408 map to safe failed HTTP uploads; shared
503 stays conservatively unknown_outcome because other server503 cases may be
post-dispatch uncertainty. It cannot display import success or automatically retry.
Transport retains HTTP status/unavailable separately from offline/timeout; raw
server strings are discarded. Known Job IDs can be inspected; unreceived upload
IDs cannot be recovered. No upload operation lookup/idempotent retransmission added.
Mobile source/dependencies remain unchanged; four new tests verify these semantics.
9B Android evidence remains for its unchanged source/dependency fingerprint;9C
does not claim a new native run.

The real two-process TCP suite covers shared Owner/global concurrency and rates,
idle/total receive deadlines, disconnect/kill recovery, partial/complete crash files,
ENOSPC, storage exhaustion, DB unavailability and continued legal requests. Additional
signed FastAPI/PostgreSQL tests cover storage attribution, pending/form limits,
atomic reservation races, live DB-loss fencing, cancel/finalize/replay, old live
partials, cleanup failure, policy mismatch and bounded hostile speaker inventories.
The previous96 upload/auth/privacy cases and full baseline regression remain active.

Deployment remains local: observed existing PG127.0.0.1:15434 only; disposable test
workers bind127.0.0.1 on private ephemeral ports and are terminated by their fixture.
No public gateway is deployed/tested. Before public use require TLS, bounded headers/
connections and non-upload bodies, trusted proxy configuration, connection/pool/
filesystem sizing, private root/fence ACLs, supervisor and monitored retention.
Application bounds do not certify arbitrary tunnels, distributed replicas, host
quota writers, maximum process RSS or public flood resilience.

The9B Windows Playwright worker exit3221226505 remains an unconfirmed P2 environment
risk. A recurrence must preserve the failed invocation and collect safe environment/
exit metadata; no removed assertion, hidden retry or invented root cause is allowed.
