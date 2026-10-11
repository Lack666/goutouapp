# Master plan

Source specification: `knowledge/goutoujunshi`, commit
`6db7354a4002dc7c448a9c87ffdad8132570c9d3`. The snapshot is MIT
licensed and its content hashes are frozen in `knowledge/upstream-manifest.json`.

## Phase gate

A phase passes only with CODE, TEST, DOC, DEMO, and REGRESSION. `make verify`
checks the gates implemented so far and names future gates as deferred. A
phase report records the exact command and output. No future feature is counted
as implemented by a placeholder directory or a golden expectation.

| Phase | Deliverable | Status |
| --- | --- | --- |
| 0 | Repository bootstrap, upstream audit, monorepo, verification | PASS |
| 1 | Skill contract and at least 40 synthetic Golden Cases | PASS |
| 2 | FastAPI, PostgreSQL, Pydantic, SQLAlchemy, Alembic, LLM Provider foundation | PASS |
| 3 | Standalone LangGraph runtime and Agent streaming integration | PASS |
| 4 | Agent Service and API transport over the standalone runtime | PASS |
| 5 | Chat Import and Relationship Data Pipeline | PASS (5A–5D) |
| 6 | User-facing memory controls and retention policy integration | PASS (6A–6D) |
| 7 | Expo React Native MVP | PASS (7A–7D) |
| 8 | Mobile API integration, generated client and stream consumption | IN PROGRESS / NOT YET COMPLETE (8A–8E engineering PASS) |
| 9 | Security, privacy, reliability and deletion | PENDING |
| 10 | Optional hybrid RAG with pgvector | PENDING |
| 11 | Agent eval and observability | PENDING |
| 12 | CI/CD, EAS preview, release preparation | PENDING |

## Exit criteria by phase

0. Preserve upstream exactly; inspect skill, README, documentation, references,
   scripts and license; record commit; run upstream validator and repository
   verifier. Demo: verified snapshot and `doctor` output.
1. Record behavioral, safety, evidence, memory, response, and knowledge
   contracts. Validate at least 40 anonymous synthetic cases with scenario,
   safety, references, and assertions. Demo: run the dataset validator. This
   phase tests the **evaluation specification**, not an absent Agent.
2. CRUD storage and migration with ownership checks; API/OpenAPI and database
   integration tests; local Compose demo.
3. Keyless MockLLM and OpenAI-compatible provider behind `chat`, `stream`, and
   `structured_output`; standalone LangGraph `run()` and typed `stream()`,
   consented memory with undo, independent CLI/Python demos, individual node
   tests and full standalone E2E regression.
4. Compose the standalone runtime behind Agent Service and owner-scoped API
   transport; map typed events to a network stream, orchestrate conversation,
   message and AgentRun persistence, and define API idempotency and disconnect
   behavior. No new relationship reasoning or embeddings.
5. A versioned WeChat Markdown parser, explicit speaker/relationship binding,
   provenance, owner-scoped imported history, one-upload authenticated API,
   bounded pagination, exact-dataset idempotency and artifact lifecycle with
   representative and 10k-message fixtures. Other formats and relationship
   analysis require later explicit scope.
6. Expose confirmed consent, inspect, pause, resume, undo and deletion controls
   through the service boundary, with owner/person isolation and production
   retention-policy decisions. The Phase 3 memory runtime is the baseline.
7. Six mobile surfaces: home, chat, relationship/profile, import/analysis,
   history, settings. Typecheck and on-device or Expo web demo.
8. OpenAPI-generated TypeScript client and mobile consumption of stable
   transport events with run and idempotency IDs.
9. Upload limits and type checks, traversal prevention, access isolation,
   deletion, log redaction, and high-risk safety priority.
10. Optional metadata, keyword/BM25, vector and rerank retrieval; prove value
    against deterministic baseline. `FEATURE_RAG=false` remains complete.
11. Behavioral eval on the running Agent, observability of nodes, latency,
    provider, tokens, cost and outcome; optional LangSmith failure isolation.
12. Locked dependencies, CI, Docker/Compose, EAS preview and release checklist.

## Implementation log

### Phase 8E — Memory Controls and Guarded Mutations Mobile Integration

- Current scope is8E only; whole8 remains IN PROGRESS,8F not started.
- 8D evidence repaired and closed first under marker7/8D: complete root exit0
  independently recorded, backend556/Mobile298, Demo22/Connected3+3+4, unchanged
  OpenAPI36 and Golden83. Original Mobile296 plus2 arrival-order tests;217→219
  traced to commit5083062 durable logout tests. Exact anonymous Android fixture
  cleanup deferred while the existing device is unavailable.
- Implementation uses existing generated13 Memory APIs, JWT/session/epoch,
  authoritative consent/pause/retention inspection, guarded latest Undo and
  one/Person/all server challenges with explicit confirmation/durable receipts.
  Immutable session attempts safely replay original targets; no local journal
  or MemoryStore. Chat navigates only; Demo and production Agent behavior preserved.
- New48 focused cases and real Memory HTTP/Expo Web gates are added to full root.
  Complete pre-marker root exited0 (556/346/48/36,Demo22,Connected3/3/4/5).
  Marker advanced only to7/8E; complete post-marker root also exited0 with the
  same556/346/48/36 and22/3/3/4/5 results. Applicable8E gates PASS. Native
  Memory is NOT RUN and carried to8F; never inferred from Chrome.
  See [Memory](MOBILE_MEMORY_INTEGRATION.md) and [8E report](PHASE_8E_ACCEPTANCE.md).

### Phase 8D — Chat Import and History Mobile Integration

- 2026-10-10 starts at clean5083062/marker7/8C. Audited actual Import routes,
  generated DTOs, shared session/transport, server revision/receipt/cancel and
  artifact contracts before connecting existing wizard/history presentation.
