# Phase 8A acceptance — 2026-10-09 (Asia/Shanghai)

PHASE: Phase 8A — Public Resource APIs and Mobile Integration Contract Foundation

STATUS: PASS — CODE, TEST, DOC, DEMO and REGRESSION passed before marker
advancement. Both required complete root verifiers exited0, including the final
accepted-marker run at7/8A. Whole Phase8 remains PENDING.

ROADMAP PREFLIGHT: HEAD `ccabc98`, clean worktree, marker `7 / 7D`. Phase 7 PASS;
Phase 8 PENDING. Read AGENTS, MASTER_PLAN, ARCHITECTURE, Phase 7 final acceptance,
Phase 8 handoff, DATABASE, AUTHENTICATION, AGENT_SERVICE, AGENT_API,
STREAMING_API, IMPORTED_MESSAGES, IMPORT_API, MEMORY_API and IDEMPOTENCY before
code edits. Audited actual models/repositories/migrations/services/auth/routers,
pre-edit OpenAPI and verifier/tests. The actual inventory is the handoff's 26
operations; the four reported resource/history gaps are real. No roadmap conflict
or existing uncommitted user work. Invocation-local safe.directory preserves global
Git settings. No subagent, live model or new dependency used.

EXISTING RESOURCE AUDIT: Person: owner/display_name/UUID/times. Relationship:
owner/Person/required type/status/UUID/times. Conversation: owner/nullable
Relationship/UUID/times, without Person/title/status. Message: Conversation,
user/assistant/tool, content/speaker/UUID/times. Existing PK/composite FKs and
15 tables remain. Internal unbounded lists and latest-20 Agent input are not
used as public list endpoints. No migration or duplicate storage added.

PERSON API: Create/list/detail over existing rows; explicit bounded name, real
UUID v4 reservation; projected ID/name/times only.

RELATIONSHIP API: Create/list/detail; validate owned Person, preserve required
explicit labels including unknown, infer no romance or identity.

CONVERSATION API: Create/list/detail; optional owned Relationship or generic
Conversation. Immediately works with existing AgentService; expected scope
remains its final authority.

AGENT HISTORY API: Owned Conversation Message pages, user/assistant only,
ascending timestamp/UUID order, actual persisted IDs/content/times. No tool,
speaker metadata, imported chat, Memory evidence or internal Agent state.

AUTHENTICATION / OWNERSHIP: Production Bearer verifier and existing-user checks;
no auth override. Missing/foreign resources and invalid binding targets share
generic 404. No client owner fields accepted. Invalid JWT returns 401.

RESOURCE CREATION IDEMPOTENCY: Required stable UUID v4 per logical operation.
Matching canonical fields replay the same row/201/timestamps across app restart;
changed fields return 409. PostgreSQL transaction locks plus existing PKs arbitrate
races; foreign reserved IDs return generic 404. Reservation lasts with the row,
not past internal/future deletion. No AgentRun or receipt table misuse.

PAGINATION: Four lists default 30/max100, opaque bounded cursor, items/next_cursor,
ascending time/UUID keys and limit+1 queries. Equal-time 61-row cases exhaust
without loss/duplication. Owner/domain/parent mismatches fail 422. Per-request
committed live reads; no fixed multi-request snapshot is promised. See RESOURCE_API.

DATA DOMAIN ISOLATION: Real HTTP import/finalize still writes only separate
RelationshipMessages and its receipt. New Agent history is empty until an Agent
run. Import rows do not enter Agent context or public Agent roles.

PUBLIC DTO: Named extra-forbid projections, required UUID creation IDs, typed
nullable association/cursors and bounded page arrays, without invented profiles
or internal ORM fields. Resource strings canonicalized NFC/trim; controls,
blank/invalid Unicode, unsupported owner/operation fields rejected.

OPENAPI CONTRACT: 36 operations: 26 unchanged + ten additions. Deterministic
offline canonical export and committed generation input; baseline hashes freeze
all old operations/schemas/security. Drift/privacy/unbounded-page mutations are
rejected by tests. No TypeScript client generated.

DEV AUTH BOUNDARY: Existing development-only bootstrap/token CLI, 15-minute
existing-user HS256 JWT, private server config. Future 8B accepts manually supplied
development credentials; no signer/login endpoint/SecureStore added. Production
account acquisition remains absent.

TRANSACTION / CONCURRENCY: Eight duplicate requests for each resource yield one
committed row. Two different payloads yield one 201/one409; two owners racing one
UUID yield one201/one404. Fail-after-flush and commit failure rollback for all
three resources, followed by successful same-ID retry. Concurrent history hides
uncommitted rows and continues after append. No runtime transaction held by resource calls.

