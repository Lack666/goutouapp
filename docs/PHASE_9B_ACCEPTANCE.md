# Phase 9B — Authentication, Ownership and Privacy Boundary Hardening

PHASE: Phase 9B — Authentication, Ownership and Privacy Boundary Hardening

STATUS: **PASS** (CODE / TEST / DOC / DEMO / REGRESSION).

ROADMAP PREFLIGHT: Clean initial tree, HEAD14eb9d4, branch codex/phase9b-auth-privacy,
marker8/9A. Prior9A independent pre/post exits0 and hashes valid. No conflicting
formal9B–9E schedule existed; explicit user instruction establishes9B consistently
in MASTER_PLAN/validator. Phase0–8/9A retained, Phase9 IN PROGRESS,10–12 PENDING.

JWT AUDIT: PASS. Eighteen signed negative variants cover absent/bad signature,
expired/future nbf, malformed, HS384/unsigned, unknown subject, wrong subject
type/UUID, issuer/audience, tampering, non-finite dates and required claims.
CLI refuses test/staging/production. Existing policy unchanged; production
issuer/key separation/refresh/revocation is still a deployment prerequisite.

PUBLIC API INVENTORY: PASS. Actual Router/OpenAPI36 operations:3 public and33
signed owner-scoped. Undo/delete execution also guarded. Exact generated drift
gate links method, owner/IDs/parents/DTO/side effects to service/repository tests.
Framework documentation routes contain schemas only. Inventory is a service
review plus signed negative tests, not a Bearer annotation claim.

PERSON / RELATIONSHIP / CONVERSATION OWNERSHIP: PASS. Signed A/B list/detail,
foreign UUID reservation and parent association refusals; native real creation.
Missing/foreign responses stay owner-neutral; no foreign ORM/owner projection.

AGENT REST / SSE AUTHORIZATION: PASS. Owned Conversation precedes key/run lookup;
both first-REST/first-SSE and opposite-transport replay stay scoped. B cannot
read A replies/history/events. Same key under B does not authorize A. Transport
rejects every stale-epoch callback; existing controller cancellation remains.

IMPORT / HISTORY AUTHORIZATION: PASS. Foreign Job/Person/Relationship operations,
stale revisions, terminal Jobs and History/cursors remain scoped; retained9A
expiry/upload/fault tests pass. New opaque v2 History cursor binds owner/parent.
RelationshipMessage has no standalone detail/mutation/download endpoint.

MEMORY / GUARDED MUTATIONS: PASS. Controls/list/detail/Undo/prepare/execute/
receipts remain owned. Foreign challenge/key/receipt/Person cannot change A;
wrong scope, expiry, consumption and stale snapshots remain guarded. New opaque
v2 Memory cursor binds exact owner/Person/Relationship filters. Old cursors need
Refresh; digest is navigation consistency, not authentication. DTOs unchanged.

CROSS-OWNER NEGATIVE TESTS: PASS through real signed JWT→FastAPI→Application
Services→migrated disposable PostgreSQL. New security41; combined focused218.
Only Mock/provider/fault sources replaced, no authentication override or bypass
of Guarded Mutation. Synthetic data only; generated private markers not committed.

SESSION / SECURESTORE: PASS within existing development contract. Retained
logout/expiry/late401/cache/cursor/pending/challenge tests plus new late-SSE test.
Fresh Android restore/foreground/A→B/confirmation purge/logout restart passed.
Clear failure remains explicit storage_error; no complete credential-erasure
claim in that fault. Volatile pending descriptors and crash reconciliation stay P2.

LOG PRIVACY: PASS. Application fixed-message whitelist strips args/exception/
stack/extra fields; Uvicorn exception filter retained and access disabled.
Connected Web trace/screenshot/video are off; native credentials stay in private
pipes/protected input. Production collectors/rotation are not certified.

ERROR PRIVACY: PASS. Runtime-generated markers excluded from403/500/SQL/Agent
REST/SSE/ENOSPC outputs;401/404 remain generic. Retained real-socket upload/SQL
logging tests pass. Private helper timeout/PowerShell/process/OS failures suppress
arguments/output/chained Python traceback details. Small real-pool exhaustion503.

EVIDENCE PRIVACY REVIEW: PASS for stated scope. Historical131 plus9A21 files
unchanged; final automatic screen also covers new9B files (189 total). No
credential-pattern hits. Separate limited manual/provenance sampling covers
native owner/Memory/import/SSE sections, failed attempts and9A/new9B logs.
Regex is not proof of all personal information; operator/workspace metadata and
future distribution/retention governance remain explicit limits. See review.

R-07 DEPLOYMENT RISK: Production acceptable **FALSE**. Actual configured host
127.0.0.1/development and observed project listeners loopback; no project public
exposure found. Default combined per-request disk <=201MiB plus overhead,
multiplied by concurrent uploads/jobs/orphans. Actual default pool5+10/30s is
per-process only. ENOSPC begin: generic500, no Job/completed artifact; bounded
test-pool saturation503. Global/owner rates, aggregate concurrent/storage quotas,
active-body deadline and monitored admission must precede public ingress;
unprotected public exposure would be blockingP1. No whole-host tunnel/firewall
certification or aggregate availability claim.

