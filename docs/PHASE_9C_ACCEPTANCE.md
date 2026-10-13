# Phase9C — Aggregate Resource Admission and Upload Reliability Hardening

PHASE: Phase9C — Aggregate Resource Admission and Upload Reliability Hardening.

STATUS: PASS within the tested shared local topology; independent complete
pre-marker and post-marker verification both exited0. Public production acceptance
remains FALSE. Matrix acceptance_state is closed, so the post-marker hash/exit
is now required by the security checker.

ROADMAP PREFLIGHT: clean1d556e9/8-9B; one worktree; newcodex/phase9c-resource-admission.
No conflicting9C scope existed; current explicit instruction formalizes it in
MASTER_PLAN and validator. Prior9B original pre/post hashes valid and both exits0;
9A/8F gates remain. Phase9 overall IN PROGRESS;10–12 PENDING.

R-07 BASELINE: no aggregate/rate/storage/active-body controls in9B. One upload
could occupy201MiB plus filesystem overhead before concurrent multiplication.

DEPLOYMENT ASSUMPTIONS: same host/local root, sibling private OS fences, PostgreSQL
and identical worker policy. Observed existing PG127.0.0.1:15434 only; no project
API/public listener. Test workers bind ephemeral loopback ports. No tunnel/firewall
or public gateway certification; public production acceptableFALSE.

UPLOAD RESOURCE BUDGET: file100MiB/body101MiB; full201MiB+16KiB reservation,
global8GiB/Owner2GiB, upload8/4, process2/2, retained Job1000/100, speakers1024.
Actual file byte scan includes cancelled/expired/deletion-failed/crash remnants.
This is accounted storage, not total physical allocation or process RSS.

EARLY REQUEST ADMISSION: ASGI JWT/known Owner/reservation before Multipart receive;
one file/two fields; actual byte cap retained. Public liveness/status/schema/OPTIONS
exemptions preserve contracts and require external ingress limits.

PER-OWNER LIMITS: trusted signed existing User identity; no body/XFF Owner authority.
Owner request/upload windows, upload/process slots, retained/pending budgets.

GLOBAL LIMITS: PostgreSQL-shared protected API/upload windows, independent upload/
finalize slots, reservations and retained bytes. DB pools bounded per process;
whole-host/TLS/header/non-upload body limits are external production prerequisites.

MULTI-WORKER CONSISTENCY: actual two spawned Uvicorn processes share DB/root/policy;
cross-worker Owner/global saturation/rate and post-kill legal requests tested.
Different machine/object-store topology is unsupported, never inferred.

STORAGE QUOTAS: full active reserves plus physical inactive files; active files
not double charged. Unknown ownership blocks upload but operator snapshot/maintenance
can count and clean it. Missing files remove inactive attribution; status alone cannot
release bytes.4KiB accounting overhead is not universal filesystem allocation proof.

SLOW-CLIENT TIMEOUT: actual receive idle15s/total120s configured; real short-deadline
TCP tests cover no data and active fragmented bodies.408 safe envelope; disconnect
closes spool/source and releases capacity. Post-body kernel hangs require supervision.

ATOMIC ADMISSION: PostgreSQL transaction advisory guard,250ms lock/2s statement
bounds; no oversubscribed slots in concurrent issuance. Same shared configuration
fingerprint required; altered worker policy fails closed.

RESOURCE RELEASE: success/failure/overflow/parser/ENOSPC/rollback/cancel/finalize/
replay and cleanup faults retain correct reservation/file semantics. Import exact
dataset/revision/binding/receipt behavior remains server authoritative.

WORKER CRASH RECOVERY: OS fence survives DB backend loss while worker alive. Real
termination during body, partial write and completed source-before-Job commit is
covered. Next admission/operator reconciliation frees dead slots and retains bytes.
No elapsed-time recycling of live work; no automatic scheduler claimed.

QUOTA RECONCILIATION: scans private root, known Artifact metadata and reservation
attribution under guard. Active pre-registration files protected from old-orphan
sweeps. Explicit maintenance reconciles→cleans→reports counts; unresolved deletion
continues to cost quota. No fake deletion or receipt removal.

ERROR CONTRACT: existing ErrorResponse/36 operations/unchanged generated DTOs;
413 upload_too_large;429/408 http_error;503 artifact_unavailable, Retry-After when
appropriate. No SQL/path/file/credential/other-owner quota information.

LOGGING / METRICS PRIVACY: existing fixed whitelist, exception filtering and disabled
access logs. Operator snapshot only aggregate byte/active counts and fixed worker
event categories; no private labels. Runtime fake markers stay uncommitted.

Final read-only pattern screen:203 files (8F131,9A21,9B37,9C14 including matrices),
74 JSON/64 exit/65 log; zero credential-pattern findings and no unreviewed file
types. Original189 historical files remain unchanged. New full pre/post logs contain
synthetic demo IDs/counts and local test paths; their end summaries were sampled.
Screened inventory SHA256:
5ea8f8d9454b53aa3aeb5bd2fd2f2f78da944ef8ae145376f77bd873266b5959
(raw working-tree bytes at closure; individual execution evidence hashes are the
cross-checkout gates). Pattern screen is not a general PII proof.

Evidence provenance and manual review: inspected the new worker fixture, signed
credential transport and synthetic transcript factory; credentials travel through
private spawn pipes/request headers, not argv or output. Reviewed both retained
failure traces and the complete crash-host diagnostic, plus focused/pre-marker
summaries and the snapshot/event implementation. Failures show synthetic database
names, code assertions and safe status codes; no original chat files are inputs.
Automated credential-pattern screening is recorded separately after closure. This
limited manual sample and a zero-pattern result cannot prove absence of all PII.