SIGNED JWT INTEGRATION: All ten routes tested with signed existing users, missing
credentials and signed unknown subjects; wrong claims rejected without creation.
Only MockLLM injected for actual Agent persistence, never authentication.

POSTGRESQL INTEGRATION: Disposable migrated real PostgreSQL test databases; no
SQLite, development DB fallback or create_all deployment. Existing local PostgreSQL
16.15 on 15434 is reachable; repository Compose PostgreSQL18.6 configuration is
unchanged. Docker availability does not substitute for the actual test result.

HTTP / UVICORN DEMO: PASS, real socket test and standalone root demo. Output:
three response-loss retries, three owner-neutral resource denials, exactly one
owned Person/Relationship/Conversation, completed Agent, actual user/assistant
history and repeat pages without loss. Only MockLLM replaced; real authentication.

MOBILE HANDOFF UPDATE: New resource/history DTOs, retry policy, exact generation
input and development identity contract documented. API availability is separate
from Mobile integration. All Mobile source, fixtures, package and lock remain unchanged.

IMPORT-TO-ANALYSIS GAP STATUS: Still absent. Finalize persists external history;
AgentService does not consume it. No automatic analysis/FIU/Profile transport;
future analysis needs owned source selection, explicit authorization and provenance.

TESTS: 97 focused cases PASS (90 signed JWT/PostgreSQL/service/socket cases and
seven offline schema cases). Retained 448 backend cases; full backend545 PASS.
Repository21 PASS, including four new marker boundaries and all old tests.

VALIDATION COMMANDS: See RESOURCE_API.md; full pre/post-marker .\make.cmd verify
and git diff --check required. Initial sandbox pytest encountered Windows temp
directory access denial; normal approved execution reran all tests successfully.
The denied attempt is not a pass.

FULL BACKEND REGRESSION: PASS in both complete root runs: 545 backend,
32 Phase6 E2E, 83 Golden annotations, all earlier Agent/REST/SSE/import/Memory
tests and demos, Alembic upgrade/downgrade/upgrade/check, frozen knowledge,
secret boundary and Ruff (167 formatted files). No skipped substitute.

MOBILE REGRESSION: PASS in both complete root runs: 95 tests, focused
7B/7C/7D24/35/13, frozen offline install, pnpm11.25.0, SDK compatibility, strict
TS, lint/format, peer audit, actual Web export and all22 Chrome scenarios.
No Mobile source/dependency/lock change; no new native validation claimed.

ROOT VERIFY: Pre-marker full .\make.cmd verify PASS, exit0 at 7/7D, evidence
`.cache/phase8a-verify-pre-marker.log`. Accepted-marker full run at7/8A PASS,
exit0, evidence `.cache/phase8a-verify-final.log`. All0–7 gates preserved and 8A
explicitly runs offline export, focused signed resource suite and real socket demo.
Future completed_phase8 or subphase8B/8C cannot be claimed by this verifier.

ARCHITECTURE DECISIONS: ADR0031: existing primary-key reservations, independent
ResourceService, narrow projections, bounded live keysets and audited generation input.
No new tables, dependency, infrastructure, graph or Memory/Import/SSE rewrite.

FILES CHANGED: Resource API/service/schema/query files; additive repository UUID
parameters; typed error mapping/router assembly; synthetic support/demo/tests;
deterministic exporter/snapshots; root gates/marker tests; resource contract,
ADR0031, architecture/API/database/auth/idempotency links, handoff, plan/README,
this report and final marker. A scoped .gitattributes rule fixes contract JSON
to LF so byte-checked generation inputs survive Windows checkout conversion.
Historical 7A–7D reports remain unchanged.

KNOWN ISSUES: Multi-page reads are live rather than a fixed snapshot; refresh
after late commits/backfills/deletions. Retry reservation is row lifetime.
Production authentication and native smoke gaps remain those of prior acceptance.

DEFERRED: 8B generated TypeScript client/auth session/owned-resource Mobile adapter;
8C SSE/import/Memory network work; production accounts, imported-data analysis,
public FIU/Profile, RAG, release and prior scheduler/backup gaps.

PROJECT PHASE MARKER: After all pre-marker CODE/TEST/DOC/DEMO/REGRESSION gates:
`completed_phase=7`, `completed_subphase=8A`. Phase8 remains PENDING. Required
accepted-marker full rerun PASS, exit0; no 8B/8C implementation begun.

NEXT: Phase 8B — Generated TypeScript API Client, Auth Session and Owned Resource Integration.
Stop after 8A. Do not begin 8B or 8C.

## Exact validation commands and evidence

