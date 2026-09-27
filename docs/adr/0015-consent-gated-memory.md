# ADR 0015: Consent-gated, scoped memory after response

Status: accepted for Phase 3G (2026-09-27)

## Decision

Keep current conversation and long-term memory in separate stores. The graph
loads eligible, scoped historical records before safety checking and analysis,
then resolves save intent, extracts at most one typed candidate, validates and
persists it after the user response. Candidate extraction has no store access.
`memory_enabled` is a runtime switch, not consent; persisted per-user opt-in
and pause state are independent. Safety runs do not write. Storage is behind
`MemoryStore`, with in-memory and SQLAlchemy implementations. Explicit inspect,
delete and control calls are separate from ordinary response generation.

## Rationale and limits

One candidate per call prevents partial batch commits on a store failure.
Hash-based dedup makes retries idempotent without introducing a queue or a
checkpointing system. The initial persisted subset contains user, object and
relationship facts; event/hypothesis need stronger temporal and correction
contracts. Historical memory is labeled and never promoted into the current
FIU. Pause blocks recall and writes, matching upstream `require_enabled`
behavior, while inspection and deletion remain possible. Delete-one returns
false when nothing matched; person/all deletion requires confirmation and
returns the deleted primary-row count. Graph delete intents are pending until
an authenticated caller makes that separate confirmed service call.

The service can validate quoted F provenance and reject obvious prohibited
content, but it cannot independently establish that a model-produced F item is
true or detect every sensitive paraphrase. The current intent parser recognizes
a narrow Chinese command vocabulary. A memory failure after response is a
generic receipt/warning and does not erase the completed answer. PostgreSQL
deletion guarantees apply only to the app-owned active primary database;
backup retention and account deletion require later policy and infrastructure.
