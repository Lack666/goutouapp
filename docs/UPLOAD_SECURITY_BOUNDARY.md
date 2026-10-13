# Upload security boundary — Phase 9A

Endpoint: `POST /api/v1/chat-imports`. Authority is the existing
[Import API](IMPORT_API.md) and [Artifact lifecycle](IMPORT_ARTIFACTS.md), plus
the narrow fixes documented here. No new formats or analysis pipeline are added.

## Input and resource limits

- Settings default: `MAX_CHAT_IMPORT_BYTES=104857600` (100 MiB), validated >0;
  configurable, not a claimed universal constant. `CHAT_IMPORT_RETENTION_HOURS=72`.
- `ImportUploadBodyLimit` counts actual ASGI received bytes, with total body cap
  `MAX_CHAT_IMPORT_BYTES + 1048576`. Content-Length is only an early rejection hint.
  The file loop independently caps exact file bytes in 65536-byte reads.
- Starlette's locked parser closes all spooled files on BaseException; framework
  cleanup closes FormData on successful body parse including dependency/route failure.
  Current default spool threshold is 1 MiB; max_files/max_fields are each 1000,
  non-file part bound 1 MiB. No unbounded full-file memory buffer exists.
- Per upload, framework spool disk <= body cap and application artifact <= file cap
  coexist transiently: conservative default combined bound 201 MiB plus filesystem
  overhead. Partial files on process death wait for orphan maintenance. Multiple
  uploads multiply this budget; no global quota, admission cap or active upload
  timeout is implemented. 1 MiB overhead also bounds extra form payloads collectively.
- Parser defaults: 25000 characters/line, 20000/message, 120/speaker,
  1000000 candidate messages, 1000 retained issues. Current message-body buffer
  stops at message+line bound; final trim is linear. Counts and speaker inventory
  are finite but can grow with file/message limits. Worst-case unique speakers
  can consume much more heap than a two-speaker resource demo. Formal merge keeps
  one batch of 500 messages and uses `TEMP ... ON COMMIT DROP`.
- The signed real HTTP resource demo sends an exact default-sized 100 MiB file
  using generator chunks and measures Python traced allocations. See acceptance
  for actual peak/time; this excludes OS page cache, native allocations, DB memory
  and process RSS, and does not establish a global server memory limit.

## Authentication, filenames and format

JWT verification completes before server artifact `begin`. FastAPI may parse/spool
the bounded form before dependency validation; invalid credentials create no
protected Job or app artifact. Unknown signed subject fails existing User validation
and deletes its upload without committing Job/artifact metadata.

Client filename and MIME never decide storage path or source validity. Traversal,
Windows paths, device names, colon/stream strings and Unicode forms are discarded;
the original filename is not persisted. Empty filename yields framework 422;
oversized header yields controlled 400 under the locked multipart parser. Valid
Markdown under an arbitrary filename/MIME is permitted by the existing contract.
Malformed ZIP/PDF/non-Markdown cannot become a valid source merely by declaring a MIME.
Only strict WeChat Markdown V1 headers and UTF-8 are supported; no archive expansion,
HTML execution, attachments or alternate-date parser is introduced.

Empty file:400 `invalid_upload`. Unsupported format:415 `unsupported_format`.
Invalid UTF-8/NUL, or detected Markdown with no accepted valid blocks:422
`parse_failed`. Undetected/unsupported source format is415. NUL fails the entire
parse before PostgreSQL text insertion. Timezone conversion overflow produces
`invalid_timestamp` rather than uncaught 500. Valid extreme dates that fit both
local and UTC ranges remain supported. Emoji/ZWJ/bidi text is preserved as data;
exact raw labels require explicit binding and are not normalized into identity.
Partially damaged files retain accepted blocks with issue counts; existing
readiness requires all accepted speakers explicitly bound. Errors never grant readiness.

## Storage and lifecycle

Private root is trusted server configuration. Only validated 32-hex server keys
reach storage; client filenames cannot escape the root. `.part` uses exclusive
creation; final publication uses atomic same-filesystem `os.link` then part unlink,
so a racing existing `.bin` cannot be overwritten. Filesystem hard-link support
and private OS ACLs are required for this local store. Unsupported storage fails
closed; no fallback overwriting rename. File symlinks are refused; O_NOFOLLOW is
used when provided by the OS. Host-level root junction/reparse replacement and
privileged file writers are outside the HTTP threat model and require OS controls.

Upload cancellation/read exception aborts partial file and closes UploadFile.
Empty/fatal parse/register failure deletes completed source and rolls back metadata;
deletion failure gives a generic cleanup warning and later orphan retry. DB register
errors become503 `import_failed`. Failed merge retains source and ready Job for retry,
with zero partial formal rows. Hash/length must match before trusted reparse and merge.

Binding/ready/finalize/cancel all authorize actor ownership. Foreign and missing
resources share project owner-neutral errors. Finalize and cancel serialize on the
Job lock: imported+all rows or cancelled+zero rows; a racing loser gets a controlled
conflict or receipt. Terminal Jobs cannot be rebound or made ready. Imported same-Job
replay returns the durable receipt without raw source reuse. Exact duplicate dataset
policy and legitimate repeated message occurrences are unchanged.

Finalize success/cancel delete raw source; 72h expiry blocks finalize immediately.
Explicit maintenance cancels expired editable Jobs and removes expired/terminal files,
then unreferenced `.bin`/`.part` older than one hour. OSError/ArtifactStoreError cleanup
failures warn with no key/path/exception text; they do not falsify deletion counts.
Already-terminal data is not reimported to retry physical cleanup. Periodic maintenance
is NOT DEPLOYED; local acceptance executes it explicitly. No physical deletion SLA
is claimed without a scheduler. No raw artifact download/static route exists.

## Errors, logging and data separation

Existing stable error envelopes omit traceback, SQL, input, key/path and credentials.
App unexpected errors log a fixed message; the Uvicorn error logger removes exception
message/arguments/stack data before handlers can render Starlette's re-raised error.
Access logs remain disabled. Native test subprocess failures suppress private command
args and chained exceptions; Mobile error adapters retain allowlisted codes only.
Cleanup warnings are diagnostic signals, not a production alert system.

Imported RelationshipMessage rows do not enter Agent Conversation history, Prompt,
Memory or external LLM calls. Instructions in bodies/labels cannot set authenticated
owner, tool authority or self binding. Future imported analysis needs its own explicit
authorization and injection tests. No such integration is implemented in 9A.

Focused regression: `apps/server/tests/test_upload_security.py`, existing
`test_import_api.py`, `test_chat_import.py`, `test_import_jobs.py`, `test_import_merge.py`,
repository security-tooling tests, Mobile safe-error tests and complete root verify.
