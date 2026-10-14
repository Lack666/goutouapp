# AgentRun recovery boundary — Phase 9G

This is an audited contract and future recovery design, not an implemented Run
reconciliation command. No privileged HTTP reset, age-based reset, forced erasure,
background Run reconciler or durable client outbox exists.

The production implementation is AgentService plus ErasureService. A pending or
running Run blocks Conversation erasure. A completed Run with null memory_status
also blocks erasure: the assistant may be committed while optional Memory work
is still live or its result is unknown. Age does not prove worker death. A failed
Run or a completed Run with finalized Memory metadata permits preparation, subject
to the exact fresh snapshot and all normal owner/challenge guards.

Consequently **yes, a crashed unresolved Run can indefinitely prevent safe
Conversation erasure in the current implementation**. This is R-10, P2 for the
controlled synthetic development topology and a blocker for a public recovery or
real-data erasure promise. Neither logout, client restart, a new operation key nor
30 days elapsed authorizes changing the server Run. Dataset and Memory deletion
remain independent controls, subject to their own confirmation contracts.

REST/SSE use the original scoped operation key. Running replays report
operation_in_progress; pending and completed-unresolved operations report
operation_unresolved. Failed keys do not execute again. Completed finalized keys
replay the same Run and assistant Message without Runtime or Memory execution.
Unknown Outcome is an observation, not a fifth DB status or proof of failure.
History alone is not a complete Run ledger. The App must never infer completion
from text or auto-resend a lost descriptor with a replacement key.

Existing disconnect handling attempts failed before answer commit, and preserves
completed after commit. An unavailable recovery update can leave running_unknown.
Provider/worker crash is not repaired by a client action. Operators may inspect
aggregate pending counts and safe status/IDs in a private authorized environment;
they must retain the unknown outcome and restrict serving while investigating.
There is no approved direct SQL procedure to rewrite a Run into failed/completed.
Do not advertise Refresh as a repair operation.

A future controlled reconciler must prove all of the following before mutation:

- Exact authenticated owner/Conversation/Run/key/fingerprint association; acquire
  the same owner and Conversation serialization barriers as normal execution.
- Deployment-wide writer exclusion, including all workers and unfinished
  provider callbacks. DB disconnection or elapsed time alone is insufficient.
- Reconcile actual user/assistant Message links and committed optional Memory
  effects. Preserve a committed answer and every existing Memory write; uncertain
  effects remain unresolved. Do not manufacture a success result or a new message.
- Preserve original Run ID and durable key; prohibit reexecution. If there is no
  assistant commit and writers are proven stopped, a specifically authorized
  transition to failed can retain the user Message. If an answer is committed,
  finalize only metadata whose actual Memory outcome has been proven.
- Commit a metadata-only operator receipt with expected old state and a compare
  check. Concurrent/repeated reconciliation must be idempotent; changed state,
  scope or uncertain authority rejects. Reprepare deletion after any transition.
- Exercise worker/provider death before/after answer and Memory commits, DB loss,
  concurrent original-key replay/deletion, restart, restore and owner A/B. A
  durable serving barrier and alerts require production deployment verification.

Tests in test_reliability_9g.py prove the current block and replay contract across
an App restart with thirty-day-old rows. Existing disconnect, idempotency,
erasure and native fault tests remain mandatory. They do not establish the future
reconciler. Implementation requires a separately authorized Phase 9 recovery task;
Phase 10 RAG cannot waive it.
