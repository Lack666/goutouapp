# Phase 9A acceptance

PHASE: Phase 9A — Security Threat Modeling and Upload Boundary Hardening.

STATUS: PASS. CODE, TEST, DOC, DEMO and REGRESSION all passed. Independent
pre-marker and post-marker complete root runs each exited0. Phase9 overall
remains IN PROGRESS; this acceptance completes9A only, within development scope.

ROADMAP PREFLIGHT: clean worktree/index at `08563c3`, branch initially
`codex/phase8f-final-acceptance`, single worktree. New branch
`codex/phase9a-upload-security`. Marker initially8/8F. Read AGENTS, MASTER_PLAN,
ARCHITECTURE, SKILL_CONTRACT and all requested API/lifecycle/retention/8F reports.
Existing evidence gate rechecks native hashes and independent pre-marker exit.
8F pre-marker-r4 and post-marker committed exit files both contain0. Handoff's
old Phase8-incomplete introduction is superseded by the committed final addendum.
No formal 9A–9E subdivision existed; only9A is added, without prescribing later labels.

PHASE 8 FINAL BASELINE: committed baseline Backend558, Mobile355, Repository47,
Golden83, Demo Web22, Connected Web3/3/4/5/1, OpenAPI36, Expo Doctor21/21.
These remain minimum prior coverage, not inferred present results. Existing import
baseline independently rerun:10 passed. Initial unconfigured local DB attempt
failed/was interrupted; not counted as PASS. Existing loopback PostgreSQL16.15
test instance was started and TEST_DATABASE_URL explicitly selected for isolated DBs.
No development/user database was used as a test fallback. Compose PostgreSQL18.6
was not available in the sandbox; no Python dependency or migration was introduced.
Official Expo compatibility patch updates and exact pnpm release-age exceptions
are documented in PHASE_9A_DEPENDENCY_AUDIT; historical native evidence remains
for its recorded build, not a new native build of the patched dependency graph.

THREAT MODEL: SECURITY_THREAT_MODEL covers STRIDE threats with assets, inputs,
identity source, attacks, controls, severity, test coverage and remaining risk.

TRUST BOUNDARIES: B1 App/transport; B2 authentication; B3 services/owner scope;
B4 DB; B5 artifacts; B6 Agent/provider; B7 logs/evidence; B8 retention/backups;
B9 concurrency/resources. Trusted host/OS-root access remains an explicit assumption.

UPLOAD SIZE / TYPE: actual received body and exact file limits; strict existing
UTF-8 WeChat Markdown V1 content parsing. MIME/filename never determine validity.
Default100MiB file +1MiB body overhead. Empty400, oversized413, unsupported415,
fatal parse422; oversized multipart header400. No format expansion.

PATH TRAVERSAL: synthetic slash/backslash/absolute/device/ADS/Unicode/long/empty
filenames; random isolated artifact names, invalid internal keys, same-name distinct
Jobs and atomic collision-preserving publication. Initial sandbox run skipped
actual Windows symlink creation; approved host execution then passed the isolated
real-file symlink-refusal test. Optional no-follow is preserved; hostile root
replacement still requires OS ACLs.

PARSER NEGATIVE TESTS: invalid UTF-8, NUL, extreme UTC conversion, invalid/unsupported
dates, oversized line/speaker, many blanks/issues, repeated time/body, emoji/ZWJ/bidi,
partial damage, group/unbound readiness and instruction text as data. Linear trim
and safe fatal/issue behavior; no hidden reasoning or Golden changes.

ARTIFACT LIFECYCLE: registration failures roll back/delete; ready source tamper
fails; merge DB failure retains source and zero formal rows; imported replay returns
durable receipt after raw deletion; cancel/expiry cleanup and cleanup faults retry
with generic warnings. Maintenance is explicit; production scheduler NOT DEPLOYED.

OWNER / SCOPE ISOLATION: signed independent A/B; inspect/speaker/relationship/ready/
finalize/cancel and imported-history denial; owned B Job cannot bind A resources;
missing/foreign responses identical. Source text cannot supply authenticated owner.