- Explicit user file selection, binary multipart/IANA timezone, real Job inspect,
  owned Person/Relationship submissions, server readiness/finalize/receipt/replay/
  cancel now use the existing APIs. No upload-recovery endpoint exists: lost Job
  ID is unknown, blocks automatic re-upload and is distinct from finalize replay.
- Separate owned Agent/Relationship history preserves occurrence IDs, source
  provenance, equal timestamps and identical content through opaque100-row pages,
  serialized More and a2,000-record collection limit. Epoch/scope/route/logout
  guards reject late responses; no imported-chat analysis or Memory invocation.
- SDK57-compatible DocumentPicker/FileSystem, lockfile and real Web picker.
  Android native testing exposed unreadable Expo Go host picker cache; Android
  now copies the user-granted content URI directly into owned cache before upload.
  The only server change is PUT CORS for the same local development origins.
- Actual JWT/FastAPI/PostgreSQL HTTP3 and Chrome import/history1 passed, including
  1,001 occurrences/all11 cursor pages, revision conflict, same-Job/exact-dataset
  replay, committed response loss, foreign owner denial and zero Agent/Memory writes.
  Latest complete pre-marker root exited0: backend556,repository30,Mobile296,
  focused77,Demo22,8B3,8C3,8D4,Doctor21/21 and all prior regression gates.
- Actual Pixel_10/Android17/API37/Expo Go57.0.9 core native picker/binary/Job/
  explicit bindings/ready/finalize/receipt passed:1,001 persisted messages,
  Agent0,Memory0,active artifact0. Formal native History showed ready/100.
  Native More/full lifecycle/fault/OwnerB/performance matrix remains incomplete;
  expiry cleared editable Job/file UI. Web is not substituted for native evidence.
- Marker advances only to7/8D after applicable engineering gates. Accepted-marker
  full root rerun passed the same296/77/556 and22/3/3/4 regression gates.
  Whole Phase8 remained incomplete;at8D acceptance8E was not started.
  See [8D acceptance](PHASE_8D_ACCEPTANCE.md), [API audit](PHASE_8D_API_AUDIT.md),
  [Import/native steps](MOBILE_IMPORT_UI.md), [History](MOBILE_HISTORY_UI.md) and
  [ADR0034](adr/0034-mobile-import-and-relationship-history.md). Stop after8D.

### Phase 8C — Agent Chat REST / POST SSE Integration

- 2026-10-10 revalidation starts from the existing f4cb2cc/7/8C implementation,
  rather than assuming7/8B. Complete root verification passed again. Actual
  Pixel_10/Android17/API37/Expo Go57.0.9 core smoke observed native reader chunks,
  Chinese committed text/completed, same-key REST/SSE replay, History, post-run
  Back, credential restoration/logout and OwnerB isolation. Active native faults,
  background/expiry and complete keyboard QA remain open; whole8 incomplete.
  Only the disposable native demo gains port/scenario options; temporary probes
  are removed. Historical8C acceptance remains preserved below its new addendum.
- Reuse generated client, actual owned Conversation, shared JWT/session/origin,
  navigation/theme/composer/FlatList; connect Agent REST/POST SSE and public Agent
  History. Import/RelationshipMessage History and Memory controls remain deferred.
- Independent incremental UTF-8 parser validates narrow V1 envelopes/order/run IDs,
  bounded frames and terminal state. Native adapter uses installed expo/fetch;
  Web/socket and native verification remain separate.
- Immutable per-action operation keys, controlled cross-transport replay, explicit
  unknown outcomes and Message-ID reconciliation prevent duplicate execution/bubbles.
  Page/session generation, cancel/deadline/expiry and owner guards reject stale data.
- Actual CLI JWT/FastAPI/PostgreSQL/MockLLM/Expo Web demo and both full root runs
  passed (exit0). Accepted-marker results: backend555, repository27, Golden83,
  Mobile217 (143 retained +74 new), focused46, parser28, Demo Web22, resources3 and
  Agent Chat3. Native Connected SSE NOT RUN; Doctor21/21 and Android JS export are
  distinct evidence. Marker advanced only to7/8C after all applicable gates;
  accepted-marker full rerun also passed. Whole Phase8 incomplete.
  See [8C acceptance](PHASE_8C_ACCEPTANCE.md), [Agent Chat](MOBILE_AGENT_CHAT.md)
  and [streaming](MOBILE_STREAMING.md). At that acceptance work stopped after8C;
  8D/8E had not started.

### Phase 8B — Generated client, development session and owned resources

- Generate TypeScript contracts, UUID fields, operation/auth inventory and callable
  openapi-fetch client from the unchanged 8A OpenAPI. Separate pinned generator
  TS5 workspace preserves Mobile TS6 and peer compatibility; byte/source-hash
  checks and mutation tests reject input/output drift.
- Add native SecureStore/Web volatile development JWT session, real server probe,
  expiry/401/logout, serialized storage and epoch/cancellation guards. Demo remains
  available; Connected uses resource adapters/controllers for explicit create/list/
  detail, opaque pages and stable UUID retries, with no synthetic fallback.
- Real CLI JWT/FastAPI/PostgreSQL/generated-client/Chrome integration verifies
  response-loss retries, concurrency, owned resources, cross-page UUIDs and A→B
  isolation. Only explicit local development/test CORS is added to the server.
- Native emulator attempts did not yield stable adb; Android connected runtime
  remains NOT RUN. Doctor and JS export are separate checks; final Phase8 still
  requires Android connected proof. Whole Phase8 remains incomplete. At8B acceptance,
  8C Agent REST/SSE, 8D Import/History and 8E Memory were not started. Full pre-marker root
  verification passed: backend555, Mobile143 (retained95 + new48), old Demo Web22,
  real Connected3, generated3, repository24 and Golden83. Marker advanced only to
  `7 / 8B`; accepted-marker full verification also exited0 with the same passing
  counts. See [8B report](PHASE_8B_ACCEPTANCE.md).

