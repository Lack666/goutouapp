# AgentRun recovery — current Phase 9H

Implemented operator-only recovery requires the exact signed owner/conversation/run,
immutable operation key and configured trusted shared OS fence. The original writer
holds its lock through Provider, runtime, persistence and possibly still-live executor
threads. Cancellation, disconnect, lost DB pools and30days elapsed never prove death.
Normal completion explicitly acknowledges writer release only after runtime ends.
Offline recovery acquires the same lock and holds it through committed Message/Memory
inspection and receipt commit. It preserves actual effects and original Agent key,
records failed/writer_stopped and unknown_preserved Memory outcome. It never creates
Completed or retries Provider. Same recovery key returns the same durable receipt;
other owners and changed payloads are rejected. Erasure requires matching receipt
owner/run/token/scope/time, not a recovered_at flag alone.

Private development/test operator command: `uv run python apps/server/data_erasure_cli.py`.
One bounded JSON line on stdin carries signed credential and action `recover_run`,
conversation_id, run_id and operation_key. Credentials never enter argv/logs. No
privileged HTTP recovery endpoint, cron reset, force flag or age threshold exists.
Operators stop only the verified owning workload, retain its fence/root and use the
supported proof path. Legacy rows or missing/moved roots remain quarantined; an
unsupported topology needs authoritative incident investigation, not fabricated proof.
DB-role/host compromise is outside the API trust boundary; root ACLs and shared
filesystem/OS lock semantics require deployment acceptance.

Actual spawned workers are held at Provider, answer and Memory commits, then killed.
A fourth case cancels the service coroutine while a Memory executor thread remains
alive: recovery still refuses until process termination. Original-key REST/SSE replay
fails without re-execution. Actual pg_dump/restore preserves the recovery receipt and
refuses release with an unacknowledged live writer. See ADR0043 and9H evidence.

## Historical Phase9G audit and proposed design

The earlier unavailable-command statements below describe the9G implementation.

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
