# Security risk register — Phase 9A

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