ANDROID UPDATED DEPENDENCIES SMOKE: **PASS**, five fresh complete independent
scenes on Pixel_10/emulator-5554/Android17 API37/Expo Go57.0.9. Installed Expo
57.0.28, Router57.0.26, Crypto57.0.4, RN0.86.3 verified. Cleared loopback Metro.
Resource creation, POST SSE, Memory inspect/guarded confirmation/delete/receipt,
SecureStore restore/logout, foreground/A→B scope purge, native Document Picker,
synthetic upload and History100→200→300→301 all ran on actual Android.
Host REST Memory preconditions are separately identified. Sessionr1 failed
because the identity probe had no post-login request sample; explicit B refresh
added and the whole independentr2 passed. Failedr1 preserved, no partial splice.
Current Mobile source/dependency fingerprint and original artifact hashes gated;
existing8F procedures reused, never old evidence. Owned Metro/relay/reverses
cleaned; shared PG/emulator/other Downloads preserved.

REAL JWT / POSTGRESQL E2E: PASS, including ownership/association, Agent transports,
Import/History, Memory guards/receipts, expiry, privacy and session switching.

P0 / P1 FINDINGS: None confirmed open under observed controlled development.

P0 / P1 FIXES: No new confirmed P0/P1 required;9A R-01–R-05 retained. Fixed three
P2 boundaries: malformed Memory cursor500, unbound navigation scope and reusable
Transport late callback (App already guarded); strengthened fixed logging policy.

REMAINING RISKS: R-06 scheduler/backup/restore, R-07 aggregate admission/deadlines,
R-08 future untrusted imported analysis/provider controls, production R-09 identity/
revocation/full deletion/collectors, volatile pending descriptors and incomplete
crash reconciliation. Primary Memory delete does not erase all-system copies.

BACKEND TESTS: **644 PASS**, baseline603 retained; new41. Focused218 PASS.

MOBILE TESTS: **359 PASS**, baseline358 retained; strict/ESLint/Prettier PASS.
Repository61, Golden83, Demo Web22, Connected Web3/3/4/5/1, OpenAPI36,
Expo Doctor21/21; frozen/offline install, codegen drift, Alembic upgrade/downgrade/
check, frozen upstream, secret boundary, Ruff and Git diff checks PASS.

ROOT VERIFY: two independent complete `.\make.cmd verify` executions.

PRE-MARKER EXIT CODE: **0**, marker8/9A, original pre-marker.log/.exit.

POST-MARKER EXIT CODE: **0**, marker8/9B, original post-marker.log/.exit.

FILES CHANGED: transport.ts, logging.py, memory_control.py, import_merge.py;
new backend/Mobile/tooling security tests; authorization/privacy/native checkers,
inventory/risk/matrix/ADR0037/new reports and hashed9B evidence; Root verifier,
marker, Master Plan, architecture/auth/import/memory/threat/risk/handoff docs;
raw-byte evidence attributes. Frozen Skill/Golden/API DTOs/lockfile unchanged.

PROJECT PHASE MARKER: **completed_phase=8, completed_subphase=9B**. Phase9 overall
IN PROGRESS; Phase10–12 PENDING. No9C–9E formal names inferred.

NEXT: Latest MASTER_PLAN/Phase9 handoff's explicitly pending security/deletion/
reliability operations, especially R-06/R-07/productionR-09 and reconciliation.
Stop after9B; no subsequent stage/model/RAG/release work started.

## Reproduction and evidence

PowerShell from repository root, PostgreSQL16.15 on127.0.0.1:15434; each test/
fixture creates, migrates and drops its own synthetic database. Set:
`TEST_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:15434/goutou_test`,
`PYTHONUTF8=1`, `PLAYWRIGHT_CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe`,
and prepend System32 to PATH. Separate PYTEST basetemps/cache were used. Complete
commands/stdout are in [pre](evidence/phase9b/pre-marker.log) and
[post](evidence/phase9b/post-marker.log); independent exits accompany both.
[PHASE_9B_MATRIX.json](PHASE_9B_MATRIX.json) records original-byte SHA256 hashes,
full native steps/reports/logs/exits, failure history and current source fingerprint.

Focused command uses locked uv pytest on test_authorization_security,
test_privacy_logging, test_upload_security, test_resource_api, test_memory_mutation
and test_phase6_e2e. Native first3 ran phase8_native_closeout with fresh batch
phase9b-core-r1; import ran phase9b_android_smoke r1, session reran r2. Fresh full
reproduction uses phase9b_android_smoke's five procedures plus the documented
loopback Metro/adb prerequisites in PHASE_8_FINAL_ANDROID_DEMO; never overwrite
old batch evidence or record CLI credentials. Release APK/EAS not requested.

Commit/worktree: clear Phase9B commit after all gates; exact final SHA and clean
tree returned separately to avoid a self-referential committed SHA.

Post-marker attempt history: first complete invocation exited1 when the existing
Connected Agent HTTP test worker terminated with Windows code3221226505. No
authentication assertion failure was reported; root cause remains unconfirmed.
The unchanged full Agent gate then passed3/3, followed by a fresh complete
post-marker root exit0. No retries were configured into tests, assertions removed
or dependencies changed. Failed log/exit and successful independent recheck are
preserved with hashes in the matrix. Windows runtime stability remains a P2
validation-environment follow-up, not a claimed repaired product defect.
