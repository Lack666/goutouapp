# Guarded erasure API — Phase9E / Backend-only

All three routes require the existing signed Bearer credential and existing
User. Owner comes exclusively from the verified actor; clients cannot supply it.
OpenAPI has39 operations: all original36 preserved plus these three. Generated
TypeScript is reproducible from docs/contracts/openapi.json. No LLM runs here.

POST `/api/v1/erasures/prepare` body: `domain` (`dataset` or `conversation`),
`target_id` UUID and exact expected `relationship_id` (null for a generic
Conversation). Dataset UUID is **dataset_job_id from a successful finalize**,
not a ready duplicate Job UUID. Only canonical imported Jobs qualify. Response:
confirmation_id, domain/target/Relationship, counts, expires_at,
memory_affected=false and retained-metadata explanation. Count refers to current
physical formal messages; run_count names preserved run metadata, not removed runs.
Inspect the returned range and obtain an explicit user's choice before Execute.

POST `/api/v1/erasures/execute` repeats the exact domain/target/Relationship and
adds confirmation_id and a valid immutable operation_key (1–128 characters,
no whitespace/control/NUL). A client `confirm=true` is rejected. Challenge lasts
five minutes; changed snapshot, active/unresolved work, expiry/consumption/mismatch
reject with409. A foreign or missing challenge/receipt/target yields404 without
disclosing another owner. Successful response is a durable receipt_id,
confirmation_id, exact target/scope, actual removed message_count, retained
run_count, performed_at, status=deleted and memory_affected=false.

GET `/api/v1/erasures/receipts/{receipt_id}` returns only the owner's receipt.
On response loss repeat **the same full payload and key**, including original
challenge UUID; success replays after restart or challenge cleanup without touching
later data. Same key/different payload409 idempotency_conflict. Receipt lookup
does not execute deletion. Network failure is unknown, never interpreted as
cancelled or successful. Refresh authoritative History after known completion.

Conversation: delete its Message rows (including tool), keep tombstone and Run
ID/status/key/fingerprint, clear message pointers via SET NULL and outcome metadata.
Existing pending/running or completed-unresolved runs yield409 target_busy; no
forced stop is offered. New Agent runs or old REST/SSE replay return404 after
deletion. Creating the old Conversation UUID returns409. Lists exclude tombstones.

Dataset: delete only canonical Job/owner/Relationship occurrences and speaker
labels/bindings. Keep dedup fingerprints/counts/import timestamps, Job/artifact
metadata and tombstone. Both original finalize and same-transcript duplicate/new
Job finalize return409 dataset_deleted; other datasets/Relationships remain.
Historical Job inspect can still show imported summary: it is an old receipt,
not evidence that messages still exist. Formal History is authoritative. Raw
canonical source was already terminal-cleaned on finalize; any residual cleanup
failure is retried by9D maintenance, not claimed erased by this receipt.

Memory is separate: neither operation invokes consent, recall, save or delete.
Person/Relationship/account/all-history/message-by-body erase are unsupported.
No production identity lifecycle, encrypted backup or independent recovery journal
is introduced. Older dumps retain bodies until expiry or quarantine reconciliation.

Mobile is Backend-only: generated callable contracts and error adapters exist,
but no App prepare/confirm/execute controller. Settings and History disclose this.
App keeps its existing immutable-key/session/epoch and separate Demo semantics.
Native regression is distinct from Android self-service deletion (NOT IMPLEMENTED).
