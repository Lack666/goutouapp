# Phase 8 Mobile integration handoff — 2026-10-09

Current Phase8C connects owned Conversation Chat through generated REST/History
and existing authenticated POST SSE, with V1 validation, retained operation keys,
explicit unknown outcomes and server-ID reconciliation. Shared8B session/native
credentials and Demo are preserved. See [8C report](PHASE_8C_ACCEPTANCE.md).
Import/RelationshipMessage history remain8D, Memory controls8E. No future stage begins.
The8B/8A historical handoff below is superseded for Agent Chat only.
Revalidated on 2026-10-10 at existing HEAD f4cb2cc/marker7/8C. All root gates
passed again; actual Android native core Chat/Chinese SSE/replay/history/logout/
owner-isolation evidence now exists. Native active-run faults/background/expiry
and complete keyboard QA remain open. See the current8C report; whole8 stays
incomplete and8D/8E have not started.

This handoff preserves the Phase7D/8A audit and adds current 8B client integration.
Whole Phase8 is IN PROGRESS / NOT YET COMPLETE. Mobile now has generated resource
HTTP, native SecureStore/Web volatile Development Session and owned-resource
create/list/detail. The entries below retain historical 8A dispositions where
explicitly labelled; current 8B completion supersedes their deferred-client wording.
See MOBILE_API_CLIENT, MOBILE_DEV_AUTH, MOBILE_RESOURCE_INTEGRATION and 8B acceptance.

Current disposition: **IMPLEMENTED IN 8B** — generated36-operation contracts and
callable client from the sole OpenAPI authority; manual development JWT probe/
expiry/logout/401; cancellation/epoch owner isolation; explicit UUID resource
acquisition and same-body retries; opaque domain cursors and real Chrome/HTTP/DB
integration. **NOT RUN** — native connected/storage/background smoke; final Phase8
still needs actual Android proof. **DEFERRED** — 8C Agent REST/POST SSE, 8D actual
Import/History, 8E Memory networking. No generated future function implies completion.
Historical 7D audit base: server at `6f9e17c`;
generated locally from `create_app(Settings(_env_file=None, llm_provider='mock')).openapi()`.
Evidence: `.cache/phase7d-openapi.json` and `.cache/phase7d-openapi-audit.log`.
That inventory had 26 method/path operations, including three health/status
operations. Phase 8A verified the same pre-edit assembly at `ccabc98` and adds
ten resource/history operations for a total of 36, preserving all old operation,
schema and security hashes. See [resource API](RESOURCE_API.md),
[formal generation input](contracts/openapi.json), [baseline](contracts/phase7d-openapi-baseline.json)
and [8A acceptance](PHASE_8A_ACCEPTANCE.md). OpenAPI describes the current assembly; service code and existing
integration tests establish semantics beyond its schema.

Each capability below has one of the required dispositions. A confirmed API
means the server implementation exists; it does not mean Mobile calls it.
All signed operations use the actor from Bearer verification, never a supplied
user ID or synthetic Mobile `demo-a` / `demo-b` identifiers.

## Auth and resource prerequisites

- **EXISTING API — CONFIRMED**: Bearer HS256 JWT verification with UUID `sub`,
  signature, expiry, issuer and audience checks, plus existing-owner checks.
  See `app/api/dependencies.py`, `app/auth/`, [authentication](AUTHENTICATION.md).
  There is no production HTTP token issuer in the OpenAPI inventory.
- **EXISTING TOOLING — CONFIRMED**: Phase 4 tooling
  `apps/server/dev_auth_cli.py bootstrap` / `token --user-id ...` supplies
  development identities and short-lived signed credentials, subject to its
  environment restrictions. This is a CLI, not an HTTP login API or production
  account system. In APP_ENV=development, bootstrap supplies a real existing
  local UUID and token signs it for 15 minutes. Development handoff for 8B is
  a manually supplied short-lived Bearer credential; signing secret stays on
  the server, and token/session entry/storage/expiry/logout remain 8B. No public
  signer, bundled JWT, console-token logging or production login is added.
