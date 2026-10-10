# Phase 8D preflight audit — 2026-10-10 (Asia/Shanghai)

Baseline: clean HEAD `5083062`, marker `7 / 8C`. Scope is only 8D.
Read AGENTS, MASTER_PLAN, ARCHITECTURE, 8A/8B/8C acceptance, integration
handoff and the Import/History/client/resource contracts. Actual routes,
Pydantic schemas and generated OpenAPI are the authority.

- Upload is POST `/api/v1/chat-imports`, multipart file/source_timezone/
  source_format=`wechat_markdown_v1`. No upload operation identifier or
  recovery lookup exists. Lost response before a Job ID is an unknown outcome;
  no automatic upload retry or new server recovery contract is introduced.
- Inspect returns `id`, status, artifact state, parser counts/time bounds,
  exact raw labels, revision, readiness issues and at most 20 distinct issue-code
  samples. It exposes neither source bytes nor a complete issue report.
- Speaker/relationship PUTs and finalize POST require expected_revision.
  Ready and cancel have **no revision request body**. Ready checks ownership,
  one self/one primary Person and compatible Relationship on the server.
- No separate receipt GET exists. Imported inspect has a **summary**; finalize
  returns the full receipt. Same-Job replay requires its unchanged revision and
  works after artifact deletion. A different exact duplicate returns the first
  dataset receipt while the duplicate Job remains ready with its own artifact.
- Relationship history has limit1–200/default100 and opaque cursor. Its
  stable occurrence IDs, UTC/original timestamp/timezone, label, sender and
  import_job_id/source_index are public. Agent history remains a separate API.
- Errors include 400 invalid_upload/binding_invalid, 413 upload_too_large,
  415 unsupported_format, 422 parse_failed/validation_error, 409 stale_revision/
  job_not_ready/artifact_unavailable/binding_invalid, and 503 import_failed.
  The older UI's generic 422 binding wording does not describe every server case.
- Historical 7C docs describe unavailable resource/Agent-history contracts;
  8A–8C supersede those statements. Connected Import/History currently use a
  pending screen. Demo wizard, History ViewModels/FlatList and shared controls
  remain the presentation baseline.
- The generator maps OpenAPI binary file to string. A narrow multipart body
  serializer must supply an actual Blob/File at the generated call boundary;
  that string type must never cause a URI to be sent as transcript content.

Preflight actually passed deterministic OpenAPI36 and 24 retained PostgreSQL
Import API/Job/Merge tests. Initial sandbox pytest temporary-directory access
failed; the normal Windows execution passed. Existing Mobile regression is
run separately and is not inferred from prior PASS markers.

Real Chrome exposed a further transport discrepancy:8B's development CORS permits
only GET/POST, while existing binding routes use PUT. Native/socket calls are
unaffected, but Web preflight fails.8D minimally adds PUT for the same explicitly
configured local origins, with tests for authenticated-route preflight and denied
origins/methods. No broader origin, credentials policy or import semantics change.

Actual native selection exposed an SDK57 distinction: DocumentPicker Android
copies to `context.cacheDir/DocumentPicker`, while FileSystem `Paths.cache` in
Expo Go is experience-scoped. A strict identical-prefix check rejected a real
selected file. A subsequent real native attempt showed FileSystem also denies
reading that host cache. Android now disables the automatic picker copy, reads
only the user's granted content URI and immediately copies it into a UUID-named
owned cache File. iOS retains automatic copying; grant/copy failures fail closed.
Only owned copies are released. See the installed official
`DocumentPickerModule.kt:82`, FileSystemPath permission checks and FileSystemFile
content-URI support. This is a mobile platform fix, not a server contract change.

Dependency sources: [SDK57 DocumentPicker](https://docs.expo.dev/versions/v57.0.0/sdk/document-picker/)
and [SDK57 Expo fetch](https://docs.expo.dev/versions/v57.0.0/sdk/expo/).
Installed SDK compatibility inventory recommends picker57.0.3 and filesystem57.0.7.
DocumentPicker supplies Web File, copies native selections to cache, and has a
documented inconsistent Web cancel event; an explicit local cancel is necessary.
