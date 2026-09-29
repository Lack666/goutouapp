# Phase 3G–3H long-term memory runtime

Phase 6A exposes signed user controls and bounded inspection over this same
store; see [Memory API](MEMORY_API.md) and [ADR 0026](adr/0026-memory-control-plane.md).

The current conversation and recent messages are short-term input. Long-term
memory is a separate, small collection of user-authorized records. The Agent
never copies a transcript, response, action plan, reference, model analysis or
hidden reasoning into this collection. The frozen upstream Skill remains the
behavior source; [ADR 0015](adr/0015-consent-gated-memory.md) records this
implementation's narrower Phase 3G choices.

## Candidate, consent and write

On ordinary and boundary runs, a deterministic intent resolver looks for a
request to save and an explicit consent phrase or a previously granted opt-in.
`memory_enabled` merely enables the feature for this run; it does not grant
consent. After response generation, `memory_candidate_extractor` calls
`LLMProvider.structured_output(MemoryCandidateBatch)` with only the current
message, current FIU facts and scoped IDs. It proposes at most one fact. It
cannot write storage. The separate persistence node validates the candidate,
checks consent and pause state, and returns a typed `MemoryReceipt`. A candidate
alone is never proof of a saved memory.

Only `user`, `object` and `relationship` facts can be stored in Phase 3G.
`event` and `hypothesis` need richer provenance and correction rules and are
deferred. A fact must quote a compact substring of both the current user
message and a current F item, cite its F ID, match the F source class and the
intended owner/subject, fit within 200 characters, and pass prohibited-content
checks. The F item itself is model-produced, so these checks establish
traceability and narrow obvious promotion errors; they cannot prove semantic
truth. Secrets, sensitive identifiers, complete chats, unsupported inference
and unknowns are excluded. An empty or rejected batch writes zero records.

The service accepts one candidate per call, so one failed save cannot leave a
partially committed batch. A normalized content hash plus owner, subject, type
and relationship scope makes repeated runs, including retries of the same run, duplicates rather
than extra rows. A user has at most 200 records; recall returns at most eight.
`saved`, `duplicate`, `undone`, `nothing_to_undo`, `skipped_no_consent`, `skipped_paused`,
`rejected_validation`, `pending_confirmation` and `failed` are distinguishable
receipts. The public `AgentResult` contains a receipt and proposed candidates,
not the loaded long-term memory collection. A successful write reports its
status and count; an unsuccessful write never claims success.

## Scope, control and deletion

`MemoryService` depends on a project-owned `MemoryStore` protocol. The
standalone runtime uses `InMemoryMemoryStore`; PostgreSQL uses
`SQLAlchemyMemoryStore`, which opens and closes its own sessions. Caller code
must supply an authenticated owner ID and confirm user consent; this stage does
not implement API authentication. The database enforces same-owner
user/person/relationship foreign keys. Object and relationship memories are
visible during recall only for the current relationship; user preferences can
be recalled globally. Without a relationship ID, recall includes only user
scope. Inspect is an explicit `list_for_user` call returning typed records and
can be scoped to a person; it is not the ordinary Agent result.

Pause blocks both recall and new writes, while inspect and deletion remain
available. Resume restores recall and eligible writes only when opt-in still
exists. Revocation with keep disables recall/write while retaining inspectable
records. `delete_one` requires owner, ID and exact person scope and returns
`False` on a repeated delete. `delete_person` requires confirmation and removes
only that owner's records for that person. `delete_all` requires confirmation
and removes all of that owner's memory records, leaving conversations and
messages intact; it can also revoke consent. The graph recognizes inspect and
delete intents; delete commands return `pending_confirmation`.
The caller must invoke the corresponding service operation after an explicit
confirmation and ownership check. No business endpoint is included here.

## Undo contract closure

The Phase 3H audit found that `SKILL_CONTRACT.md` §8 marks revoking the latest
update as a **MUST**. The frozen upstream memory guide says `undo` reverses the
most recent update, its script stores at most 20 operations, and
`forget-object` clears operation history. [ADR 0016](adr/0016-memory-undo.md)
records the implementation decision. `MemoryService.undo_last(user_id)`
reverses only the owner's latest **new record insertion**, because insertion
is the only reversible memory mutation in this runtime. It works after a new
SQLAlchemy session or while consent is paused/revoked; it cannot restore a
hard-deleted record. A duplicate save creates no undo operation. Each owner
retains at most 20 operations; deleting a record or person clears affected
operations, and deleting all clears the entire owner's history. Repeated undo
after the sole operation returns `nothing_to_undo`. If multiple saved records
remain, each new `undo_last` call intentionally reverses the next latest
record; it is not a replay-idempotent network command. Phase 4 must supply API
idempotency and authenticated caller identity. The graph recognizes “撤销刚才的记忆”
and returns a typed `undone` receipt after the response.

Deletion covers app-owned active primary database memory. Production backups
and retention policy are not implemented, so no immediate deletion claim is
made for backups or external copies. There is no account deletion workflow.

## Graph and failure boundary

`normalize_input → load_memory → safety_check` loads eligible historical
records before analysis. The high-risk branch exits through safety finalization
without candidate extraction or persistence. On ordinary/boundary paths,
`relationship_analysis` receives current FIU, historical memory and reference
knowledge in separate JSON fields. Memory retains source and creation time and
is never copied into current F facts. Instructions inside a record remain
untrusted data. `response_generator → memory_intent_resolver →
memory_candidate_extractor → memory_persist` happens after the final answer.
Memory load, extraction and store errors produce generic warnings or a failed
receipt without discarding that answer. No SQL, password or provider exception
is returned publicly.

The keyless two-conversation demo is:

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked python apps/server/agent_demo.py
```

The isolated PostgreSQL tests exercise a new store/session after saving;
`scripts/check_db_migrations.py` exercises upgrade, downgrade, upgrade and
`alembic check` on a disposable database. `scripts/check_memory_replay.py`
runs the Phase 1B memory subset with Mock output and checks actual write counts.
