# Connected Agent Chat — Phase 8C

Phase8D adds separate imported RelationshipMessage History; this Chat controller,
AgentService input and Conversation Message contract remain unchanged. Import
creates no Agent answer or Memory. No imported transcript is sent to a provider.
The historical import-deferred description below is superseded only for8D UI.

Connected Chat uses the existing owned Conversation selector, generated client,
8B API origin/JWT session, transport, themes, FlatList and composer. Demo remains
local and unchanged. Import and RelationshipMessage history remain deferred;
Agent Conversation Message is a separate domain. No imported dataset enters a prompt.

The controller first GETs the owned Conversation and verifies any supplied
relationship against its actual nullable binding. Missing/foreign IDs are neutral
404s. Malformed/Demo IDs and mismatched scope fail closed before sending. A generic
Conversation works independently. With no relationship assertion, its actual
server binding supplies `expected_relationship_id`; it is never inferred.

REST uses generated `CreateAgentRunRequest` with bounded nonblank, valid Unicode
message (Mobile 2,000 UTF-16 units, server 20,000 Unicode characters), actual
Conversation path, nullable expected relationship and a fresh crypto UUIDv4
`operation_key`. Resource-create UUID and Agent operation key have separate scopes.
Generated `AgentRunResponse` is adapted only after validating completed status,
Conversation/run/assistant IDs, assistant role/text, memory status and public warnings.
Only server-confirmed text becomes an assistant bubble. No FIU is derived from text.

Presentation states: local composer draft, submitting, running, committed answer
awaiting terminal event, completed, failed and running_unknown. Progress is separate
from answer text. There are no optimistic user bubbles: the pending request has a
separate status/key, while formal user bubbles come from Agent History. REST/SSE
committed answers carry their real assistant Message ID. History merges by ID, never
by content, preserving distinct identical messages. SSE supplies no message time;
until History returns it the time label explicitly says it is awaiting history time.

History GET `/api/v1/conversations/{conversation_id}/messages` uses generated
AgentMessagePage, bounded30 pages and opaque cursor continuation. It orders actual
timestamps then UUID, deduplicates IDs, validates the scope/roles/times, supports
empty/loading/error/retry/refresh and bounds the visible collection at1,000 messages.
Refresh resets the history page while retaining already confirmed assistant IDs.
It does not claim snapshot semantics. It cannot establish a particular run's terminal
status, since public Message has no run_id/operation_key association.

One immutable body/key per logical action is reserved before sending. Duplicate
clicks are guarded. Timeout/offline/incomplete stream/unsupported version/protocol
failure retain the original operation as outcome unknown. New sends are blocked
until controlled same-key retry establishes an outcome; edited composer text never
changes that retry. Explicit new messages after known failure/completion get fresh
keys. At most20 Conversation attempts are retained per credential session.

Both retry buttons intentionally replay the same body/key through REST or SSE.
Completed operations return the original run/Message without Runtime or Memory
execution. Running/busy/unresolved returns explicit unknown/in-progress presentation;
there is no live-generator reattachment. Failed operations stay failed. Public codes,
run ID and recovery_status are allowlisted; raw SQL/provider/JWT errors are discarded.
HTTP404 cannot distinguish foreign, missing or server-rejected relationship scope;
the local verified-scope error is separate. HTTP running_unknown takes precedence
over a failure category. Changed retry payload409 is a client conflict, never a new key.

Leaving/blurring Chat, changing Conversation/relationship, backgrounding, logout,
expiry,401 or identity replacement aborts consumption and rejects stale events.
Session epochs and page generations guard every async response. Logout immediately
clears in-memory credentials/attempts/messages/cursors/errors/scopes and cancels
requests. A `clearing` presentation remains until native storage confirms removal;
only then does `no_token` acknowledge completion. Failure becomes `storage_error`.
Closing the process before confirmation can interrupt durable removal; keep the App
open during clearing. Old clear completions cannot replace a newer session epoch.
Navigation reset
checks canDismiss before clearing an existing stack. Pausing preserves the original
key and states only that the client stopped waiting. It does not promise rollback.
Established SSE auth is not continuously checked by the server; local token expiry
still cancels consumption and clears the session, without asserting server cancellation.

Pending keys/bodies live in session memory, with no durable offline outbox. Returning
to a Conversation within the same session can retry the retained operation. Process
restart/Web reload loses pending metadata; formal history recovers committed messages,
and no old action is automatically resent. A persisted history row cannot reconstruct
an operation key or prove that optional memory finalization ended. Production recovery
and reconciliation remain future reliability work.

Memory status and pending confirmation are read-only public receipts; no grant,
revoke,pause,resume,undo or delete transport is enabled. Pending confirmation explains
the formal confirmation service; chat cannot bypass it. Structured FIU/Profile DTOs,
real provider quality, Import networking and Memory controls remain deferred.

See [streaming](MOBILE_STREAMING.md), [Agent API](AGENT_API.md),
[idempotency](IDEMPOTENCY.md) and [acceptance](PHASE_8C_ACCEPTANCE.md).

The 2026-10-10 revalidation independently reran all root gates at the existing
7/8C marker and exercised actual Android core Chat. Native Chinese consumption
observed eight reader chunks and ten V1 events; same-key REST/SSE replay retained
one completed run and two Message rows. Actual History, postcompletion Back,
logout, SecureStore restoration and Owner B's foreign-Conversation denial were
observed. Native active-run disconnect/background/expiry and full keyboard QA
remain separate unexecuted checks. No temporary native QA route is shipped.
