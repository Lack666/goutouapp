# Phase 9 — Security, Privacy, Reliability and Deletion handoff

Current handoff, 2026-10-13: Phase8 is PASS at committed8/8F, backed by the
[final closeout addendum](PHASE_8_FINAL_ACCEPTANCE.md) and native hash matrix.
The user authorized Phase9A only. Its current acceptance and completion marker
are recorded in [9A acceptance](PHASE_9A_ACCEPTANCE.md); Phase9 overall remains
IN PROGRESS. Original Phase8F limits below remain historical context and are
not an instruction to rerun or reopen Phase8 product implementation.

The following are separate existing contract limits. Classification as P2
applies only while the stated conservative behavior remains true; confirmed
unsafe repeated effects, cross-owner state or unconfirmed deletion are P1/P0
as appropriate and block Phase 8 closure.

1. **Agent pending operation key has no durable outbox — P2 current limit.**
   Same-session replay retains immutable key/payload and server run identity.
   Process death loses that pending request; the client must read authoritative
   history and disclose incomplete reconciliation. Never mint a replacement
   key and automatically resend an unknown previous request. Next work: minimal
   scoped durable pending descriptor, safe lifecycle/ownership purge and
   operation lookup contract before implementing automatic recovery.
2. **Memory pending mutation key is lost on restart — P2 current limit.**
   Same-session retry uses the original key and exact challenge/Undo target.
   Restart loads control/list/known receipt and clears confirmation. It cannot
   infer failed execution from an absent record or recreate an old deletion.
   Next work: minimal encrypted pending descriptor if a future contract requires
   durable reconciliation; test response loss, server commit and restart first.
3. **Unknown upload has no operation lookup — P2 current limit.**
   Lost upload response cannot recover a Job by an operation ID. Display unknown
   and require explicit user action; do not claim import success or silently
   upload again. Next work: owner-scoped operation lookup/idempotent upload if
   required, retaining binary validation, artifact retention and short lifetimes.
4. **Agent history lacks full run association — P2 current limit.**
   Persisted user/assistant messages are authoritative messages, not a complete
   terminal/pending/failed run ledger. Do not infer completed run from text.
   Next work: a bounded owner-scoped run-status association/lookup contract.
5. **Cursor history is not a fixed snapshot — P2 current limit.**
   Current stable ordering and ID deduplication preserve repeated text and
   same-timestamp occurrences. Concurrent writes/deletes between pages can
   change the viewed dataset; Refresh starts a fresh traversal. Next work:
   decide whether a snapshot watermark is needed, then specify and test it.
6. **Development issuer; no production login or refresh — P2 scope exclusion.**
   Current signed short-lived CLI JWT validates ownership; expiry invalidates
   session, scopes, cursors and confirmations. No production session assurance
   or silent renewal is promised. Native SecureStore authenticated restart and
   logout restart now have actual Phase 8F evidence; full pending-operation
   lifecycle remains incomplete. Next work: production identity/refresh/revocation design,
   least privilege and actual lifecycle acceptance without embedding secrets.
7. **Production backup/restore/scheduler undeployed — P2 scope exclusion.**
   Confirmed deletion affects scoped primary Memory/undo history, retaining
   mutation/confirmation metadata by policy. It does not erase chats, identities,
   imports, provider copies, logs or backups. Logical expiry prevents new recall;
   physical cleanup is a separate retention operation. Next work: deploy/test
   backup restore, bounded retention jobs, deletion propagation and audit policy.

Phase 8F does not certify production reliability. New tests exercise safe
controller reconstruction and same-key replay; real native crash/outage proof
remains a Phase 8 acceptance requirement, not something this handoff waives.
Do not introduce Redis, Kafka, microservices, a vector database or a generic
offline synchronization framework without a demonstrated requirement.

Other exclusions: release APK/EAS pipeline, real LLM behavioral quality,
imported-chat-to-Agent analysis, public structured FIU/Profile and optional RAG.
Maintain MockLLM/keyless regression and the frozen upstream snapshot.

## Phase 8F Closeout evidence boundary

The Closeout Addendum records separate real native tests for postcommit REST
and Memory response loss, original-key replay, force-stop/restart and
authoritative reload. Restart deliberately loses the volatile pending mutation
descriptor: the App clears confirmation, reads current Memory/control and
discloses incomplete reconciliation. A manually supplied known receipt ID can
be inspected without recreating or executing a deletion. These conservative
behaviors satisfy Phase8 acceptance when their complete native scenes pass;
they do not deliver a durable outbox or automatic crash reconciliation.

The direct SSE observer is Android development acceptance tooling. Production
node observability, token/cost accounting and production identity are not
implemented by this observer. Fixture fault injection adds no production
endpoint or authentication bypass. Future Phase9 work must keep exact keys,
owner/scope invalidation, server challenges and persisted receipts authoritative.
At the time of that Phase8F closeout, Phase9 was pending and had not started.

## After Phase9A: executable remaining work

No formal9B–9E subdivision existed before9A; future labels/scope require the
next explicit instruction. Do not infer completion of Phase9 from9A. Keep
Mock/keyless tests and all prior native/OpenAPI/frozen gates.

- R-06: operational artifact maintenance, bounded backlog and generic failure
  alerts; test process death, cleanup faults, missed schedule and backlog drain.
  Add production backup/key custody/rotation and quarantined restore drill before
  recovery/deletion claims. Query-time expiry is not physical cleanup.
- R-07: define active-body deadline, concurrent admission, owner/global file and
  Job quotas and reverse-proxy rate/body controls before untrusted exposure.
  Stress worst-case unique speaker inventories and aggregate disk/heap/DB/slow
  connections, including unauthenticated form spooling. This9A demo only proves
  bounded single-file behavior and controlled small concurrency. Public exposure
  with present aggregate limits would beP1 and must not be accepted.
- R-09: broader full-system object authorization and identity/revocation audit;
  preserve development issuer boundaries until explicit production auth work.
  Define user/history/cache/account deletion and tombstone/retry semantics without
  weakening existing Memory guards. Audit deployed collectors and retention.
- Existing pending-request/outbox/run-lookup limits remain conservative unknown
  outcomes. Decide minimum scoped descriptors and reconciliation contracts before
  implementing automatic replay; test postcommit loss and restart with original keys.
- R-08: imported history remains outside Agent and providers. Future analysis
  requires explicit owned source/consent, bounded untrusted envelopes and injection
  evaluation; no unsolicited pipeline or provider integration in this handoff.

9A fixed R-01–R-04 blockers and R-05 trim cost. Real Windows symlink refusal passed
in approved host execution after the sandbox-only skip; private root ACL/reparse
protection remains an operational assumption.
Read-only historical131-file evidence screening found no credential pattern hits;
this is not a general proof about arbitrary prose. Keep original evidence unchanged.
