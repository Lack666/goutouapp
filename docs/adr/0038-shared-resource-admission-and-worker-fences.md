# ADR0038 — Shared resource admission and OS worker fences

Status: accepted for explicitly authorized Phase9C, local shared-filesystem topology.

R-07 previously bounded one upload but multiplied spool/artifact/parse/DB costs
without aggregate admission or receive deadlines. FastAPI parsed Multipart before
JWT dependencies. PostgreSQL already provides cross-process transaction guards,
and the artifact store already separates immutable bytes from durable Job metadata.

Use two small migrated metadata tables for bounded rate windows and reservations;
serialize issuance/reconciliation with one PostgreSQL advisory transaction lock per
canonical deployment root. Reject capacity immediately after bounded lock waiting.
Validate signed existing Owner before body parsing, reserve worst-case spool and
artifact bytes, restrict Multipart cardinality and bound actual receive idle/total
time. Preserve all existing business service authorization and durable merge receipts.

An OS-owned one-byte file lock is the liveness authority. A DB connection/session
lock dying alone cannot prove a worker stopped writing. No TTL releases live fences.
Recovery runs opportunistically at admission or explicit maintenance; residual
files retain Owner attribution until physical deletion. Unknown files fail closed
for admission but remain countable/cleanable by privileged maintenance.

The default local topology supports actual multiple worker processes sharing the
same private filesystem/DB/configuration; separate machines, network filesystems
and object stores require a future validated fence/storage design. No new server,
queue, account service, endpoint, public DTO, dependency or Agent behavior is added.
Safe count-only snapshots are operator-only; rate and capacity errors reuse the
existing error envelope. All raw private log protections remain active.

Consequences: bounded admission DB connections can reduce available per-worker
pool capacity, and full byte reservations reject small files conservatively.
Fixed-minute windows permit boundary bursts; external ingress and supervisors are
still required. Reconciliation counts filesystem bytes with conservative4KiB
overhead, not exact total physical disk allocation or RSS. Policy changes require
draining workers and guarded explicit reconfiguration; inconsistent workers fail.

Primary technical references: [PostgreSQL advisory locks](https://www.postgresql.org/docs/16/explicit-locking.html#ADVISORY-LOCKS),
[Python temporary files](https://docs.python.org/3/library/tempfile.html),
and the locked Starlette Multipart implementation inspected locally. Repository
tests, rather than these general references, prove actual admission/recovery behavior.