- **FUTURE / OUT OF SCOPE**: Formal registration/password/OAuth/refresh/revocation
  account flows are absent. They require separately agreed account-system scope.
- **SERVER GAP — PHASE 8 COORDINATION**: Production identity acquisition remains
  absent; the manual development credential contract does not provide accounts.
- **FUTURE / OUT OF SCOPE** for this 8A delivery: SecureStore/session/token storage
  has not been implemented. Phase 8 owns secure local lifecycle, expiry handling
  and credential removal; server authority must remain separate from UI state.
- **EXISTING API — CONFIRMED (8A)**: Person POST/GET `/api/v1/persons`, GET
  `/api/v1/persons/{person_id}` return real owned UUID/name/times, without inferred
  identity/profile fields. Import/Memory selectors must use these actual resources.
- **EXISTING API — CONFIRMED (8A)**: Relationship POST/GET `/api/v1/relationships`,
  GET `/api/v1/relationships/{relationship_id}`. Explicit owned Person and required
  type/status strings including `unknown`; no romance inference. This is a narrow
  resource, not a structured Profile DTO.
- **EXISTING API — CONFIRMED (8A)**: Conversation POST/GET `/api/v1/conversations`,
  GET `/api/v1/conversations/{conversation_id}`. Optional owned Relationship or
  generic null association; no Person/title/status fields exist. A new resource
  immediately works with AgentService; expected_relationship_id stays its authority.
- **EXISTING CONTRACT — CONFIRMED (8A)**: Each creation requires a fresh UUID v4
  retained for the same logical payload on retries. It becomes the real resource
  ID. Matching requests replay 201/the original timestamps; changes return409;
  foreign reserved IDs/bindings use generic404. Reservation lasts with the row.
  No resource operation_key/AgentRun receipt. Lists default30/max100 with opaque
  cursor and `{items,next_cursor}`. See RESOURCE_API for normalization and lifetime.
- **FUTURE / OUT OF SCOPE (8A)**: Mobile acquisition/controllers/resource selection,
  generated client and session storage are 8B. Server availability is not UI integration.

## Chat, public answer and stream

Authority: `app/api/v1/agent_runs.py`, `app/schemas/agent_run.py`,
`app/schemas/stream_event.py`, `app/services/agent_service.py`,
[Agent API](AGENT_API.md), [SSE](STREAMING_API.md), [idempotency](IDEMPOTENCY.md).

- **EXISTING API — CONFIRMED**: `POST /api/v1/conversations/{conversation_id}/agent-runs`.
  Request: nonblank `message` (maximum 20,000), optional UUID
  `expected_relationship_id`, optional bounded `operation_key`. The existing
  composer limit of 2,000 is a UI constraint, not the server limit.
  Response `AgentRunResponse`: `run_id`, `conversation_id`, `status`,
  `assistant_message {id,role,content}`, `memory_status`, `warnings`.
- **EXISTING API — CONFIRMED**: POST at the same path plus `/stream` accepts
  identical JSON and Bearer header; it returns `text/event-stream`. It is neither
  WebSocket nor a GET EventSource route. Each complete frame has a V1 JSON
  envelope `{schema_version,event,run_id,data}`; transport chunks are not frames.
- **EXISTING API — CONFIRMED**: All events share the persisted `run_id`.
  Supported events: `run_started`, `status`, `final_response`, `memory_status`,
  `pending_confirmation`, `completed`, `failed`. A validated committed answer
  arrives whole in `final_response`, not token by token. `failed` has generic
  code/recovery status; no fabricated assistant reply follows a failure.
- **EXISTING API — NEEDS CONTRACT REVIEW**: Map the seven UI presentation states
  to request lifecycle and actual public progress values; current `completed`
  synthetic FIU cards are teaching fixtures, not server answer fields.
  Pre-stream HTTP JSON errors and post-header `failed` events need separate recovery.
  `pending_confirmation` must lead to explicit Memory control flows rather than
  execute conversational undo/delete or grant consent.