### Phase 8A — Public resource APIs and integration contract foundation

- Add ten signed Person/Relationship/Conversation create/list/detail and Agent
  Message history operations over existing PostgreSQL rows, without migrations,
  inferred Profile fields or imported-chat analysis. Generic Conversations remain
  valid. AgentService remains the expected-relationship authority.
- Required stable UUID v4, transaction advisory locks and existing PKs give
  row-lifetime retry safety; matching payloads replay, changes conflict. Owner
  checks, bounded timestamp/UUID pages and explicit public projections apply.
- Export deterministic OpenAPI generation input with all 26 actual Phase 7D
  operation/schema/security hashes preserved and ten additions. Refine development
  JWT/resource/history handoff. Mobile/client/session/SSE remain deferred.
- Focused 97 signed JWT/PostgreSQL/contract/concurrency/rollback/history/socket
  tests and actual Uvicorn demo pass. Complete pre-marker verifier passed at7/7D:
  backend545, repository21, Mobile95/Web22, Golden83 and all0–7 gates. Marker
  advanced only to `7 / 8A`; accepted-marker full rerun also exited0 with the same
  results. Phase8A is PASS. Whole Phase8
  was PENDING at 8A acceptance; 8B/8C had not started at that point.
  See [resource API](RESOURCE_API.md) and [8A acceptance](PHASE_8A_ACCEPTANCE.md).

### Phase 7D — Mobile MVP integration and Phase 7 final acceptance

- Verified the six interactive surfaces as complete real Expo Web journeys in
  both palettes at 320/360/412px. Preserved 13 existing browser cases and added
  nine integration/deep-link/scope/lifecycle/error-recovery cases: 22 PASS.
- Fixed three observed P1 issues with targeted regression: Import Next now
  requires explicit identities and relationship confirmation; Chat consumes
  latest-message scroll after row layout; Home renders loading/error rather
  than blank output. Kept FlatList, stable IDs, 1,020-occurrence history windows,
  source/ViewModels and local-only business boundaries. Mobile 95 PASS, focused
  7B/7C/7D 24/35/13; frozen install, Doctor 21/21, SDK/peer/TS/lint/format pass.
- Audited current server code and generated OpenAPI for the Phase 8 handoff.
  Conversation/Person/Relationship public resources, Agent history, public FIU/
  Profile DTOs and imported-data analysis remain explicit coordination gaps.
  No generated client, auth/session, REST/SSE, real import/Memory/LLM or server
  change is made. Phase 8 remains PENDING.
- User-manual Android smoke is REPORTED PASS after 7C. Codex detected an existing
  Pixel_10 AVD and briefly connected Android 17/API 37 with Expo Go 57.0.9,
  but native UI smoke could not complete after disconnect/unresponsive shell.
  Native keyboard/Back/TalkBack/automation and APK build remain NOT RUN/NOT BUILT.
  Preserve all historical 7A–7C reports; Web meets the roadmap's demo minimum.
- Complete pre-marker root verify exited 0 at 6/7C: 448 backend, 32 Phase 6
  E2E, 17 repository tests, Golden 83, migration cycle/check, frozen snapshot,
  Ruff/secret boundary, all prior gates plus actual Mobile export/browser.
  Advanced to 7/7D only after CODE/TEST/DOC/DEMO/REGRESSION; the complete
  marker-aware verifier also exited 0 with the same counts and all Phase 0–7
  gates. Results are recorded in [final acceptance](PHASE_7_FINAL_ACCEPTANCE.md). See
  [Phase 8 handoff](PHASE_8_MOBILE_INTEGRATION_HANDOFF.md). Stop after 7D.

### Phase 7C — Import, History and Settings UI

- Kept the SDK/theme/Stack/provider and added typed, injected local feature
  templates. Import has five explicit steps with preserved raw labels/Emoji,
  manual self/person/system/ignore binding, relationship confirmation and local
  compatibility/group readiness. Real picker/parser/upload/finalize/analysis
  remain disabled; result is only demo precheck completion.
- History separates Agent user/assistant from external self/person/system, scopes
  exactly to the chosen relationship, and orders historical instants with stable
  dataset/source-index/ID tie-breakers. One FlatList uses 30-row incremental
  windows; tests preserve all 1,020 occurrences per relationship and exhaust pages.
- Settings previews Phase 6 consent/pause semantics, inspect/expiry, expected
  undo and one/person/all deletion confirmation with explicit consent choice.
  Formal operations remain disabled; retention is a server-configurable policy
  with 180 days as an example. No records are actually deleted or persisted.
- Explicit scope propagates across Relationship/Import/History/Chat; unknown IDs
  fail closed, and scope changes/reset/unmount/reload clear local previews.
  No business network, private fixture, new dependency, backend/frozen knowledge
  or lockfile change. Public FIU/profile/history resources need Phase 8 coordination.
- Mobile static gates pass 82 tests, including 35 new 7C and retained 47 7A/7B
  cases. Doctor 21/21, frozen install/peer/SDK checks and Web export pass.
  Real Expo Web passes 13 scenarios (both themes, 320/360/412px), including
  reload, zero requests/errors and B-only history. Ten representative PNGs were
  visually reviewed. Android native/TalkBack NOT RUN: SDK tools exist but no
  device, AVD or installed emulator system image is available.
