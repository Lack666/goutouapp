# Security risk register — Phase 9A–9F

## Phase9F current risk status

The sections below this update retain historical acceptance-time findings.
Controlled development acceptance does not certify public production use.

- R-06: 9D bounded maintenance and 9E controlled current-primary restore are
  implemented and regression tested. Monitored production scheduling, encrypted
  rotation, independent deletion journal and lost-primary recovery remain absent.
- R-07: 9C shared-root owner/global reservation, rates and active body deadlines
  are implemented. Trusted production ingress, capacity sizing, supervision and
  deployed monitoring still require separate evidence before public exposure.
- R-08: imported history remains outside Agent/provider analysis. No new provider,
  imported-chat analysis or injection-sensitive reasoning path is added in9F.
- R-09: signed public ownership audit and exact guarded Dataset/Conversation
  erasure are implemented, now exposed through Mobile. Production issuer/refresh/
  revocation and full account/Person/Relationship erasure are still missing.
- R-10: OPEN reliability limitation. pending/running/unresolved-memory AgentRun
  blocks Conversation erasure with target_busy. Controlled development impact:
  a Conversation can remain undeletable (P2); production reliability acceptance
  remains blocked. Existing service fence plus explicit App refresh protects data;
  there is no automatic timeout, forced erase, status rewrite or new-key bypass.
  Tests: test_erasure.py running/unresolved cases; erasureController.test.ts;
  erasure-connected/web.spec.ts; native phase9f_faults.json. Next authorized work:
  define server Run reconciliation and prove a safe terminal state before allowing
  deletion. User-facing copy explains that status may require separate recovery.

9F validation event: one full-backend run and the first root pre-marker run
returned503 in old Person business-concurrency tests. Instrumented repetition
reproduced admission LockNotAvailable/SQLSTATE55P03 at the existing250ms bound
(359/360 pass). The precise historical uninstrumented causes remain unconfirmed.
ResourceFlow now establishes one signed read-only request before business races:
the warmed diagnostic and uninstrumented repetition each pass360/360. All original
mutation responses, concurrency and SQL uniqueness assertions remain unchanged;
there is no response retry, timeout/quota relaxation or production behavior change.
Cold admission remains fail-closed and covered by the existing admission suite.
Independent complete root pre/post passes are still mandatory; failed logs remain.
The second root pre-marker attempt passed Backend761/Mobile396/Doctor21 but
found the old Connected Web network allowlist omitted the new Dataset discovery
GET. Only that exact path is added, with observed-request and GET-only assertions;
existing owner, count and forbidden-deletion checks remain. Its failure is retained.
The first post-marker attempt failed two historical tests still rejecting authorized9F.
Their future-stage rejection now targets9G; all original safety assertions remain.
Marker was reverted8/9E and affected44/88 gates revalidated before final complete
pre-marker r4 and post-marker r2 exits0. Failed logs remain nonzero evidence.
9F-01's separately reproduced upload-promotion/inventory race is fixed with two
new deterministic tests; unknown disappearing files continue to fail closed.

9F native validation event: the second prior-regression batch failed session
controls/login and is retained with nonzero exits. An independent diagnostic
confirmed an unavailable Android accessibility hierarchy; the dedicated emulator
was rebooted and a complete diagnostic login then passed. The precise cause of
each earlier login failure is unconfirmed. Acceptance requires fresh complete
formal scenes on unchanged application/helper source, never diagnostic output.

Historical9E authority: PHASE_9E_RISK_ASSESSMENT.json. R-09 gains tested guarded canonical
Dataset and Conversation deletion, metadata-only durable receipts and replay fences;
full-account/Person/Relationship erasure, production identity and App chat deletion
remain formally unfinished. R-06 restore extends exact primary reconciliation to
both targets; no independent journal or primary-loss production recovery. R-07 local
admission topology remains tested; deployed ingress/host sizing/supervision stay
blocked. R-08 imported analysis/provider integration remains absent and blocked
pending explicit source/authorization/retention contracts. All four include controls,
test evidence, remaining work, development/production risk and next task. Public
production acceptableFALSE; prior JSON/matrices/evidence remain immutable history.