- **EXISTING API — CONFIRMED**: `operation_key` is actor/Conversation scoped.
  Reuse only for the same logical payload. Same-key completed REST/SSE requests
  replay persisted results without another Agent/Memory execution; running,
  failed, stale and conflicting requests fail closed. New attempts use new keys.
- **EXISTING API — NEEDS CONTRACT REVIEW**: Disconnect/replay UI policy.
  A precommit disconnect cancels and marks failure; a postcommit disconnect keeps
  the completed answer. Completed SSE replay contains only final/completed.
  A running operation cannot be reattached; no Last-Event-ID resume or public
  AgentRun inspect endpoint exists. `running_unknown` needs truthful reconciliation
  UX; agree any server recovery gap before showing retry as a fresh successful run.
- **FUTURE / OUT OF SCOPE**: Token-level streaming, WebSocket, live attach,
  heartbeat/version negotiation and production reconciliation are absent.

## History and cursor mapping

Authority: `app/api/v1/resources.py`, `app/services/resources.py`,
`app/api/v1/chat_imports.py`, `app/services/import_merge.py`,
`app/schemas/chat_import.py`, [imported history](IMPORTED_MESSAGES.md).

- **EXISTING API — CONFIRMED (8A)**: Public Agent history
  `GET /api/v1/conversations/{conversation_id}/messages?limit=...&cursor=...`.
  Owner-validated Conversation, default30/max100, ascending created_at/UUID,
  `{items,next_cursor}`. Message fields: id/conversation_id/user-or-assistant/
  content/created_at, without tool/speaker/internal state. Reads the actual Message
  domain independently of AgentService's latest20 input; no imported rows.
- **EXISTING CONTRACT — NEEDS CLIENT IMPLEMENTATION**: Resource/Agent cursors
  are owner/domain/parent-bound navigation values. Every query authorizes separately.
  Per-page committed/live reads, not a held snapshot; refresh after exhaustion or
  late commits/backfills/deletions. Preserve occurrences, stable IDs and scope resets.
- **EXISTING API — CONFIRMED**: Imported history
  `GET /api/v1/relationships/{relationship_id}/messages?limit=...&cursor=...`.
  Default 100, maximum 200; response `{items,next_cursor}`. Fields include UUID
  ID/scope, import job/dataset ID, source index, aware historical timestamps,
  timezone/original timestamp, sender kind, Person ID, raw label and plain content.
  Owner checks apply to the actual Relationship, with stable keyset order.
- **EXISTING API — NEEDS CONTRACT REVIEW**: Adapter maps `timestamp_utc` to
  historical time, `import_job_id` to dataset provenance and
  `self/person/system` independently from Agent `user/assistant`. Preserve
  server occurrence order and row identity; do not deduplicate by text.
- **EXISTING API — NEEDS CONTRACT REVIEW**: Treat `next_cursor` as opaque,
  retain per owner/relationship/domain, clear on scope/logout/reset, guard
  concurrent More requests and append each returned occurrence once.
  Local 30-row windows and 1,020-row fixtures demonstrate rendering only;
  they are not an implementation of real cursor pagination or bounded network storage.
- **EXISTING API — CONFIRMED**: Repository/service ownership and composite
  scope constraints exist for imported data. Mobile still needs actual owned
  resource acquisition; a URL parameter is not authorization.

## Import workflow

Authority: `app/api/v1/chat_imports.py`, `app/schemas/chat_import.py`,
`app/services/import_workflow.py`, `app/services/import_jobs.py`,
[Import API](IMPORT_API.md), [jobs](IMPORT_JOBS.md), [artifacts](IMPORT_ARTIFACTS.md).

- **EXISTING API — CONFIRMED**: Multipart `POST /api/v1/chat-imports` with
  `file`, required `source_timezone`, optional supported `source_format`.
  Phase 5D owns a bounded private artifact, parsing and persistent owner-scoped Job.
  Do not upload again for finalize. Authentication precedes artifact creation.
