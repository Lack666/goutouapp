# Chat import HTTP API — Phase 5D

All routes require the Phase 4 signed Bearer JWT. The verified subject becomes
`AuthenticatedActor`; caller-supplied owner IDs are never accepted. Unknown and
foreign jobs or relationships use the same 404 response. Errors use
`{"error":{"code":"...","message":"..."}}` and never include source text,
storage keys, server paths, tokens or SQL details.

## One-upload flow

1. `POST /api/v1/chat-imports` with multipart `file`, required
   `source_timezone` (IANA name) and optional `source_format`
   (`wechat_markdown_v1`). The server reads in 64 KiB chunks, enforces
   `MAX_CHAT_IMPORT_BYTES` (default 100 MiB), stores a temporary immutable
   artifact, parses it, and creates an owner-scoped Job. HTTP 201 returns the
   typed Job view, counts, issue-code samples, exact speaker inventory,
   duplicate hint, revision and readiness issues. It contains no chat body.
   An ASGI receive guard caps the entire multipart body at the configured file
   limit plus 1 MiB of form overhead, including requests without
   `Content-Length`; the file read loop applies the exact file-byte limit.
2. `GET /api/v1/chat-imports/{job_id}` inspects the current Job, bindings,
   artifact state and durable import summary. A raw source cannot be read by
   this API.
3. `PUT /api/v1/chat-imports/{job_id}/speakers` with
   `{raw_speaker_label,binding_kind,person_id,expected_revision}` explicitly
   binds one inventory label. `person_id` is required only for `person`.
   The transport delegates all rules to `ImportJobService`. In particular,
   `我` is not inferred as `self`.
4. `PUT /api/v1/chat-imports/{job_id}/relationship` with
   `{relationship_id,expected_revision}` binds an existing owner-scoped
   Relationship. `POST /api/v1/chat-imports/{job_id}/ready` checks the 5B
   one-to-one readiness rules. Binding edits increment the revision.
5. `POST /api/v1/chat-imports/{job_id}/finalize` with
   `{expected_revision}` opens the Job's bound artifact, checks its SHA-256
   and length, then invokes 5C's reparse, fingerprint/inventory check and
   atomic merge. It returns imported/ignored/system counts, timestamps,
   dataset Job ID and `new_message_count`. The client sends no second file.
   Replaying an imported Job returns the durable receipt after raw deletion.
6. `POST /api/v1/chat-imports/{job_id}/cancel` cancels an editable Job and
   removes its temporary source. It does not remove existing imported data.

`GET /api/v1/relationships/{relationship_id}/messages?limit=100&cursor=...`
returns owner-scoped historical messages. `limit` is 1–200. An opaque cursor
continues strict UTC timestamp, Job ID, source index and row ID order. The
response is `{items,next_cursor}`. There is no unbounded history route.
These messages remain separate from Agent Conversation history.

Stable import codes include `invalid_credential` (401), `job_not_found`
(404), `invalid_upload` (400), `upload_too_large` (413),
`unsupported_format` (415), `parse_failed` (422), `stale_revision` (409),
`binding_invalid` (400/409), `job_not_ready` (409),
`transcript_mismatch` (409), `artifact_unavailable` (409/503) and
`import_failed` (503). Malformed framework request fields return the shared
`validation_error` (422).

Content-Type and filename are untrusted metadata. The parser decides source
validity. Phase 5A line, message, speaker and issue limits still apply. No
upload or finalize calls an LLM, Agent, analysis or Memory workflow.
Cross-file partial-overlap deduplication and analysis of imported history are
deferred. See [Artifact lifecycle](IMPORT_ARTIFACTS.md),
[Imported messages](IMPORTED_MESSAGES.md) and
[Phase 5D acceptance](PHASE_5D_ACCEPTANCE.md).

## Phase 9B navigation supplement

History cursors now use opaque v2 positions bound to owner and Relationship.
Malformed, old or mismatched-scope cursors return existing invalid pagination400;
Refresh obtains a current cursor. Owner queries remain independent authority.
Ordering/page sizes/public DTOs are unchanged; this is not a fixed snapshot.
All9A upload guards remain. See ADR0037 and authorization audit.
