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
