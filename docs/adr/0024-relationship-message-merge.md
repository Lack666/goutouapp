# ADR 0024 — Separate relationship history and atomic transcript promotion

Date: 2026-09-28. Status: accepted for Phase 5C.

Existing `messages` are Agent Conversation history with user/assistant/tool
roles. Reusing them for external chat would confuse sender semantics and risk
Agent history leakage. We add a separate `relationship_messages` table with
explicit sender kinds, source occurrence and historical timestamp. Agent
history queries remain confined to their original table.

Because Phase 5B intentionally stores no raw source, merge requires the actor,
Job ID, expected binding revision and a one-pass source again. It reruns the
trusted parser, stages canonical messages in a transaction-local PostgreSQL
table in bounded batches, validates the complete transcript against the Job,
then promotes all formal rows in one transaction. `importing` is a transient
transaction state; failures roll back to ready. Imported Job bindings become
immutable through the application service.

We use `(import_job_id, source_index)` for occurrence uniqueness and preserve
the canonical message fingerprint for integrity and provenance. Same-Job
replay returns its durable Job summary. A partial unique index on imported
owner/Relationship/transcript scopes, plus a transaction advisory lock,
prevents exact duplicate datasets across Jobs. Cross-file partial overlap
dedup is deferred because content equality cannot distinguish overlap from
real repeated messages. System speaker messages are stored explicitly;
ignored speaker messages are counted but skipped. Phase 5D owns upload and
resumable network transport.