REAL JWT / POSTGRESQL E2E: real signed TCP→FastAPI→services→migrated disposable
PostgreSQL→isolated Artifact Store. Two independent workers; no auth overrides.
Additional TestClient cases identify their in-process scope, not TCP proof.

IMPORT REGRESSION: retain parser/type/hash/binding/ready/merge/receipt/deletion tests
and original dataset semantics. Workflow's speaker cap is an explicit safe rejection.
Old anonymous chunk-byte test now isolates the same middleware; signed overflow
coverage retained. Storage ENOSPC begin now formally503 instead of unexpected500;
old privacy assertion updated with the contract reason, never removed.

Retained unsuccessful invocations: focused-attempt1 exited1 (135 PASS/2 FAIL)
because a terminated worker returned a failure HTTP response on this host instead
of the narrowly expected TCP exception. Dedicated host diagnostics observed502;
the final test disables environment proxy use, accepts only disconnect or HTTP
failure, and additionally asserts actual process termination and zero committed
Jobs. The cause of the original502 is unconfirmed. No successful response is
accepted. Pre-marker-attempt1 exited1 because Root uv --env-file populated an
unavailable development DATABASE_URL in intentionally database-free Mock Service
contract fixtures. Those fixtures now explicitly set database_url=None; JWT/service
assertions remain, and real migrated PostgreSQL E2Es are separate. The same fixture
issue affected two CORS cases in an intermediate backend diagnostic and was fixed
there. Both retained failed invocations are hashed in PHASE_9C_MATRIX. The
intermediate backend-env diagnostic is also retained (669 PASS/2 FAIL); its separate
exit code was not recorded and is explicitly NOT RECORDED, never an acceptance gate.

MOBILE COMPATIBILITY: four new tests keep failed/unknown states and no automatic
re-upload, retain HTTP unavailable/status distinct from offline, suppress raw text.
Shared503 remains conservativeunknown_outcome; known Job inspect/revision/receipt
behavior remains. Mobile src/dependency fingerprint unchanged; no new9C Android
run claimed. Prior9B current-source native gate remains mandatory and passes.

P0 / P1 FINDINGS: no confirmed new open P0/P1 under tested local topology. Unprotected
public deployment remains blocked; it would not inherit this local acceptance.

P0 / P1 FIXES: substantively mitigate R-07 with early authentication, shared admission,
actual receive deadlines, resource accounting and fenced recovery. No production waiver.

R-07 REMAINING RISK: undeployed ingress/TLS/header/connections/non-upload body limits,
whole-host storage writers/cluster costs, pool sizing and supervisor. No universal
DDoS/RSS/physical-quota guarantee. Live hung workers require explicit supervisor action.

PRODUCTION DEPLOYMENT STATUS: NOT DEPLOYED / production acceptableFALSE. R-06 monitored
retention/backup/restore and R-09 production identity/deletion/reconciliation remain.
9B unconfirmed Windows worker exit3221226505 remains P2; any recurrence preserved.

BACKEND TESTS:671 PASS in each full root run (pre84.17s/post85.75s); baseline644
and all earlier cases retained. New9C27; focused137 PASS with actual Windows
symlink execution. Repository67 PASS.

MOBILE TESTS:363 PASS in each full root run; baseline359 plus4 new cases.

ROOT VERIFY: complete pre-marker and post-marker PASS. TypeScript strict/ESLint/
Prettier/frozen pnpm install, Expo Doctor21/21, OpenAPI36 generation/drift,
Backend/Mobile/old focused gates, Golden83/upstream/secret/Ruff, PostgreSQL/Alembic
upgrade/downgrade/check, Web Demo22 and Connected3/3/4/5/1 all passed.

PRE-MARKER EXIT CODE:0, docs/evidence/phase9c/pre-marker.exit.

POST-MARKER EXIT CODE:0, docs/evidence/phase9c/post-marker.exit.

VALIDATION COMMANDS: locked uv pytest focused/full; pnpm strict/lint/format/test;
real spawned Uvicorn TCP tests; Alembic upgrade/downgrade/check; codegen drift;
Golden/upstream/secret/Ruff; all existing Web gates and complete make.cmd verify.
Set TEST_DATABASE_URL to the loopback synthetic_test template, PYTHONUTF8=1,
Chrome executable path and System32 PATH as recorded in9B acceptance. No real chats.

Independent root commands: .\make.cmd verify (before/after marker); saved stdout/
stderr in separate pre-marker.log/post-marker.log and saved each LASTEXITCODE in
its own .exit immediately after completion. PYTEST_ADDOPTS supplies distinct
.cache/phase9c-pre-marker-r2 and .cache/phase9c-post-marker basetemp directories
and distinct pytest cache directories. No retries are hidden in these invocations.

FILES CHANGED: admission ASGI/service/OS fence/metadata migration, Settings/pool,
upload form/storage/preview/cleanup, security/Mobile/tooling tests, Root/marker gates,
budget/reliability/ADR/matrix and threat/risk/roadmap/handoff documentation.

ARCHITECTURE DECISIONS: ADR0038; existing PostgreSQL/local artifacts, no new infrastructure,
public endpoint, model/Agent behavior or dependency.

PROJECT PHASE MARKER:completed_phase8/completed_subphase9C, post-marker verified0.
Phase9 overall IN PROGRESS; Phase10–12 PENDING.

NEXT: explicit future Phase9 deletion/backup consistency/reliability task from current
MASTER_PLAN/handoff. Stop after9C; no9D/10/11/12 or real provider integration.
