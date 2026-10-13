# Phase9E — User Data Erasure and Security Reliability Closeout

PHASE: Phase9E — User Data Erasure and Security Reliability Closeout.

STATUS: PASS — CODE / TEST / DOC / DEMO / REGRESSION; independent complete pre/post exits0.

ROADMAP PREFLIGHT: clean dce4737, completed_phase8/completed_subphase9D. Explicit
9E scope registered before implementation. Phase0–8 and9A–9D retained; Phase9
IN PROGRESS;10–12 PENDING. No uncommitted user changes existed.

9D BASELINE: independent dce4737 checkout complete `.\make.cmd verify` exit0;
Backend715/Mobile363/repository74. PHASE_9E_MATRIX links successful execution and
retains failed invocation logs/details; no old report substitutes for execution.
Original dce4737 tracked content matches under explicit LF comparison. Baseline
checkout uses _phase9e_baseline to avoid Windows Jest escaped-dot glob ambiguity.
Mobile LF checkout policy is now explicit; binary assets keep automatic detection.

DATA DELETION INVENTORY: DATA_DELETION_MATRIX.json covers each domain's owner,
confirmation, affected resources, primary rows, receipts, dedup, Memory, backup and
UI/API limits. DATA_LIFECYCLE_INVENTORY covers19 tables through20261013_02.

IMPORTED DATASET DELETION: signed exact canonical dataset_job_id/Relationship,
five-minute snapshot challenge, physical RelationshipMessage and speaker removal,
durable imported Job tombstone/dedup metadata. Original/duplicate/new identical
same-scope finalize409 dataset_deleted. Other transcripts/scopes stay independent.

CONVERSATION DELETION: exact owner/Conversation/optional Relationship; remove all
formal Messages, preserve hidden Conversation/Run/key fences. Active/pending or
completed-unresolved run rejects target_busy. Old Agent REST/SSE404, old UUID
creation409. No forced stop or automatic age reset.

PERSON / RELATIONSHIP CONTRACT: Backend/UI deletion unavailable including empty
resources. Existing RESTRICT/multiple Relationship/Memory/import/provenance FKs
remain; no enlarged cascade. Formal future lifecycle task, not implicitly erased.

ACCOUNT ERASURE BOUNDARY: full Owner/account erasure formally unfinished R-09.
Development JWT is no production identity/revocation lifecycle. App cannot claim
complete personal-data deletion; copy/export/provider/backup policies remain.

GUARDED MUTATION: Prepare → server confirmation → explicit Execute → durable
receipt → authoritative refresh; no confirm boolean. Canonical UTC snapshots,
counts/scopes/expiry/consumption and owner checks; same-key changed payload409.

OWNER ISOLATION: signed A/B target/challenge/receipt denial; all reads filter owner.

IDEMPOTENT REPLAY: immutable owner/key/payload receipt survives unread socket response,
service restart and challenge cleanup; never re-executes or deletes later data.
Two real Uvicorn processes and PostgreSQL arbitrate concurrent same-key calls.

HISTORY/CURSOR INVALIDATION: physical rows gone and tombstone-filtered queries;
old Relationship cursor returns empty; deleted Conversation history404. Mobile
focus/open/refresh/leave/logout clears cached models/cursors using existing epochs.

MEMORY / IMPORT DATA SEPARATION: both deletions preserve Memory/consent/undo and
the other history domain; no Agent/LLM/Memory invocation in ErasureService.

RESTORE SAFETY: real native pg_dump/pg_restore in quarantined synthetic DB; frozen
current primary checks immutable target scopes, propagates exact tombstones, removes
formal body/speaker rows, copies current immutable receipts and invalidates challenges.
Existing Memory and Agent key checks retained. Repeated reconciliation safe.

MISSING PRIMARY RECOVERY: missing/unavailable/tampered/lagging target/key/receipt
authority or restore error keeps release false. No independent journal implemented;
production full-primary-loss recovery unavailable. Post-backup data loss disclosed.

RETENTION AUTOMATION: opt-in local periodic loop, actual repeated cycles/fail/retry/
worker death/restart/root contention/cursor/capacity tests retained. New expired erasure
challenges use bounded expiry+24h maintenance; receipts remain. Production scheduler
registration, supervision and monitoring NOT DEPLOYED.

BACKUP/RESTORE: anonymous native unencrypted dumps only, temporary and removed.
Future encrypted daily35d rotation/key custody/operator audit/alerts/cutover policy
is specified, not installed. Local DELETE cannot modify older backup copies.