Current9D authority: [PHASE_9D_RISK_ASSESSMENT.json](PHASE_9D_RISK_ASSESSMENT.json).
R-06 is mitigated for tested local periodic primary maintenance/retry/resource
reconciliation and native synthetic restore with an intact authoritative current
primary. R-09 Memory deletion/owner/key semantics remain protected and restore
controls/receipts now reconcile. Neither risk is closed for production: installed
monitored scheduling, encrypted rotation/key custody, independent journal/WAL and
serving barriers, production identity and full account/history/dataset erasure
remain prerequisites. Missing APIs are inventoried, not advertised as implemented.
No new confirmed open P0/P1 in the controlled local topology; real-user erasure or
production disaster recovery promises without these controls are prohibited.
Prior9A JSON/9B/9C matrices and evidence remain immutable historical authorities.
9D-01/P1 fixed: the first recovery coordinator reconciled Memory receipt keys but
missed post-backup Agent keys. Real source execution/archive/restore reproduced
unsafe release (1fail/1pass); current source checks every issued Agent key for
restored owners against restored run/scope/fingerprint before release (2pass).
Missing keys keep recovery quarantined; reconstructing newer Agent history is not
implemented. See the9D assessment and original reproduction/fix evidence.

Current Phase9C supplement: R-07 is substantially mitigated for the tested local
shared-filesystem topology by early signed admission, shared protected request/
upload rates, Owner/global concurrency/storage/pending budgets, actual receive
deadlines and OS-fenced crash reconciliation. PHASE_9C_MATRIX/ACCEPTANCE link
tests and independent results. Historical9A JSON and9B evidence remain unchanged.
Public production acceptableFALSE: TLS/ingress/header/connection/non-upload body
limits, private OS fencing/storage ACLs, whole-host allocation/free-space races,
DB/worker sizing, supervisor and monitored maintenance are not deployed/certified.
Unknown-provenance files fail closed until reviewed/cleaned; living hung workers
retain capacity until safely stopped. Do not equate accounted bytes with total
physical disk or bounded RSS. R-06 backup/restore/deletion scheduling and R-09
production identity/full deletion/reconciliation remain explicit future tasks.
The9B Windows native worker exit remains an unconfirmed P2 environment finding.

Assessment: 2026-10-13, local development scope. Machine-readable authority:
[SECURITY_RISK_REGISTER.json](SECURITY_RISK_REGISTER.json). Root verification
validates IDs, severity, status, owner stage, all required fields and existing
test references. A test reference is coverage identification; actual execution
results are in [9A acceptance](PHASE_9A_ACCEPTANCE.md).

P0: authentication bypass, cross-owner disclosure/mutation, arbitrary file
read/overwrite through API, exposed real keys. P1: bypassed file limit, severe
resource exhaustion, indefinitely exposed raw artifacts, important error-detail
disclosure or inconsistent concurrent import. P2: constrained development limits
and additional deployment work. No confirmed open P0/P1 may be waived by prose.

## Confirmed and fixed

- **R-01 / P1 / B7:** Uvicorn rendered the original exception despite safe HTTP
  500 handling. Real socket captured a synthetic SQL/private-path sentinel.
  Fix: exception record filter plus safe uploaded-registration DB error mapping.
  Unexpected exceptions still fail; they are not presented as success.
- **R-02 / P1 / B4:** NUL labels reached PostgreSQL text fields; NUL bodies could
  create a Job that could not finalize; timezone conversion could overflow.
  Fix: fatal NUL parse issue before metadata write and controlled time issue.
- **R-03 / P1 / B5/B8:** cleanup ArtifactStoreError escaped; deletion failures
  were silently deferred. Fix: catch storage failures and issue fixed warning,
  retaining explicit orphan retry semantics. Scheduling is separately R-06.
- **R-04 / P1 / B5:** prechecked rename could overwrite a racing final file on
  platforms where rename replaces existing destinations. Fix: exclusive link
  publication; synthetic race preserves old bytes and removes failed partial.
  Client keys were already inaccessible, so no remote overwrite exploit was found.
- **R-05 / P2 / B9:** blank trimming was quadratic within finite parser bounds.
  Fix: linear trim with identical valid output and repeated-message semantics.