- Pre-marker root verify passed 448 backend tests, 13 repository tests, Golden
  83, migration cycle, frozen upstream, all previous replay/HTTP/SSE/demo gates
  and Mobile gates. It ran 81 Mobile/34 7C tests before one extra lifecycle case
  and strengthened paging/browser assertions; the later Mobile/browser gates
  passed 82/35 and 13 respectively. Marker advances only to 6/7C; final
  marker-aware verification also exited 0 with 82 Mobile/35 7C, 448 backend
  and every earlier gate. See [7C acceptance](PHASE_7C_ACCEPTANCE.md).
  Phase 7D overall acceptance and Phase 8 are not started. See
  [Import UI](MOBILE_IMPORT_UI.md), [History UI](MOBILE_HISTORY_UI.md),
  [Settings UI](MOBILE_SETTINGS_UI.md).

### Phase 7B — Chat and Relationship UI

- Completed local Chat/Profile presentation using the existing SDK/theme/Stack,
  typed injected templates and anonymous synthetic fixtures. One FlatList handles
  messages; fixed multiline composer validates/clears/appends only a local user
  bubble, with honest no-send/no-save feedback and no generated assistant.
- Seven manual run previews respect progress-then-final SSE semantics; synthetic
  FIU separates fact/provenance, inference/alternative and unknown. Safety has a
  reserved notice and pending execution remains disabled. Profile A/B selection
  replaces every field, handles missing values and passes scoped Chat navigation.
- Retained all 23 7A scenarios (local input now enabled, server send disabled),
  added 24 focused tests and integrated their explicit root gate. Real Expo Web
  passed seven scenarios, covering both themes and 320/360/412px. Twelve PNGs
  were visually inspected. Android/TalkBack NOT RUN: SDK tools exist but there
  is no connected device or configured AVD.
- Complete pre-marker `make verify` exited 0: 47 Mobile, 448 backend and 13
  repository tests, Golden 83, migrations, frozen upstream, replay, Ruff and
  all completed-phase gates. Doctor 21/21; Web export passed. Advance only to
  `completed_phase=6`, `completed_subphase=7B`; whole Phase 7 stays incomplete.
  Final marker-aware full verifier also exited 0 with the same test counts;
  its evidence is recorded in the acceptance report.
- At 7B acceptance, Phase 7C UI and Phase 8 client/API/SSE/auth remained deferred. Current public
  answer DTO does not supply structured FIU/profile resources; record that
  integration seam instead of changing the server. See [Chat UI](MOBILE_CHAT_UI.md),
  [Relationship UI](MOBILE_RELATIONSHIP_UI.md),
  [ADR 0030](adr/0030-mobile-chat-preview-and-relationship-scope.md) and
  [7B acceptance](PHASE_7B_ACCEPTANCE.md).

### Phase 7A — Expo React Native foundation and navigation shell

- Added an actual Expo SDK 57 project in the pnpm workspace, strict TypeScript,
  Expo Router Stack and reachable Home/Chat/Relationship/Import/History/Settings
  skeletons. Central theme and shared accessible components handle small screens.
- The injected local read-only DataSource and ViewModels are separate from
  screens. All pages declare Demo; state previews/retry and session-local theme
  changes work. Unimplemented business controls are disabled.
- Root verify includes frozen dependency/peer/SDK/static Mobile gates separately
  from live Expo Web smoke. All Phase 0–6 regression gates remain active.
  At 7A acceptance Android was NOT RUN. Whole Phase 7, Phase 7B feature UI and Phase 8 generated
  client/auth/API/progress streaming remain deferred.
- After CODE/TEST/DOC/DEMO/REGRESSION pass, marker advances only to
  `completed_phase=6`, `completed_subphase=7A`. The pre-marker full verify exited
  0 with 23 Mobile tests, 448 backend tests and all prior gates; live Expo Web
  smoke separately passed. Final accepted-marker full verify also exited 0.
  See [Mobile architecture](MOBILE_ARCHITECTURE.md),
  [ADR 0029](adr/0029-mobile-shell-and-data-boundary.md) and
  [Phase 7A acceptance](PHASE_7A_ACCEPTANCE.md).

Phase 6D is accepted after full verification of CODE/TEST/DOC/DEMO/REGRESSION.
Integration adds a signed HTTP Agent/Memory acceptance suite and full
real socket demo, plus a minimal owner-locked atomic expired-duplicate resave fix.
The Phase 6 final marker is updated only after all CODE/TEST/DOC/DEMO/REGRESSION
gates pass. Production scheduler, backup and restore automation remain NOT
DEPLOYED. See [Phase 6 final acceptance](PHASE_6_FINAL_ACCEPTANCE.md).

Phase 2A–2D, Phase 3A–3H and Phase 4A–4D are complete. Phase 3 is accepted
as a transport-independent Agent Runtime. Phase 4 adds the application
service, signed REST authentication, network progress streaming, disconnect
policy and PostgreSQL-backed cross-transport idempotency. Phase 5A establishes
the offline chat parser; 5B–5D complete the import pipeline. The Phase 4D
instruction names Chat Import and Relationship Data
Pipeline as Phase 5; the former Phase 5 memory-control deliverable moves to
Phase 6 in this roadmap. Neither future phase was implemented in Phase 4D.

### Phase 5A — chat import contract and parser foundation

- Added transport-free typed import source, options, message, issue and result
  contracts with parser/schema version `1` and a `ChatImportParser` protocol.
- Added a one-pass WeChat Markdown v1 parser with strict header handling,
  conservative multiline normalization, explicit IANA source timezone,
  DST anomaly errors, raw speaker inventory, provenance and stable SHA-256
  message/transcript/source fingerprints. It never binds a speaker to a user.
- Synthetic fixture, standalone summary-only dry run and 10,000-message
  generator test exercise the parser without network, Agent or database.
  Focused tests and the full Phase 0–4 gate are part of `make verify`.
  Import jobs, speaker/relationship binding, message persistence and Mobile
  remain deferred. See [Chat Import](CHAT_IMPORT.md),
  [ADR 0022](adr/0022-chat-import-parser-boundary.md) and
  [Phase 5A acceptance](PHASE_5A_ACCEPTANCE.md).

