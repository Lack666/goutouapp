# ADR 0034 — Mobile import and separate relationship history

Date: 2026-10-10. Scope: Phase 8D only.

Reuse the generated client, single ApiTransport/DevelopmentSession, resource
selectors, ImportStep/source/speaker ViewModels, shared controls and History
FlatList. Add feature adapters/controllers rather than a new database, auth
store or parser. Generated Import/History methods become explicitly permitted;
Memory routes remain disabled. No production server contract changes.

DocumentPicker57.0.3 selects native provider documents. FileSystem57.0.7
supplies a readable binary File; Web uses DocumentPicker's actual File.
Keep URI/Blob private to the controller and expose only name/size/MIME.
Native testing found SDK57's host DocumentPicker cache differs from Expo Go's
experience-scoped FileSystem cache and cannot be read by the scoped module.
Android disables that automatic copy and immediately copies the user-granted
content URI into a UUID-named owned File. iOS keeps automatic copying. Verify
readability/size, bound copies by the client byte limit and clean up failed owned
copies. Release only owned files; do not delete provider originals or promise
immediate OS-cache erasure. Original grants are not a durable upload outbox.

Explicit upload supplies binary FormData through the generated body's serializer, bridging
OpenAPI's generated binary-as-string representation. Libraries own the boundary.
No URI-as-body or base64. Installed Expo fetch buffers the bounded multipart body;
this is not resumable or streaming upload. Client100MiB is a precheck and the
configured server limit is authoritative. Copies are released on successful
upload, replacement, leave, reset and credential invalidation; OS cache/privacy
and backup erasure are not promised.

Upload creation has no operation-key recovery endpoint. A lost response before
Job ID is unknown_upload_outcome, preserves selected metadata and blocks repeat
upload. An explicitly labelled new import can create another Job. Known IDs are
inspected on return/foreground or manually recovered after process restart.
No durable outbox/job store is added. Server cancel and client stop differ.
Binding/finalize use the last server revision; conflicts inspect and invalidate
explicit confirmations. Changes of Relationship revoke speaker confirmation.
Ready is authoritative on the server; it has no revision body in the current API.
Finalized inspect summaries are displayed as summaries. Explicit same-Job replay
retrieves the full receipt after raw deletion. Exact-dataset duplicates retain
their existing Phase5 semantics and may leave the new Job ready.

History reads separate generated Agent/Relationship DTOs after owned-parent
verification. Preserve server occurrence order and microseconds, identity and
historical/original/source-zone provenance. Opaque cursor/100-row pages, serialized
More, server-ID-only merge and 2,000-row collection limit bound loading. Route,
domain, owner and relationship changes abort and discard old state; session epochs
and request generations reject late updates even when fetch ignores abort.
Background pauses/clears History and foreground verifies/refreshes its scope.
The system picker itself can change AppState, so its epoch-guarded result survives
that transition. Process death loses session-local Job metadata; known UUID
recovery never resubmits a file.

Import completion only persists external history. AgentService, Memory, FIU,
Profile, provider prompts and frozen Knowledge remain unchanged. Separate native
and browser evidence is required; Web does not prove Android content-provider
conversion or file permissions. Memory integration begins only with a new8E task.
