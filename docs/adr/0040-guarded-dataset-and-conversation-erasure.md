# ADR0040 — Guarded Dataset and Conversation erasure

Status: accepted for Phase9E, 2026-10-13. Delivery: Backend-only.

Hard deletion would remove resource UUID retry fences, break AgentRun/import
provenance FKs and allow old operations to execute again. Keep Conversation and
canonical imported ChatImportJob tombstones with original IDs and key/fingerprint
metadata. Physically delete only their formal Message/RelationshipMessage rows
and canonical Dataset speaker labels/bindings. Preserve unrelated Memory and
Person/Relationship scopes. Do not use SQL cascades as a product deletion policy.

One transport-independent ErasureService owns Prepare → server challenge →
explicit caller execute → atomic durable receipt → authoritative read. Three
signed routes, strict extra-forbid DTOs and a five-minute challenge bind exact
domain, UUID, expected Relationship, message/run counts and canonical UTC snapshot.
The owner's User row serializes challenges and retry keys; the existing Agent
Conversation advisory lock or import canonical Job/scope lock serializes effects.
Completed-unresolved, running and pending AgentRuns reject erasure. No force
cancellation or age-based reset is inferred; supervision/reconciliation remains
separate. Agent reads acquire the Conversation lock before checking tombstones.

Same owner/key + exact original payload returns the immutable receipt before
challenge or target lookup; changed payload conflicts. Receipt contains IDs,
counts and time, no bodies, speaker labels, prompts or provider reasoning. Another
owner cannot prepare/use/inspect a challenge or receipt. Same Conversation UUID
creation retry conflicts after deletion; Agent REST/SSE returns owner-neutral404.
Canonical Dataset keeps imported status and exact-dataset unique index, plus
deleted_at. Old canonical finalize, duplicate Jobs and later identical same-scope
transcripts return409 dataset_deleted; no silent reimport. Different transcripts
or Relationships remain independent. Explicit reimport of an erased transcript
is intentionally unavailable until a separately authorized lifecycle contract.

Deletion removes formal primary history only. Failed original artifact cleanup
continues under9D maintenance; no raw-source/backup/all-account erasure claim.
Tombstones and receipts remain indefinitely in the current owner lifecycle;
challenge metadata uses existing bounded expiry+24h maintenance. Person and
Relationship deletion is unavailable even when empty, to avoid undocumented
creation-key/provenance semantics. Account erasure requires production identity,
revocation, dependency enumeration and copy policies; it is formally unfinished.

Synthetic offline recovery still requires a complete frozen current primary.
Reconcile exact owner/target IDs and immutable resource scopes, apply tombstones,
delete target messages/speakers, replace immutable current receipts and invalidate
all old challenges. Missing current target/key/receipt history, mismatch, missing
primary or any error keeps release false. A post-backup tombstone for a target
absent from the backup also blocks release rather than losing its fence. Repeated
application is safe; deleted IDs cannot reappear while nondeleted owners survive.
No independent journal is implemented: it must also carry trustworthy current
controls and operation fences to be useful, and production disaster recovery is
not claimed. Native dump files are unencrypted anonymous fixtures, removed after
the drill, never advertised as secure production backups.

Mobile generates all39 operations and safely projects new error codes. Existing
History focus/refresh/leave and session epochs discard old models and cursors;
Settings/History explicitly explain absent self-service chat/account erasure.
No deletion controller or executable App button is added. Fresh five-scene native
regression validates changed Mobile source; it is not native deletion evidence.
Dependencies, Runtime graph, frozen Skill, Golden and FEATURE_RAG behavior stay
unchanged. See DATA_DELETION_CONTRACT/MATRIX and PHASE_9E_ACCEPTANCE/MATRIX.

9E-01 (P1, fixed): a deleted Dataset must already be a canonical `imported`
Job in the backup. A pre-finalize `ready` Job lacks the partial unique-index
re-import fence; reconciliation refuses release rather than synthesizing newer
import history. Covered by `test_restore_cannot_drop_post_backup_imported_dataset_fence`.

9E-02 (P2, fixed): owner serialization uses PostgreSQL FOR NO KEY UPDATE,
which conflicts with other owner mutation locks but permits FK KEY SHARE checks.
This avoids a cycle with an Agent holding the Conversation advisory slot while
inserting its Run; after that insertion commits, erasure rejects target_busy.
Covered by `test_new_agent_run_and_erasure_lock_order_remain_live`.
