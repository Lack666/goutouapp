# ADR 0041: Server-discovered exact targets and session-only guarded Mobile erasure

Accepted for Phase9F, 2026-10-14.

After restart, existing import inspection requires a known Job ID and History
does not enumerate canonical empty/tombstoned Datasets. Add only an owned
Relationship Dataset summary page, built from canonical imported Jobs with
existing bound cursor conventions. Keep duplicate jobs out and preserve tombstone
metadata. No new Dataset management infrastructure or content search is needed.

Reuse the unchanged 9E Prepare/Execute/Receipt service from a separate Mobile
controller using generated DTOs, session epochs and immutable submitted bodies.
Keep keys in bounded volatile memory only. A durable outbox would require a
separate storage/security/reconciliation contract. Losing a process therefore
requires authoritative rediscovery without automatic mutation or success claim.

Invalidate exact target caches before Execute and ignore aborted late events.
Confirm success by formal Receipt and show refresh outcome separately. Busy
remains a server refusal; unresolved Run recovery is deferred, recorded in R-10.
Dataset, Conversation and Memory keep distinct IDs, scopes and controls.