### Phase 5B — persistent import jobs and explicit binding

- Added owner-scoped PostgreSQL job and speaker inventory records, a
  transport-independent `ImportJobService`, explicit self/person/system/ignore
  binding, relationship compatibility and one-to-one readiness checks.
- Fatal parse results are rejected. Ready remains pre-import; no imported
  Conversation or Message is written. Source bytes are not stored. See
  [Import Jobs](IMPORT_JOBS.md), [ADR 0023](adr/0023-persistent-import-binding.md)
  and [Phase 5B acceptance](PHASE_5B_ACCEPTANCE.md).

### Phase 5C — imported relationship messages and idempotent merge

- Added a separate owner-scoped RelationshipMessage table and atomic
  parse/stage/validate/promote service. Agent history remains isolated.
- Added source occurrence uniqueness, exact transcript dataset dedup, durable
  Job import summary, same-Job replay, 10k PostgreSQL regression and standalone
  demo. Cross-file partial overlap dedup remains deferred. See
  [Imported Messages](IMPORTED_MESSAGES.md),
  [ADR 0024](adr/0024-relationship-message-merge.md) and
  [Phase 5C acceptance](PHASE_5C_ACCEPTANCE.md).

### Phase 5D — import API, artifact lifecycle and final acceptance

- Added a private, immutable-key artifact store with bounded multipart upload,
  owner-bound metadata, size limit, SHA-256, explicit expiry cleanup and
  single-upload Job creation. Authentication reuses the Phase 4 JWT.
- Exposed inspect, explicit speaker/relationship binding, ready, finalize,
  cancel and bounded relationship history routes. Finalize reuses 5C integrity
  and atomicity, deletes successful raw data, and replays imported receipts
  after deletion. No Agent, LLM or Memory work runs during import.
- Real Uvicorn socket demo, 10k HTTP/PostgreSQL import, concurrent finalize,
  security/lifecycle tests, migration cycle and Phase 0–5 regression pass.
  See [Import API](IMPORT_API.md), [Import Artifacts](IMPORT_ARTIFACTS.md),
  [ADR 0025](adr/0025-import-artifact-api.md) and
  [Phase 5D acceptance](PHASE_5D_ACCEPTANCE.md).

### Phase 6A — memory control service and public contracts

- Added authenticated, typed consent, pause, resume and inspect APIs over the
  Phase 3 authoritative MemoryStore; PostgreSQL serializes control changes.
- Added bounded keyset memory inspection, owner/person/relationship validation,
  signed HTTP and Agent integration tests, plus standalone and socket demos.
  Undo/deletion are covered by 6B; retention policy is 6C and mobile is Phase 7. See
  [Memory API](MEMORY_API.md), [ADR 0026](adr/0026-memory-control-plane.md)
  and [Phase 6A acceptance](PHASE_6A_ACCEPTANCE.md).

### Phase 6B — guarded undo and confirmed deletion

- Added read-only undo preview, expected-operation guarded undo and durable
  owner-bound operation-key receipts. A retry replays its original outcome and
  cannot undo the next record.
- Added server-side, five-minute confirmation challenges for delete-one,
  delete-person and delete-all. Execution rechecks the target snapshot under
  the owner lock, deletes active primary memory records, clears affected undo
  history and persists the receipt in one transaction. Delete-all requires an
  explicit choice to preserve or revoke consent.
- Signed JWT/PostgreSQL tests cover concurrency, rollback, ownership, runtime
  recall after deletion and preservation of Agent/import data. Keyless direct
  and HTTP demos are included. The public Agent Service returns a pending
  receipt for conversational undo after safety routing; the guarded API
  performs the mutation. Retention and backup policy
  remain 6C; Phase 6 final acceptance remains 6D. See
  [Memory Deletion](MEMORY_DELETION.md),
  [ADR 0027](adr/0027-guarded-memory-mutations.md) and
  [Phase 6B acceptance](PHASE_6B_ACCEPTANCE.md).

### Phase 0

- Copied 63 upstream Skill files, including 20 knowledge and 23 practical
  references, scripts, documentation and MIT license, into an immutable snapshot
  at `knowledge/goutoujunshi`. The source checkout matches the recorded commit.
- Recorded the exact source commit and SHA-256 inventory.
- Created `apps/mobile`, `apps/server`, `knowledge/goutoujunshi`, `docs`,
  `evals` and `scripts`, plus `AGENTS.md`, `.env.example`, `README.md`,
  `Makefile`, `pyproject.toml`, pnpm workspace and phase-aware verification.
- Rechecked this structure against the explicit Phase 0 acceptance list on
  2026-09-26. Simplified `ARCHITECTURE.md` to the confirmed system boundaries;
  moved the snapshot without changing source file contents. See ADR 0004.
- Acceptance: [Phase 0 report](PHASE_0_ACCEPTANCE.md).
- Commit: `eccc633` (`chore: bootstrap standalone runtime monorepo and freeze upstream`).

### Phase 1

- Completed `docs/SKILL_CONTRACT.md` with intake, evidence, scenario route,
  safety, relationship, memory, import and evaluation obligations.
- Added 55 anonymous synthetic Golden Cases across 21 categories, including
  13 high-risk cases, and a 19-reference alias map linked to the frozen source.
- Validated uniqueness, coverage, reference existence, safety precedence,
  explicit memory consent and fact/inference annotation structure.
