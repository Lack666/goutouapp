# Phase 9 — Security, Privacy, Reliability and Deletion handoff

This is documentation prepared during Phase 8F, not implementation or approval
to start Phase 9. Phase 8 remains IN PROGRESS; incomplete Android evidence in
[final acceptance](PHASE_8_FINAL_ACCEPTANCE.md) must first be resolved.

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