BINDING / FINALIZE AUTHORIZATION: explicit self/person inventory binding, revision
conflicts, readiness and rechecked row-lock state; duplicate dataset semantics preserved.

LOG REDACTION: app fixed messages; Uvicorn exception filter; disabled access logger;
native subprocess timeout/nonzero/OS failure suppression; Mobile error allowlists
and no console logging verified through retained Mobile gates and added sentinel test.

EVIDENCE PRIVACY AUDIT: read-only131 files, inventory SHA-256
`159f8343692c0c78f23ca164fc4444026edd41dd102ba8ff9042db0a10ac8c83`.
No JWT/provider-key/credential-bearing DB URL/Bearer value pattern findings.
Scripts/matrix identify synthetic fixture provenance; UI contains synthetic text,
and test Memory setup uses anonymous fixtures. General private prose cannot be
excluded by regex alone. No historical evidence file was rewritten or removed;
no confirmed real credential leak requiring repository-history cleanup was found.
The10 new9A execution logs also have zero credential-pattern findings; successful
logs and exit files are byte-pinned in PHASE_9A_MATRIX.json.

ERROR CONTRACT: stable existing codes, generic private failures; unexpected error
still500. Uploaded metadata DB failure503 import_failed; no fake success. Real socket
SQL and unexpected exception sentinels absent from responses and captured server logs.

RESOURCE EXHAUSTION: real exact-default100MiB chunked upload/cancel records traced
Python peak/time; approved final focused measurement2155660 bytes/1.114s for
104857600 file bytes, zero artifacts after cancel. Not RSS, native memory, DB memory or worst-case
unique-speaker inventory. Conservative transient spool+artifact disk bound201MiB
per request; handles close on real interrupted TCP and excessive-body parsing.
Aggregate rate/quota/concurrency/active-body timeout absent; R-07 is a production
deployment prerequisite. No DDoS protection claim.

CONCURRENCY: four concurrent signed A/A/B/B uploads, original repeated-finalize gate,
cancel/finalize simultaneous start and locked terminal states. DB failure rollback,
same-owner exact-dataset merge and legitimate repeated occurrences retained.

REAL JWT / POSTGRESQL E2E: no authentication dependency override. Real signatures,
FastAPI/Import/SQLAlchemy/migrated disposable PostgreSQL/private artifacts used;
actual loopback TCP covers upload/auth/format/size/filename/binding/finalize/replay/
cancel/disconnect, plus separate actual socket DB/unexpected failure and100MiB demo.
In-process signed A/B matrix adds all object authorization cases and controlled races.

P0 / P1 FINDINGS: R-01 log exception disclosure; R-02 NUL/UTC boundary; R-03 cleanup
failure handling; R-04 atomic publication race. No remote authentication/path/owner
bypass found in tested paths. Severity conditions and limits are in the risk register.

P0 / P1 FIXES: fixed minimal parser/logging/storage/cleanup defects with linked
negative tests. R-05 bounded quadratic trimming also fixed. No open confirmed blocker.

REMAINING RISKS: R-06 retention/backup deployment; R-07 aggregate admission/storage/
slow-client bounds; R-08 future analysis/provider injection; R-09 production identity,
broader deletion/logging and reconciliation. All remain explicitly deferred with
responsible subsequent tasks. Untrusted production exposure would elevate R-07 toP1.

SECURITY DOCUMENTATION: threat model, upload boundary, Markdown+JSON risk register,
ADR0036, handoff, architecture and roadmap updated. Risk references validated in root.

BACKEND TESTS: final approved focused upload/parser/job/merge88 passed, no skips;
45 new security cases. Full Backend603 passed independently in pre-marker-r6
and post-marker. Earlier
sandbox focused87 passed/1 skipped and preliminary86/1 are retained separately.

MOBILE TESTS:358 full tests passed in both complete root runs, including3 new private upload
error tests. TypeScript/lint/format, Expo compatibility and Doctor21/21 passed.

REGRESSION: pre-marker-r6 and independent post-marker both passed full0–8,
repository55, Golden83, Web22,
Connected Web3/3/4/5/1, migration/check/cycle, OpenAPI36, generated client,
frozen upstream, secret boundaries and all native evidence hash/scene gates.