- Acceptance: [Phase 1 report](PHASE_1_ACCEPTANCE.md).
- On 2026-09-26, completed the narrower Phase 1A behavior-contract audit
  against the frozen upstream. Expanded the contract with 18 source-backed
  scenarios, 9 fact/inference/unknown examples, all 43 reference names,
  response and memory rules, safety priority, 18 anti-patterns and explicit
  source/script ambiguities. Added three document acceptance tests. The
  existing Golden dataset was not changed or re-scored in this subphase;
  a later explicit Phase 1B instruction can rebaseline it against the
  expanded contract. See [Phase 1A report](PHASE_1A_ACCEPTANCE.md).
- On 2026-09-26, completed the requested Phase 1B Golden Dataset audit.
  Preserved all 55 original IDs, added 26 targeted synthetic cases, linked
  every case to contract rules and a behavioral rubric, and covered all 18
  scenarios plus memory. Added six linked minimal pairs, sourced FIU
  expectations, flexible 1–3-reference routing, explicit safety and memory
  decisions, a coverage matrix, and stronger static validation. No Agent or
  model behavior was run. See [Phase 1B report](PHASE_1B_ACCEPTANCE.md).

### Phase 2A

- On 2026-09-26, implemented the FastAPI backend foundation: environment-backed
  settings, `/health`, `/api/v1/status`, versioned routing, safe base error
  responses and logging, and a Uvicorn development launcher. No database or
  model connection is made at startup.
- Added root uv runtime/dev dependencies and `uv.lock`; integrated backend
  pytest and Ruff checks into the Windows `make.cmd verify` path while keeping
  `completed_phase` at 1 and marking only `completed_subphase` as `2A`.
- Ran a real Uvicorn process and requested both endpoints over localhost.
  See [Phase 2A report](PHASE_2A_ACCEPTANCE.md) and
  [ADR 0005](adr/0005-fastapi-foundation.md).

### Phase 2B

- On 2026-09-27, added the PostgreSQL persistence foundation: six UUID-based
  owner-scoped models, a lazy engine and request session dependency, a small
  repository/service layer, Alembic initial migration, database readiness and
  a Compose development service.
- The database gate creates disposable test databases, exercises Alembic CLI
  upgrade/downgrade/upgrade, then runs PostgreSQL integration tests. Agent and
  mobile gates remain deferred. See [database operations](DATABASE.md),
  [ADR 0006](adr/0006-postgresql-foundation.md) and the
  [Phase 2B acceptance report](PHASE_2B_ACCEPTANCE.md).

### Phase 2C

- On 2026-09-27, added a typed `LLMProvider` protocol, keyless queued Mock
  provider, a single OpenAI-compatible Chat Completions provider, strict
  structured-output validation, provider-level SSE streaming, and safe error
  normalization. No real model request or Agent behavior is part of this phase.
- Moved existing HTTPX to runtime dependencies in the single `uv.lock` and
  extended Settings with base URL, model and timeout. The verifier now runs an
  explicit offline LLM unit gate before all backend and PostgreSQL regression
  tests. See [LLM Provider architecture](LLM_PROVIDER.md),
  [ADR 0007](adr/0007-llm-provider-boundary.md) and the
  [Phase 2C acceptance report](PHASE_2C_ACCEPTANCE.md).

### Phase 2D

- On 2026-09-27, verified FastAPI, PostgreSQL and both LLM Provider choices in
  one backend environment. Added offline/dependency-isolated smoke tests,
  FastAPI shutdown disposal of the lazy database pool, and `alembic check` to
  the disposable migration cycle. Re-ran dependency sync, Compose startup,
  development migration, live Uvicorn HTTP checks and all prior gates.
- Completed the Phase 2 verification gate and set `completed_phase` to `2`.
  Agent and Mobile gates remain deferred. See the
  [Phase 2D acceptance report](PHASE_2D_ACCEPTANCE.md) and
  [ADR 0008](adr/0008-backend-composition-lifecycle.md).

### Phase 3A

- On 2026-09-27, defined transport-independent Agent input, total TypedDict
  state, strict structured result/failure schemas, FIU and memory candidate
  separation, status/error vocabulary, and injected runtime dependencies.
- Added an offline compatibility test for all 81 Golden cases and six minimal
  pairs. This proves schema coverage, not Agent behavior or memory writes.
- Added the future node read/write matrix and hidden-reasoning policy in
  [Agent contracts](AGENT_RUNTIME.md), with [ADR 0009](adr/0009-agent-contract-boundary.md).
  Agent execution, knowledge loading, memory persistence and mobile remain
  deferred. See [Phase 3A report](PHASE_3A_ACCEPTANCE.md).

### Phase 3B

- On 2026-09-27, added locked LangGraph 1.2.12 and a reusable standalone
  `StateGraph` with independently testable nodes, a conditional synthetic
  safety branch, scoped state updates and an injected Mock LLM path.
- Runtime results and failures share a run ID; input, provider output and
  unexpected node failures map to safe project-owned errors. A keyless CLI
  demo prints JSON without FastAPI or PostgreSQL.
- A focused offline gate verifies graph structure, both routes, node limits,
  failure paths, run isolation and a Golden pair architecture smoke. The full
  81-case behavior eval remains deferred. See [Phase 3B report](PHASE_3B_ACCEPTANCE.md)
  and [ADR 0010](adr/0010-minimal-langgraph-runtime.md).

### Phase 3C

- On 2026-09-27, replaced synthetic safety routing, the constant scenario and
  minimal analysis with separate provider-backed `SafetyResult`,
  `ScenarioResult` and `FactExtractionResult` nodes. High risk exits before
  ordinary classification; explicit refusal has a distinct boundary route.
- Added short source-backed system prompts, speaker-labeled JSON context,
  structured-output failure handling and a 24-case Golden subset including all
  six minimal pairs. A deterministic evaluator checks structured fields and
  catches promoted inferences; oracle-derived Mock replay is not live accuracy.
