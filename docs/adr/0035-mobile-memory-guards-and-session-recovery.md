# ADR 0035 — Mobile Memory guards and session recovery

Date: 2026-10-11. Scope: Phase8E only.

Reuse generated13 Memory operations, the single ApiTransport/DevelopmentSession
and owned resource selectors. Add public DTO adapters, a bounded asynchronous
MemoryController and Connected Settings panel. FastAPI services/PostgreSQL are
the only control, ownership, retention, confirmation and receipt authority.
Do not add endpoints, a client MemoryStore, token manager or consent database.

Control submissions always re-inspect authority, including after response loss.
Undo binds fresh global preview's expected operation ID. Deletion uses real
server challenge and explicit user confirmation. At Execute, freeze original
key plus expected operation/confirmation ID and target/scope. Unknown outcomes
lock new prepares/target changes; read-only refresh does not prove completion.
Only original-request retry or matching formal receipt resolves the operation.
No fallback to an older Undo or a newly prepared deletion is permitted.

Recovery remains session-memory only, consistent with8B/8C. Background/blur
invalidates unexecuted challenges, cancels reads and retains submitted immutable
attempts. Foreground reads only. Logout/epoch clears everything; restart loses
the key and explicitly cannot safely auto-retry an unconfirmed mutation. This
avoids durable private content, token or pending-operation synchronization and
keeps server receipt replay authoritative. A durable journal can be separately
designed if an explicitly requested later scope needs cross-restart recovery.

Public record/provenance/expiry and server policy are displayed; private evidence,
hashes, prompts and operation keys are not. The existing Demo is retained. Chat
Memory status links to Settings and never performs mutations. Actual JWT/PG/
LangGraph/Phase6Mock and visible Chrome UI tests remain separate from unit mocks;
offline Android is NOT RUN, with native final evidence deferred to8F.