PRE-MARKER VERIFY: first sandbox attempt1 failed at Expo compatibility network
EACCES after Backend602/1skip and repository55. Its log/exit are retained as
pre-marker-attempt1. Approved attempts pre-marker-approved and pre-marker-final
failed on official dependency recommendations after Backend603 and repository55.
pre-marker-r4 passed compatibility but failed on the new Mobile test callback's
TypeScript contract, fixed by matching the existing asynchronous test harness.
Typecheck/lint/format and full358 Mobile preflight tests then passed.
pre-marker-r5 passed Backend603, Mobile358 and Doctor21/21, then failed all22
browser launches because default managed Chromium was absent. Missing System32
inherited PATH also stalled Playwright's Metro cleanup. Only this run's verified
owned Metro tree was stopped to release cleanup and preserve the real exit1.
Reruns use the installed Chrome and System32 settings already documented by8F;
no browser config/test or root gate is weakened. Independent pre-marker-r6 ran
the complete `.\make.cmd verify` under8/8F and passed every gate.

PRE-MARKER EXIT CODE:0 (`docs/evidence/phase9a/pre-marker-r6.exit`).

POST-MARKER VERIFY: independent complete `.\make.cmd verify` under8/9A,
distinct test/cache directories and `docs/evidence/phase9a/post-marker.log`.
All original gates and added security gates passed; no skip in final Backend603
or focused88. PHASE_9A_MATRIX.json pins all successful log/exit hashes.

POST-MARKER EXIT CODE:0 (`docs/evidence/phase9a/post-marker.exit`).

FILES CHANGED: narrow parser/artifact/workflow/server-log/native-helper changes;
security tests/tooling/documents and phase verifier; no Mobile implementation,
Python dependencies, migrations, knowledge or eval data changes. Existing Expo
dependencies receive four direct compatibility patches, a UI peer patch, exact
release-age exclusions and a lockfile update (see dependency audit).

PROJECT PHASE MARKER: advanced after all five pre-marker gates to8/9A;
Phase9 overall remains IN PROGRESS. Independent post-marker verification passed.

NEXT: subsequent Phase9 security/privacy/deletion/reliability tasks per MASTER_PLAN
and handoff. Stop after9A; no Phase10/11/12, imported analysis or real LLM work.

Five-gate acceptance: CODE — minimal fixes in existing boundaries; TEST — signed
negative/fault/race/size tests and safe Mobile errors; DOC — threat model, boundary,
register, ADR and handoff; DEMO — real TCP signed PostgreSQL import/cancel and exact
100MiB resource measurement; REGRESSION — two independent complete root exit0
runs preserving all previously completed phase gates.

## Reproduction and evidence

Commands run from repository root in PowerShell. Local PostgreSQL must be
available; the configured disposable test database prefix is never a development
database fallback. On this host the explicit test settings were:

```powershell
$env:TEST_DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:15434/goutou_test'
$env:PYTHONUTF8='1'
$env:PLAYWRIGHT_CHROME_PATH='C:\Program Files\Google\Chrome\Application\chrome.exe'
$env:PATH='C:\Windows\System32;'+$env:PATH
uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env pytest -q -s apps/server/tests/test_upload_security.py apps/server/tests/test_chat_import.py apps/server/tests/test_import_jobs.py apps/server/tests/test_import_merge.py
.\make.cmd verify
```

Each complete root run uses a distinct PYTEST_ADDOPTS basetemp/cache under
`.cache/phase9a-*`, redirects stdout+stderr to its own `docs/evidence/phase9a/*.log`,
and immediately saves `$LASTEXITCODE` to the corresponding `.exit` file. Root
pre/post runs are independent. Focused `-s` output preserves the count-only real
100MiB measurement. The matrix pins successful original evidence bytes by SHA256;
`.gitattributes` prevents newline conversion of new evidence. Historical8F
artifacts retain their existing attributes and hashes.

Windows file-symlink creation required approved host execution; sandbox-only skips
are recorded and excluded from the final no-skip acceptance. Restricted network
failure and obsolete Expo recommendations are failures, not alternative PASS
paths. Current compatibility, frozen install and peer gates remain mandatory.