- Updated the verifier with focused offline semantic tests. No live semantic
  model validation was run. See [Phase 3C report](PHASE_3C_ACCEPTANCE.md) and
  [ADR 0011](adr/0011-semantic-entry-nodes.md).

### Phase 3D

- On 2026-09-27, added deterministic Knowledge Router and independent Reference
  Loader nodes to ordinary, boundary and high-risk graph paths. The safety
  branch still skips scenario/FIU but now loads its safety reference first.
- An app-owned registry validates `reference_map.json` aliases against the
  frozen manifest and canonical paths. The loader verifies selected file
  hashes, returns typed excerpts under explicit document/total budgets and
  converts failures to a safe Agent error. The public result exposes aliases
  only. No RAG or relationship advice was added.
- The verifier runs all 81 Golden routing constraints with expected semantic
  labels as fixtures, plus runtime integration and loader security tests.
  This is a deterministic router evaluation, not a live model evaluation.
  See [Phase 3D report](PHASE_3D_ACCEPTANCE.md),
  [Knowledge routing](KNOWLEDGE_ROUTING.md) and
  [ADR 0012](adr/0012-deterministic-knowledge-loading.md).

### Phase 3E

- On 2026-09-27, added a provider-backed `relationship_analysis` node after
  knowledge loading on ordinary/boundary paths. High risk still bypasses it.
  The node consumes typed FIU and the actual loaded excerpts, and writes only
  structured `AnalysisResult` with evidence/reference provenance.
- Extended analysis points with observed/tentative/framework/uncertainty roles,
  relevant dimensions and source IDs. The runtime rejects invalid IDs,
  inference-to-fact promotion, missing boundary recognition and obvious action
  or unsupported certainty language. This does not prove semantic entailment.
- Added a 30-case Golden Mock replay and structural evaluator plus direct
  reference-content, truncation, injection and failure tests. Live-model
  relationship analysis was not run. See [Phase 3E report](PHASE_3E_ACCEPTANCE.md),
  [Relationship analysis](RELATIONSHIP_ANALYSIS.md) and
  [ADR 0013](adr/0013-grounded-analysis-contract.md).

### Phase 3F

- On 2026-09-27, replaced the ordinary-path placeholder with independent
  `action_planner` and `response_generator` nodes. Each uses typed
  `LLMProvider.structured_output` and writes only its declared state field;
  high-risk input still bypasses both nodes.
- Extended `ActionPlan` with a contact policy and analysis-point provenance,
  added `ResponseResult`, bounded prompts and project-owned validation for
  refusal, manipulation, unsupported certainty, internal IDs and plan/answer
  consistency. No memory persistence or transport was added.
- Added a 38-case Golden Mock replay, focused mutation tests, a keyless
  standalone demo and an active verifier gate. This validates wiring and
  structural rules, not live-model advice quality. See
  [Phase 3F report](PHASE_3F_ACCEPTANCE.md), [Action and response](ACTION_RESPONSE.md)
  and [ADR 0014](adr/0014-action-response-boundary.md).

### Phase 3G

- On 2026-09-27, added a post-response memory intent, bounded structured
  candidate extraction, fact/source/consent validation and separate persistence
  node. Early memory loading provides historical context to analysis without
  changing current FIU; high-risk runs skip memory writes.
- Added per-user opt-in and pause state, scoped inspect/deletion operations,
  in-memory and SQLAlchemy stores, a two-table Alembic migration, duplicate
  prevention and nonblocking memory failure receipts. A narrow user/object/
  relationship fact subset is persisted; event/hypothesis remain deferred.
- The verifier runs focused memory tests, real PostgreSQL persistence and
  migration checks, a 14-case Golden Mock replay, all prior gates and a
  standalone two-run demo. The Phase 3F stop-condition validator was corrected
  for simple reply/invitation and its 38-case replay rerun. See
  [Phase 3G report](PHASE_3G_ACCEPTANCE.md), [Memory](MEMORY.md) and
  [ADR 0015](adr/0015-consent-gated-memory.md).

### Phase 3H and Phase 3 final acceptance

- On 2026-09-27, closed the Phase 1A memory undo MUST gap with a bounded
  20-operation, owner-scoped undo history for newly saved records. Alembic
  revision `20260927_03` adds `memory_operations`; undo works across sessions,
  while hard deletion clears affected operation history.
- Added transport-independent `AgentRuntime.stream()` over the same compiled
  LangGraph as `run()`. Typed, JSON-restorable events provide stable progress,
  a validated full final answer, memory receipt and terminal result/failure.
  Token-level model generation remains deferred. Cancellation closes the
  underlying graph iterator; high-risk runs never publish ordinary planning
  or composing statuses.
- Eight standalone full-pipeline E2E cases cover ordinary reply, explicit
  refusal, high risk, cross-conversation memory, absent consent, memory failure,
  person isolation and run/stream parity. The verifier also runs focused
  streaming tests and all earlier gates. Phase 3 is complete as an engineering
  runtime gate; live-model end-to-end quality remains unverified. See
  [Phase 3H report](PHASE_3H_ACCEPTANCE.md),
  [Streaming runtime](STREAMING_RUNTIME.md), [ADR 0016](adr/0016-memory-undo.md)
  and [ADR 0017](adr/0017-runtime-streaming.md).

### Phase 4A — Agent application service

- `AgentService.execute` binds a verified actor to an existing owned conversation,
  stores the user message and running run in a short transaction, then calls the
  standalone runtime without a database transaction. A second transaction stores
  the validated answer and completion, or a failure state. Runtime and database
  run IDs are identical. The owner-scoped history contains at most 20 prior
  user/assistant messages.