- **EXISTING API — CONFIRMED**: `GET /api/v1/chat-imports/{job_id}` inspects Job
  status, artifact state, inventory, binding revision, readiness issues, parser
  counts/time/warning metadata and completed receipt summary.
- **EXISTING API — CONFIRMED**: `PUT /api/v1/chat-imports/{job_id}/speakers`
  accepts preserved `raw_speaker_label`, `binding_kind`, nullable `person_id`,
  `expected_revision`; mapping remains explicitly user-confirmed.
- **EXISTING API — CONFIRMED**: `PUT /api/v1/chat-imports/{job_id}/relationship`
  accepts nullable `relationship_id` plus `expected_revision`; owned resources
  and compatibility remain service checks, not frontend inference.
- **EXISTING API — CONFIRMED**: `POST /api/v1/chat-imports/{job_id}/ready`
  performs authoritative readiness. The local `loaded`, confirmation and
  `演示预检通过` flags are not substitutes for a server Job status.
- **EXISTING API — CONFIRMED**: `POST /api/v1/chat-imports/{job_id}/finalize`
  accepts `expected_revision` and returns `ImportReceiptResponse`, including
  original/dataset Job IDs, Relationship, counts, historical bounds,
  fingerprint, status and import time. Exact-dataset duplicates have explicit
  merge semantics; do not infer duplicates from text or UI warnings.
- **EXISTING API — CONFIRMED**: Cancel uses
  `POST /api/v1/chat-imports/{job_id}/cancel`. Successful/cancelled imports clean
  artifacts; inspect supplies a receipt summary after completion. No standalone
  `GET /receipt` route exists. Imported-message history is the endpoint above.
- **EXISTING API — NEEDS CONTRACT REVIEW**: Map parser issue samples/truncation,
  revisions, expiration/cancelled artifacts and merge receipts to UI recovery;
  retries must respect actual revision and durable workflow status. Native picker
  MIME/UTF-8/size handling and real upload adapter are Phase 8 work.
- **EXISTING API — CONFIRMED (8A)**: Person and Relationship resources now supply
  explicit binding IDs. Mobile acquisition/upload adapters remain future work;
  a selected nickname or synthetic fixture ID cannot authorize binding.

## Analysis / FIU / Profile

- **EXISTING API — CONFIRMED**: Public final answer is text in REST
  `assistant_message.content` and SSE `final_response.data.answer`, with bounded
  run/memory status. The independent Python AgentResult exposes richer internal
  structured values but is not the current Mobile transport response.
- **SERVER GAP — PHASE 8 COORDINATION**: Public FIU and structured Profile DTOs
  are absent in both OpenAPI and the V1 SSE envelopes. Agree minimal public DTOs
  or a text-only presentation; do not expose private Memory evidence, prompts,
  loaded knowledge or hidden reasoning and do not parse model prose as confirmed facts.
- **SERVER GAP — PHASE 8 COORDINATION**: Imported RelationshipMessage does not
  enter AgentService history or current analysis input. History reads the Agent
  Conversation/Message domain, not imported messages. Any explicit scoped analysis
  context selection/size/provenance needs a server contract and separate evaluation.
- **SERVER GAP — PHASE 8 COORDINATION**: No import-completed → Agent analysis
  workflow/endpoint exists. Finalize persists external chat and returns a receipt;
  it does not create an Agent answer or automatically save Memory.
- **FUTURE / OUT OF SCOPE**: RAG, new analysis behaviors and upstream Skill changes.

## Memory controls and guarded mutations

Authority: `app/api/v1/memory.py`, `app/services/memory_control.py`,
`app/services/memory_mutation.py`, `app/retention.py`,
[Memory API](MEMORY_API.md), [deletion](MEMORY_DELETION.md),
[retention](MEMORY_RETENTION.md), [backup boundary](MEMORY_BACKUP_DELETION_POLICY.md).

- **EXISTING API — CONFIRMED**: `GET /api/v1/memory/control`,
  `POST /api/v1/memory/consent {enabled}`, `/memory/pause`, `/memory/resume`.
  Control includes consent, pause, effective read/write and update time.
  Revoke retains records and pauses; grant preserves pause; resume cannot grant.
