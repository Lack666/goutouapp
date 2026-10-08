# Memory Backup and Deletion Policy — Phase 6C

Status, 2026-10-08: production backups, backup erasure automation, deletion
ledger export, encrypted backup storage and restore replay are **NOT DEPLOYED**.
The repository's local PostgreSQL validation is not production backup coverage.
This document is an operational design and deployment requirement, not a claim
of verified recovery infrastructure. See [retention inventory](MEMORY_RETENTION.md).

## Backup handling

A full PostgreSQL backup includes Memory records/content, consent controls,
undo history, confirmation challenges and durable mutation receipts, as well
as other database domains. Planned policy: encrypted daily recovery copies,
maximum **35 days** from backup creation, checked rotation every day. Required
controls: encryption in transit and at rest, keys managed separately from copies,
least-privilege operator access, access audit, inventory of all copies and
retention timestamps, and tested deletion of expired backup objects/volumes.
None of those production mechanisms is implemented by this phase.

A user's delete removes app-owned primary Memory and associated undo targets;
it does not rewrite older backups, immediately destroy copies, delete imported
RelationshipMessages, source transcripts, conversations, identities or external
provider data. Offline backups must not be used for serving or analysis and
expire through the planned rotation. Operator exports/copies belong in the same
controlled inventory and maximum retention. Unknown external copies and prior
provider transmissions cannot be guaranteed erased by local DELETE.

Durable primary receipts have no time cutoff. A rotated backup expires after
35 days even if it contains those receipts. Losing current receipts during
restore can lose key fencing, so old client retries must not be accepted against
a restored snapshot without reconciliation. Backup age and primary lifecycle
are separate rules.

## Restore runbook (design only)

1. Record backup timestamp, source, integrity check and restored recovery point.
   Restore into an isolated database with application access disabled. Preserve
   the current database/WAL and safe mutation metadata independently before
   replacement. Do not expose an older snapshot to users first.
2. Identify changes after that recovery point from a trusted current database,
   WAL recovery chain or independently maintained deletion journal. Include undo,
   delete-one/person/all, consent revocations and successful operation keys.
   Receipts hold action, scope, time, counts and fingerprints, but delete-person
   and delete-all do **not** retain the exact deleted ID set. Receipts in an old
   backup cannot reveal later deletions. There is currently no independent
   deletion journal or automatic reconstruction/replay implementation.
3. Prefer a verified WAL recovery point including all acknowledged deletions,
   or reconcile against a trusted current primary snapshot. A future exact-ID
   deletion journal must be reapplied by privileged offline tooling; calling the
   public mutation API with an old key merely replays a receipt and does not
   re-delete restored rows. Scope-only replay can over-delete subsequently saved
   memories and cannot prove exact historical deletion. Do not claim otherwise.
4. If a complete authoritative post-backup history is unavailable, keep Memory
   serving disabled. The conservative recovery option is operator-approved
   removal of **all restored Memory records and undo operations**, plus reset of
   restored consent controls to disabled/paused and explicit reconciliation of
   receipt/key metadata. Never grant consent from an unverified older snapshot.
   This may lose still-valid memories; it must be recorded as a recovery loss.
   If current durable key metadata cannot be recovered, keep destructive mutation
   endpoints disabled until a separately reviewed safe key-fencing recovery plan
   is installed. Phase 6C implements neither a global recovery switch nor this
   purge/reconciliation tooling: isolation is a deployment/operator responsibility.
5. Run migrations/schema check, maintenance dry-run/execute and verify expiration
   exclusion. Inspect primary records by deleted IDs and structured scopes; verify
   no orphan undo targets, current controls, original receipt replay/conflicting
   key rejection, Person/owner isolation and a synthetic Agent+MockLLM recall.
   Validate backups' encryption, copy inventory and next rotation date separately.
6. Document reconciliation evidence, known gaps and responsible operator before
   reopening access. With incomplete deletion or retry-key evidence, do not
   reopen Memory. Do not call this restore-safe deletion replay until a full
   backup → deletion → restore → reconciliation exercise has passed.

Production operations owns copy inventory, scheduling, encryption/key custody,
rotation and restore quarantine. Application engineering owns primary lifecycle
and replay invariants. The deployment owner must implement and test this runbook
before production backup/restore claims are made. Complete account deletion,
all-history deletion and a backup service remain outside Phase 6C.

## Phase 6 final operational readiness

Engineering completion and production deployment are independent. Phase 6D
does not deploy a scheduler, backup system or restore reconciliation tooling.

| Capability | Engineering evidence | Production status / required operator action |
| --- | --- | --- |
| Finite expiry and query-time exclusion | UTC boundary tests, real Agent recall excludes expired rows before cleanup | Code ready; configure finite new-save lifetime before rollout |
| Bounded maintenance CLI | Dry-run, committed counts, FK undo cascade, restart/retry/concurrent cleanup tested | CLI ready; grant only maintenance operator DB privileges |
| Periodic scheduling | One-shot command documented; no worker infrastructure added | **NOT DEPLOYED**; install hourly scheduler, retry and backlog alerts |
| Backup encryption and custody | Requirements documented only | **NOT DEPLOYED**; provision encryption, separate keys, least privilege and copy inventory |
| Daily backups and 35-day rotation | Proposed finite policy documented only | **NOT DEPLOYED**; automate copies, verified rotation and erasure of expired objects |
| Restore isolation | Fail-closed restore runbook documented | **NOT DEPLOYED**; quarantine restored DB and block serving/mutations until reconciliation |
| Post-backup deletion replay | Receipt limits and exact-history requirement documented | **NOT DEPLOYED**; authoritative current/WAL/history reconciliation and full restore drill required |
| Receipt/key durability | Owner/key replay after challenge cleanup and conflicts tested; cleanup removes zero receipts | Code ready; protect current receipt metadata across restore and monitor storage growth |
| Owner/person/relationship isolation | Signed HTTP inspection/mutation and actual Agent recall tested | Code ready; deployment auth/key custody and access audit must be configured |
| Full Phase 5 data separation | Real HTTP import/bind/finalize, memory deletes and cleanup preserve imported and Agent data | Code ready; all-history/account deletion remains outside this scope |

The passing local PostgreSQL + Mock LLM exercise proves primary-store engineering
behavior. It is not evidence of deployed backups or a completed production restore
drill. Do not reopen a restored Memory service with incomplete deletion or key
evidence. Exact reconciliation, global recovery disable controls and purge tooling
remain explicitly deferred.