- A failed runtime preserves user input but writes no assistant answer. If the
  answer commit fails, the service rolls it back and attempts a separate failed
  run update; it reports recovery status either way. Memory failure remains a
  completed response with a warning. See [Agent Service](AGENT_SERVICE.md),
  [ADR 0018](adr/0018-agent-service-orchestration.md) and
  [Phase 4A acceptance](PHASE_4A_ACCEPTANCE.md).

### Phase 4B — REST API and authentication boundary

- Added signed HS256 Bearer JWT verification with required UUID subject,
  expiration, issuer and audience. The verifier issues a typed identity before
  the transport constructs an `AuthenticatedActor`; the service checks the User
  still exists and continues to own conversation authorization.
- Added a synchronous typed Agent run endpoint, uniform public errors, OpenAPI
  Bearer scheme and app-scoped lazy runtime composition. Health endpoints remain
  public. A development-only CLI can create local test identities and sign
  short-lived tokens; no production token issuance route exists.
- Offline authentication and REST contract tests, real PostgreSQL API
  integration and a signed-token Uvicorn socket demo pass. See
  [Phase 4B acceptance](PHASE_4B_ACCEPTANCE.md),
  [Authentication](AUTHENTICATION.md), [Agent REST API](AGENT_API.md) and
  [ADR 0019](adr/0019-rest-authentication-boundary.md).

### Phase 4C — streaming transport and disconnect policy

- Added a POST SSE endpoint with a versioned, narrow event envelope. It reuses
  4B JWT authentication and awaits `AgentService.stream()` ownership/preflight
  before HTTP headers. The service shares transaction and recovery helpers
  with `execute()`, consumes one runtime stream, and commits the assistant and
  completed run before sending the final response frame.
- Defined precommit disconnect as runtime cancellation plus failed run with
  `client_disconnected`; postcommit disconnect preserves the completed run and
  cancels unfinished optional memory work. PostgreSQL advisory transaction
  locking and an active-run query reject a second run on the same Conversation
  with 409 across service instances.
- Real PostgreSQL signed-JWT integration, socket-level cancellation tests and
  a frame-by-frame Uvicorn demo verify terminal DB state and event order. See
  [Streaming API](STREAMING_API.md), [ADR 0020](adr/0020-streaming-transport-disconnect.md)
  and [Phase 4C acceptance](PHASE_4C_ACCEPTANCE.md).

### Phase 4D — persistent idempotency and Phase 4 acceptance

- Added an owner/Conversation-scoped operation key and SHA-256 fingerprint to
  AgentRun, with PostgreSQL uniqueness and an advisory-lock first-writer
  transaction. Repeated matching requests never create another user Message,
  AgentRun, assistant Message or Runtime/Memory execution.
- Completed operations replay across synchronous REST and POST SSE from the
  persistent assistant Message and bounded result summary. Running, failed,
  conflicting and unresolved operations fail closed with stable pre-stream
  HTTP errors. A new user attempt requires a new key.
- Signed API E2E, an eight-request PostgreSQL race, real socket disconnect
  retries, migration cycle and a local Uvicorn sync/stream replay demo pass.
  Phase 4 is complete as an engineering API gate. This does not include Mobile,
  Chat Import, OAuth, RAG, token-level model streaming or production
  reconciliation. See [Idempotency](IDEMPOTENCY.md),
  [ADR 0021](adr/0021-persistent-operation-idempotency.md) and
  [Phase 4D acceptance](PHASE_4D_ACCEPTANCE.md).

## Dependency policy

Official documentation was checked before selecting the layout: uv's project
and lockfile guidance, FastAPI's request-model tutorial, SQLAlchemy's ORM
documentation, and Expo's SDK compatibility table. Exact application library
versions are chosen at their implementation phase and locked in `uv.lock` or
`pnpm-lock.yaml`; no pre-release versions by default. Phase 2A introduced the
first Python runtime dependencies, selected against official release records
and verified with the lockfile.

### Phase 6C — retention, expiry and backup/deletion policy

- Fixed configurable finite memory expiry; migration-time legacy grace; query-time
  exclusion, user-visible expiration/state/summary and unavailable expired undo.
- Bounded deterministic maintenance with owner-lock serialization, cascade-safe undo
  history cleanup and challenge expiry+grace. Receipts remain durable to preserve
  persistent destructive-operation retries after challenge removal.
- Authoritative inventory and backup/restore design, true primary deletion boundaries,
  real PostgreSQL/MockLLM demo, failure/race tests and prior-phase regression.
  Production scheduling and backup automation are NOT DEPLOYED. See
  [retention policy](MEMORY_RETENTION.md), [backup policy](MEMORY_BACKUP_DELETION_POLICY.md),
  [ADR 0028](adr/0028-memory-retention-lifecycle.md) and [acceptance](PHASE_6C_ACCEPTANCE.md).
  At 6C acceptance, 6D final acceptance and Phase 7 Mobile were pending.

### Phase 6D — integrated controls and Phase 6 final acceptance

- Actual signed JWT HTTP, AgentService/LangGraph/MockLLM and PostgreSQL E2E
  cover consent, inspection, pause/revoke/resume and in-flight control changes;
  guarded undo, confirmation safety, durable retries and ownership isolation;
  REST/SSE failure/pending/safety behavior and Phase 5 import separation.
- Expired same-content resaves atomically replace only the expired collision,
  creating a new ID, dates and undo operation after durable control checks.
  Active duplicates, owner locking, rollback and concurrency invariants remain.
- Full real socket demo and phase-aware verification include 32 new E2E tests,
  448 full backend tests, 83 Golden annotations and all prior regression gates.
- Phase 6 is PASS; marker is `6 / 6D`. Production scheduler, encrypted backup
  rotation and restore replay remain NOT DEPLOYED. Phase 7 is PENDING.
  See [Phase 6 final acceptance](PHASE_6_FINAL_ACCEPTANCE.md).