- **EXISTING API — CONFIRMED**: `GET /api/v1/memories` with owner-bound optional
  Person/Relationship filters, limit (maximum 50) and opaque cursor; response
  includes active `items`, `next_cursor`, `retention_policy_summary` and historical
  notice. `GET /api/v1/memories/{memory_id}` permits scoped inspection of existing
  records including expiry/state. There is no public `include_expired` query.
- **EXISTING API — NEEDS CONTRACT REVIEW**: Map public content/provenance summary,
  subject/scope, creation/expiry and state to inspect ViewModels. Fetch required
  scope resources and preserve historical notices. Do not map private raw evidence.
- **EXISTING API — CONFIRMED**: `GET /api/v1/memory/undo/preview` returns
  availability/latest-operation/Memory ID and limited target metadata.
  `POST /api/v1/memory/undo` requires exact `expected_operation_id` and
  `operation_key`. Stale/expired operations do not fall back to another target.
- **EXISTING API — CONFIRMED**: Server challenges are created by
  `POST /api/v1/memory/deletions/one/prepare` (`memory_id`, optional expected scope),
  `/person/prepare` (`person_id`) or `/all/prepare`
  (`revoke_consent_after_delete` explicitly chosen).
  Public challenge contains owner/action/target/scope, expected count, authorization
  choice, issue/expiry and deletion notice; snapshot hash remains server-owned.
- **EXISTING API — CONFIRMED**: Execute uses
  `POST /api/v1/memory/deletions/{confirmation_id}/execute {operation_key}`;
  mutation inspection uses `GET /api/v1/memory/mutations/{mutation_id}`.
  Receipt includes action/status/count/target/scope/time/replayed and primary-store
  notice. The server serializes, rechecks and consumes challenges atomically.
- **EXISTING API — NEEDS CONTRACT REVIEW**: The Demo acknowledgement is not a
  server challenge. Real UI must review the server-owned count/scope/expiry,
  prepare again after target/consent-choice changes and use a stable operation key
  for retries. One/person/all are distinct; preserve/revoke all-delete choice
  must never be silently supplied by a default UI confirmation.
- **EXISTING API — CONFIRMED**: Retention summary and record expiry/state already
  exist in inspection DTOs. Recall excludes expiry independently of physical
  cleanup. Display server policy, not hardcoded 180 days.
- **FUTURE / OUT OF SCOPE**: No public retention-policy editor, scheduled
  maintenance endpoint, production scheduler, backup rotation/restore deletion
  replay or instant full-backup erasure exists.

## Mobile seams to preserve

`_layout.tsx` selects the injected source; screens consume typed UI contracts.
`readChat/readRelationships/readImport/readHistory/readSettings` currently return
synchronous Demo templates; `kind: 'demo'` is deliberately honest. Phase 8 should
add async resource/controllers and authoritative DTO adapters at this composition
boundary, preserving rendering, explicit identity choice, domain discriminants,
FlatList windows, scope resets, theme and guarded confirmation UI. Do not pretend
the present interface already is a network client.

The SDK/React Native/Router/toolchain lock remains unchanged. Generated TypeScript
types alone will not describe SSE event semantics (OpenAPI declares the stream
body as text). Phase 8 must review a public event schema/version mapping and test
split UTF-8/chunk boundaries, terminal errors, disconnect/replay and stable IDs.
No generated client, parser or token storage is delivered by Phase 8A.

Generate future 8B types only from `docs/contracts/openapi.json`, checked with
`uv run --locked python scripts/export_openapi.py --check`. Export is deterministic
and offline; all 26 old operations/schemas/security are compatibility-gated. Use
the separate STREAMING_API V1 contract when implementing later SSE consumption.

Stop after 8B. Begin 8C only on a new explicit instruction. Resource/history
server gaps are closed; Mobile message-history/import/Memory networking, production
accounts, public FIU/Profile and imported-data analysis gaps remain. Do not enable
an analysis button based on import completion.