Executed from the repository root, with the existing local PostgreSQL16.15
cluster; the harness creates/drops separate randomized migrated databases.
No real model or production credentials are used. Local socket/demo output
contains counts/status/roles only; raw logs are ignored.

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONUNBUFFERED='1'
$env:TEST_DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:15434/goutou_test'
$env:DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:15434/goutou_dev'
$env:PLAYWRIGHT_CHROME_PATH='C:\Program Files\Google\Chrome\Application\chrome.exe'
$env:PATH='C:\Windows\System32;'+$env:PATH
uv --cache-dir .cache/uv --no-managed-python run --locked python scripts/export_openapi.py --write
uv --cache-dir .cache/uv --no-managed-python run --locked pytest -q apps/server/tests/test_resource_api.py apps/server/tests/test_resource_contract.py --basetemp=.cache/phase8a-focused-final -o cache_dir=.cache/phase8a-focused-cache
uv --cache-dir .cache/uv --no-managed-python run --locked ruff check apps/server scripts/export_openapi.py scripts/verify.py
$env:PYTEST_ADDOPTS='--basetemp=.cache/phase8a-pytest-pre-marker -o cache_dir=.cache/phase8a-pytest-cache'
.\make.cmd verify  # 7/7D, exit0
# Only after CODE/TEST/DOC/DEMO/REGRESSION: update marker to 7/8A.
$env:PYTEST_ADDOPTS='--basetemp=.cache/phase8a-pytest-final -o cache_dir=.cache/phase8a-pytest-final-cache'
.\make.cmd verify  # 7/8A, exit0
git -c safe.directory=F:/狗头军师app化/goutouapp diff --check
git -c safe.directory=F:/狗头军师app化/goutouapp diff --cached --check
git -c safe.directory=F:/狗头军师app化/goutouapp ls-files --eol -- docs/contracts/openapi.json docs/contracts/phase7d-openapi-baseline.json
```

Both complete root logs include these results:

```text
Ran 21 tests ... OK
PASS: isolated Alembic upgrade head / downgrade base / upgrade head / check
32 passed (Phase6 E2E)
PASS: deterministic OpenAPI, 36 operations, all 26 Phase 7D contracts preserved
97 passed (Phase8A focused)
545 passed (full backend, retained448 + new97)
Golden annotation validation passed: cases83
Repository secret boundary check passed
All checks passed! / 167 files already formatted
Tests: 95 passed; focused24/35/13
No peer dependency issues found
Exported: dist
22 passed (actual Chrome/Expo Web, no skipped/flaky substitute)
PASS: all active Phase 0..7 and Phase 8A; Phase 8 PENDING
```

Ignored evidence: `.cache/phase8a-before-openapi.json`,
`phase8a-focused-tests.log`, `phase8a-verify-pre-marker.log`, `phase8a-verify-final.log`,
existing `.cache/phase7d-web-smoke.json` and Web screenshots/results. The real
socket demo is run by both the focused test and each root verifier. JSON outputs
confirm one owned resource each, three response-loss retries, three owner-neutral
denials, Agent completed and repeated persisted user/assistant pages without loss.
Both contract JSONs have `i/lf w/lf attr/text eol=lf`. Working/staged diff checks
pass. Mobile, knowledge, evals and both lockfiles have zero staged changes.

## Changed files

- Transport: `apps/server/app/api/v1/resources.py`, `api/v1/router.py`, `api/errors.py`.
- Persistence/contracts: `apps/server/app/db/repositories/resources.py`,
  `db/repositories/records.py`, `schemas/resources.py`, `services/resources.py`.
- Real test/demo: `apps/server/resource_api_demo.py`, `resource_demo_support.py`,
  `tests/test_resource_api.py`, `tests/test_resource_contract.py`.
- Verification/input: `scripts/export_openapi.py`, `scripts/verify.py`,
  `tests/test_mobile_phase_gate.py`, `.gitattributes`, `project-phase.json`,
  `docs/contracts/openapi.json`, `docs/contracts/phase7d-openapi-baseline.json`.
- Documentation: `README.md`, `docs/RESOURCE_API.md`, `PHASE_8A_ACCEPTANCE.md`,
  `PHASE_8_MOBILE_INTEGRATION_HANDOFF.md`, `MASTER_PLAN.md`, `ARCHITECTURE.md`,
  `DATABASE.md`, `AUTHENTICATION.md`, `AGENT_API.md`, `IDEMPOTENCY.md`,
  `adr/0031-public-resource-acquisition-and-retries.md`.

Stage commit scope:29 files, Phase8A only. No generated client, Mobile business
request, production auth route, new migration/table/dependency or Agent behavior.
