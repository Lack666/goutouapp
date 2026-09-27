# ADR 0018 — Agent application service and short transactions

Date: 2026-09-28. Status: accepted for Phase 4A.

## Decision

Reuse the Phase 2B Conversation, Message and AgentRun records. A trusted
authentication adapter issues a typed actor; `AgentService` alone resolves the
owner-scoped conversation and composes `AgentInput`. Application transaction A
commits user input and the running run before calling the runtime. Transaction
B atomically writes the validated answer and completes the same run ID. A
failure transaction marks the run failed. Repositories do not commit. The
runtime remains free of database and transport concerns.

Add only `started_at`, `completed_at` and `failure_code` to AgentRun. Its
existing `created_at` and ID provide creation time and correlation. Injecting
the persistent UUID through optional `AgentInput.run_id` preserves direct
standalone runtime callers while aligning all application IDs. The existing
four-value `AgentRunStatus` remains the sole status vocabulary.

History is an owner- and conversation-scoped, 20-message window read before
the current message insert. An optional operation key is validated at the
service boundary but persistent deduplication belongs to Phase 4D.

## Consequences

The service holds no SQLAlchemy transaction during LLM latency. If answer
persistence fails, a separate transaction tries to mark the run failed. If
that also fails, the run may remain running; a future recovery worker must
inspect it. The service reports `running_unknown` and never reports success.
Memory can persist independently before answer persistence; this cannot be
atomically undone without a distributed transaction. The client sees a typed
persistence error and must not assume an assistant message exists.

Phase 4C streaming must use the same application start/finish operations. Its
disconnect policy remains an open design question, including the Phase 3H
final-answer-before-memory-close case.