Remaining production diagnostics must avoid adding raw exception traces as a
shortcut. Local artifact storage requires hard-link support and private OS ACLs.

## Open P2 and ownership

- **R-06 / B5/B8 / subsequent Phase 9 operations/privacy:** install monitored
  artifact retention maintenance, bounded backlog processing, encryption/access
  policy, backup rotation and restore drill. Tests only prove explicit local
  primary cleanup; no automatic physical-deletion deadline is promised.
- **R-07 / B2/B9 / subsequent Phase 9 resource/deployment:** define admission,
  per-owner/global quotas, active upload deadlines and rate limits; test aggregate
  load and hostile speaker inventories. Local signed identities and loopback
  validation keep this P2 now. Public untrusted exposure without these controls
  would be P1. The 100MiB demo proves one bounded Python allocation workload,
  not worst-case heap or DDoS resistance.
- **R-08 / B6 / explicit future analysis/provider task:** preserve import/Agent
  separation until scoped consent, context bounds and injection evaluation exist.
  Future provider copies cannot be erased by primary Memory deletion.
- **R-09 / B1/B3/B7 / subsequent Phase 9 identity/privacy/reliability:** production
  auth/revocation, all-system object audit, history/cache/account deletion, log
  collectors/rotation and pending-operation reconciliation require separate work.
  Keep current conservative unknown outcomes and exact retry keys.

Actual symlink creation was unavailable in the initial sandbox run; approved
host execution subsequently passed the real isolated symlink-refusal test.
Host-level root redirection remains an OS trust assumption. Historical privacy
regex screening is reproducible but cannot prove
absence of all sensitive free text; provenance review ties the 8F UI data to
synthetic fixture/preconditions. Historical evidence is unchanged.

## Phase 9B current assessment

9A JSON remains its historical risk baseline. Current supplemental authority:
[PHASE_9B_RISK_ASSESSMENT.json](PHASE_9B_RISK_ASSESSMENT.json). No confirmed open
P0/P1 under controlled local use. Fixed P2: malformed Memory cursor500 (9B-01),
unbound position cursors (9B-02, owned SQL never broadened), reusable Transport
late callback (9B-03, existing App controllers already guarded). Tests reproduce
each issue; fixed logging whitelist additionally hardens future diagnostics.

R-09's current public object/session/error audit is now addressed by9B; production
issuer/refresh/revocation, full account/history/cache deletion, collector retention
and durable reconciliation remain. R-06 scheduler/backup/restore and R-08 future
provider/import analysis controls remain deferred.

R-07 production acceptance is FALSE. Repository APP_HOST and Compose Postgres
default loopback. Observed project listeners: PG127.0.0.1:15434, fixture
127.0.0.1:8024, Metro::1:8092, relay127.0.0.1:8093; no project API listener was
present before smoke. This does not certify arbitrary tunnels/firewall/router
state. There is no evidence of actual project public exposure in this environment.

Default per-upload spool+artifact budget <=201MiB plus filesystem overhead;
N simultaneous uploads multiply it (20 can approach4020MiB). Orphans/other jobs
add storage. SQLAlchemy default pool bounds one process only; workers multiply
connections, and unauthenticated ready can consume DB capacity. ENOSPC begin
returns generic500/no Job/artifact; real small-pool saturation returns503. No
remaining capacity, aggregation or slow-client resilience claim follows.

Minimum next design: trusted ingress owner/IP/global rates and body/active
deadlines; reject429/503 before form spooling; owner/global concurrent reservations;
atomic storage reservations for spool+artifact+retained jobs; monitored free-space
thresholds; bounded DB pool/worker alignment; release on all exits and reconcile
process death. Test aggregate legal uploads, malicious slow bodies, disk/pool
failure and cleanup before public ingress. Private development can defer this
implementation; public untrusted exposure without it becomes blockingP1.

9B validation environment P2: one Windows Playwright worker terminated natively
with code3221226505 during first post-marker run. Unchanged Agent3/3 and fresh
full post-marker0 subsequently passed. Cause unconfirmed; preserve evidence and
investigate host/runtime/CI stability if repeated. This is not a claimed fixed
product defect or a waiver of failed verification.
