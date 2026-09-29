# ADR 0025 — Owner-bound temporary artifacts and one-upload HTTP import

Status: accepted for Phase 5D.

We use a private local filesystem behind `ImportArtifactStore` and a separate
PostgreSQL metadata row. Each successful upload gets an opaque random key,
content length and SHA-256. A composite foreign key binds one Job to one
artifact of the same owner. This keeps large raw exports outside PostgreSQL
and lets a future object store implement the same interface without changing
5B binding or 5C merge services.

The HTTP adapter reads bounded chunks, then parses the completed artifact.
Finalization verifies artifact bytes and reruns 5C integrity gates inside its
atomic transaction. A durable imported Job replays without raw bytes.
Completed imports delete raw bytes; failed merges retain them until retry or
expiry. Explicit cleanup covers expired and crash-orphan files. Scheduling,
distributed reconciliation and production object storage are deferred.

The relationship history endpoint uses bounded keyset pagination in
historical timestamp/source order. Imported rows never enter the Agent
Conversation Message table or Memory workflow. Exact dataset idempotency
remains the 5C database rule; partial overlap across files remains deferred.
