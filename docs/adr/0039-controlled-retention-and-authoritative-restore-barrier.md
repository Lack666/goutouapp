# ADR0039: Periodic primary maintenance and controlled restore barrier

Date2026-10-13; status accepted for the explicitly authorized Phase9D scope.

Existing Memory guarded mutation/retention services and PostgreSQL/local Artifact
storage stay authoritative.9C already charges actual files and protects live workers
with OS fences. A periodic operator process can compose those services without a
queue, distributed scheduler or new public API. A second root-scoped OS lock prevents
competing maintenance instances; bounded DB/keyset batches limit work. Physical
unlink precedes final metadata status, while physical accounting remains independent.
Failures retry on scheduled passes; no live lock is stolen because it is old.

Existing delete-person/all receipts contain scopes/counts, not exact historical
target IDs. Rather than add another long-lived content/identity store,9D uses the
already-documented current-primary recovery option: offline freeze, compare exact
surviving owner/Memory IDs, copy current controls/receipts/valid undo metadata,
invalidate stale challenges, then verify before any restored access. This also
covers legacy standalone Undo and retention without relying on receipt inference.
Raw sources are deliberately absent from the controlled backup; restore cancels
pending imports and keeps formal imports. No SQL schema/dependency change is needed.

The consequence is explicit: an intact complete authoritative primary is required;
the tested synthetic drill is not disaster recovery and cannot accept real data.
Post-backup nondeleted new data is recovery loss, not reconstructed data. Without
current terminal key/consent/deletion information, no serving release is allowed.
Future production requires independent durable deletion/WAL recovery, encrypted
copy rotation/key custody, a real access barrier and monitored scheduling. Public
account/history/dataset deletion and durable Mobile outbox remain separate scope.

All current issued Agent keys for restored owners must have matching restored
run IDs/scopes/fingerprints before release. A missing post-backup run/key fails
closed; no reconstruction of newer Agent history is introduced. The first
coordinator lost a post-backup Agent key while preserving Memory mutation keys;
the two-case real LangGraph/PostgreSQL reproduction/fix closes9D-01 with this
barrier, without changing Agent behavior or adding tables.

Validation: actual migrated PostgreSQL/native dump/restore, exact-ID replay,
receipt/owner/Agent recall, short-interval maintenance/retry/multi-process lock,
physical mismatch and9C quota/crash regressions plus unchanged full root gates.