9C QUOTA RECONCILIATION: original27-case suite retained; physical artifact source
cleanup remains9D terminal/TTL/retry, separate from primary-history deletion receipts.

ANDROID REAL DELETION: NOT IMPLEMENTED / Backend-only. No App prepare/confirm/execute
flow. Generated client39 and safe error adapters synchronize contract; Settings and
History disclose limitations. Fresh five-scene Connected regression is separate.

LOG/PRIVACY AUDIT: allowlisted messages/counts only; no body/labels/JWT/provider
reasoning in erasure tables/logs. Failed DB/receipt operations generic503; native
credential pipes and original privacy tests retained. Evidence screen is limited
credential pattern/provenance validation, not a guarantee of arbitrary PII absence.

R-06/R-07/R-08/R-09: current PHASE_9E_RISK_ASSESSMENT records all four as production
open/blocked with controls/tests/remaining/dev/prod risks/next tasks. Public acceptableFALSE.

P0/P1 FINDINGS: no confirmed open implementation P0/P1 in controlled local scope.
Full-account/identity/App erase and production DR remain explicit admission gaps.

P0/P1 FIXES: 9E-01/P1 reproduced on real native restore (exit1), then fixed and
retested (exit0): an old ready Job cannot supply the canonical imported dedup
fence, so restore refuses release. UTC connection-independent snapshots also
repaired a fail-closed false conflict. No original safety assertion removed.
9E-02/P2 lock cycle reproduced (exit1) and fixed (exit0) using owner FOR NO KEY
UPDATE; a concurrent new Run commits and erasure rejects target_busy.

BACKEND TESTS:754 PASS on both independent complete pre/post runs; focused39 PASS,
original lifecycle44 and admission27 current-source regressions PASS.

MOBILE TESTS:374 PASS (original363 preserved, eleven additive tests). Five fresh
Android scenes PASS; no erasure UI. Repository80, Golden83, Web22/3/3/4/5/1, Doctor21/21.

ROOT VERIFY: two independent complete `.\make.cmd verify` processes PASS.
Original-source9D baseline also complete exit0; unsuccessful attempts are retained
in PHASE_9E_MATRIX. No cherry-picked gate is substituted for either full root process.

PRE-MARKER EXIT CODE:0 (pre-marker.log/.exit in PHASE_9E_MATRIX).

POST-MARKER EXIT CODE:0 (independent post-marker.log/.exit).

FILES CHANGED: erasure models/migration/service/schema/routes; tombstone access,
merge/dedup guards and primary restore; bounded challenge retention; OpenAPI/client,
safe adapters/UI limitation text, tests, stage gates/docs/evidence.

ARCHITECTURE DECISIONS: ADR0040. PostgreSQL/REST/Python service boundaries preserved;
no new dependency/infrastructure, real provider/chat, RAG or Runtime reasoning changes.

PROJECT PHASE MARKER:8/9E, independently reverified after marker change.

PHASE 9 OVERALL STATUS: IN PROGRESS. Full deletion/production prerequisites not waived.

NEXT: stop after9E; further Phase9 work requires explicit authorization. Only after
whole9 acceptance may MASTER_PLAN advance10/11/12. No later implementation here.

Actual verification environment (process-only overrides; original .env unchanged):

```powershell
$env:TEST_DATABASE_URL="postgresql+psycopg://postgres@127.0.0.1:15434/goutou_test"
$env:DATABASE_URL="postgresql+psycopg://postgres@127.0.0.1:15434/goutou_dev"
$env:PYTHONUTF8="1"
$env:PATH="C:\Windows\System32;"+$env:PATH
$env:PLAYWRIGHT_CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
.\make.cmd verify
```

Backend tests use disposable migrated databases; no development rows erased.
Final native smoke: `scripts/phase9b_android_smoke.py --adb <Android SDK adb>
--serial emulator-5554`: resource/SSE/Memory/import batch9e-r3 and complete session9e-r4. The session script waits for the durable no-token UI acknowledgement before force-stop, and retains the original after-restart assertion.
Prior9e-r1/9e-r2/9e-r3 executions and failures remain separate history; final artifacts
all correspond to final Mobile source. No step-splicing or self-service erasure
is claimed. The blocked ADB invocation was interrupted before any scene existed;
the verified SDK5037 daemon was restarted and emulator device status reconfirmed.
