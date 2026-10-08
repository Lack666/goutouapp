# ADR 0028: Fixed expiry and durable destructive-operation receipts

Status: accepted for Phase 6C, 2026-10-08.

Compact relationship memory may become stale and must remain user-controlled.
The frozen Skill specifies consent, limits and deletion but no retention days.
Choose configurable finite retention, default 180 days from creation, because
it limits stale private context with one timestamp and preserves arbitrary
user deletion. This is a product choice, not a legal-compliance duration.

Stored expiration is fixed; ordinary recall and duplicate save do not renew it.
Configuration changes apply prospectively. Legacy records receive a one-time
180-day transition from migration time, avoiding immediate deletion based on
old creation dates. SQL and standalone service recall both exclude expiry at
the exact UTC boundary. Default lists contain active records; owned inspection
by ID can show expired state until physical removal. In-flight context cannot
be retracted remotely after recall/model transmission.

Use deterministic bounded one-shot maintenance and existing owner locks;
physically remove expired records and cascade only their undo history. Expired
latest undo is unavailable; expected-ID matching prevents falling back to an
older record. Challenges expire after five minutes and become cleanup eligible
24 hours later by default, consumed or not. No extra state table/queue is needed.

Choose durable receipts (strategy A), retained for owner lifetime. There is no
receipt cutoff or expired-key case; supported retry horizon is that lifetime
with intact metadata. Replay reads the receipt before a possibly removed
challenge. Different payloads still conflict. Maintenance never modifies
receipts, so concurrent retry/cleanup preserves the 6B owner-lock transaction
invariant. Storage growth is accepted and must be monitored; bounded receipts
would require terminal-key fencing, which is outside 6C.

Consent and retention stay independent: expiry does not grant, revoke, pause
or resume; revoke-and-keep still expires. Delete-all's explicit revoke flag and
structured Person deletion scope remain unchanged. Primary deletion is not
backup or provider erasure. The separate backup policy describes a planned
35-day rotation and fail-closed restore runbook; no production backup, replay
or scheduler is claimed deployed. No Mobile, RAG, queue or new reasoning.

Authoritative policies: MEMORY_RETENTION.md and MEMORY_BACKUP_DELETION_POLICY.md.

Phase 6D clarification: an expired row still owns its scoped unique content key
until physically removed. A new authorized save may atomically remove just that
expired collision and cascade its old undo, then insert a new UUID/creation/expiry
and undo operation. It reuses the owner lock and durable final consent/pause gate;
failure rolls back both steps. Active duplicate saves do not renew lifetime.
No new ADR, schema, graph or runtime abstraction is required for this repair.
