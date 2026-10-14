# Phase 9F — Mobile Self-Service Data Erasure Integration

Status: PASS — controlled development acceptance only. Complete independent
`make.cmd verify` pre-marker r4 (8/9E) and post-marker r2 (8/9F) each exited0.
Marker is `completed_phase=8`, `completed_subphase=9F`. Phase9 overall remains
IN PROGRESS; Phase10–12 PENDING. Work stops after9F.
Only the user's explicitly authorized 9F scope is implemented. Frozen Skill,
Golden83 and Agent reasoning/provider behavior are unchanged. No ErasureService
rewrite or new analysis feature was introduced.

Preflight read AGENTS, MASTER_PLAN, architecture, 9E acceptance/matrix, deletion
contract/matrix/lifecycle/backup policy, Phase9 handoff, resource/import/history/
Agent/Mobile/Memory/auth/idempotency contracts. Initial Git was clean at
`a6d8c2c` (9E). Historical matrices and evidence remain immutable.

The expected 9E baseline is Backend754, Mobile374, repository80, Golden83,
Web22/3/3/4/5/1, OpenAPI39, Doctor21/21. Independent original-source verification
was attempted on a frozen Git archive; failure logs are retained. Its existing
concurrent upload test reproduces a file-promotion/inventory TOCTOU: `is_file()`
sees a vanished `.part` after atomic rename and rejects an otherwise admitted
upload. Buffered instrumentation identified ResourceAdmission inventory line160.
9F minimally uses one no-follow stat, permits vanished entries only under a live
fully charged reservation and retains rejection for unknown entries. Two new
deterministic PostgreSQL regressions protect charging and fail-closed behavior.
The pristine baseline failure is not reported as a successful verify.

Existing APIs could not list canonical imported Datasets after App restart.
The sole added public operation is the signed, owner/Relationship-scoped summary
query. OpenAPI now40 preserves the original26 frozen operations/schemas and all
existing39 operations; generated TypeScript is checked for drift. Five real
PostgreSQL tests cover canonical-vs-duplicate, owner/parent neutral404, pagination,
cursor scope/limits and tombstone summaries. No message text or raw speaker label
is exposed in discovery.

Shared Mobile state machine, domain-specific target adapters and explicit server
confirmation drive History and Chat erasure. Both require durable receipts and
authoritative refresh; bounded session-only original-key recovery, Busy, expiry,
owner/epoch switching and late response invalidation preserve 9E safety. Memory
and backup limits are visible. See [user/runtime contract](MOBILE_DATA_ERASURE.md).

Final runs: Backend761/761; Mobile396/396; repository88/88; Golden83;
OpenAPI40; Expo Doctor21/21; existing Web22/3/3/4/5/1 and new erasure2/2.
Independent Android Dataset and Conversation executions passed signed App
Prepare/Execute/Receipt, authoritative refresh and SQL deletion, with other scopes
and Memory retained. Fault/restart and all five previous native scenes also passed
on the final App source, with execution-time fingerprints and complete transcripts.

Final complete root evidence is independently recorded and hashed:

- [Pre-marker r4, exit0](evidence/phase9f/phase9f-pre-marker-r4.log), marker8/9E.
- [Post-marker r2, exit0](evidence/phase9f/phase9f-post-marker-r2.log), marker8/9F.
- [Matrix](PHASE_9F_MATRIX.json): closed; individual exits, SHA256 artifacts,
  source fingerprints, SQL/wire proofs and original matrix hash links.

Prior failed runs remain failures. Original baseline reproduced the upload
inventory race fixed as9F-01. First pre-marker run failed an old Person concurrent
create503 (760 others passed). Instrumented360-case repetition reproduced250ms
admission LockNotAvailable/SQLSTATE55P03; exact earlier uninstrumented causes remain
unconfirmed. Test/demo ResourceFlow establishes one signed read-only request before
business races: diagnostic and uninstrumented repetitions each pass360. All original
mutation statuses, concurrency and SQL uniqueness assertions remain, with no retry,
production timeout or quota change. The helper is source-fingerprinted.

Second pre-marker run passed Backend761/Mobile396/Doctor21/DemoWeb22 before the
old Connected network allowlist rejected new Dataset discovery. It now permits
only the exact owned summary path and asserts observed requests are GET-only;
all original owner/status/count checks remain. All Web groups independently pass.
Earlier pre-marker r3 passed; post-marker r1 failed two historical unit tests that
still rejected explicitly authorized9F. Their future-phase rejection advances only
to9G, preserving prior security/native assertions. Marker was restored8/9E;
affected lifecycle44 and repository88 were revalidated before the final full
pre-marker r4 and post-marker r2. A sandbox-only lifecycle attempt failed temporary
directory access; the independent authorized host run passed44. All nonzero logs
and exits remain retained, including Android accessibility/Metro setup failures.

Known limits: development JWT issuer/refresh/revocation; private filesystem and
single shared-root admission assumptions; production ingress sizing/supervision;
monitored retention/scheduler/encrypted rotation; independent deletion journal;
full account/Person/Relationship erasure; lost-primary disaster recovery; and
long unresolved Agent Runs; discovery UI windows of200 summaries and20 volatile deletion attempts. No unsafe automatic Run reset or deletion exists.
No provider, RAG, release or Phase10–12 work is authorized. Stop after9F.


Commands and environment: Windows PowerShell, uv locked dev environment, pnpm11.25.0,
Python UTF-8, PostgreSQL16 on loopback15434 with per-test disposable databases,
Chrome through PLAYWRIGHT_CHROME_PATH, Expo57 / React Native0.86.3. Android API37
emulator-5554 uses Metro8092 on IPv6 loopback, an IPv4 loopback relay8093 and adb
reverse for API8024. The native observer is explicitly enabled for metadata-only
SSE acceptance. No account, provider key or secret is committed.

- Original source: Git archive a6d8c2c; `.\make.cmd verify` in isolated snapshot.
  Original full backend753 passed/1 failed from old concurrent upload race;
  original Mobile374, repository80 and Golden83 separately pass. Snapshot Jest
  uses existing module paths because pnpm rejects an external dependency junction.
- Backend: `uv run --locked --group dev pytest -q apps/server/tests` =>761 pass.
  A prior run had one old resource-owner race503/760 pass. Full resource90 and
  backend761 reruns pass; root pre/post must independently pass too. Its precise
  transient cause is unconfirmed and is not advertised as a fixed service bug.
- Focused final source: admission27, lifecycle/backup44, erasure39, discovery5,
  upload-scan regression2; all independent exit0 with SHA256 evidence.
- Mobile: `pnpm --filter @goutou/mobile test` =>396; includes existing374 plus22 cases,
  exact DTO projection, all dangerous states, immutable retry, session/owner reset,
  expired token, stale target, late REST/SSE/History and domain separation.
- Web: `pnpm --filter @goutou/mobile smoke:erasure` =>2. Both anonymous signed
  journeys check actual UI and SQL, not just control availability. Other-scope
  preservation, tombstones/recreate409, A/B denial and unknown-body replay covered.
- Native: `uv run --locked --group dev python scripts/phase8_android_demo.py
  --adb <SDK adb> --serial emulator-5554 --port 8024 --closeout --steps
  scripts/native/phase9f_<scene>.json --report .cache/<unique-report>.json`.
  Dataset and Conversation are independent complete actual App executions.
  Faults cover server expiry, committed response loss, exact-body/key replay and
  persistent target_busy. Restart/session covers Back, force stop, restored login,
  logout, A→B and expired-token zero mutation. SQL proves retained other scopes.
- Existing native regression: `python scripts/phase9b_android_smoke.py --adb
  <SDK adb> --serial emulator-5554 --batch 9f-r3`; each scene keeps its own exact
  steps, report, full log and exit. Web never substitutes for this gate.

Failed attempts remain in evidence with nonzero exits, including initial ADB/
Metro, Web fixture-navigation/timing and original-source baseline failures.
Historical9B/9C/9D/9E matrices and logs are byte-preserved; current-source gates
require a new independent five-scene native suite plus27/44/39 revalidation.


Final review also tightened recovery selection to the exact domain, target and
Relationship, including coincident UUIDs across domains. The immutable Execute
body/key was already isolated; the UI recovery predicate now has the same scope.
A new regression proves different domain or Relationship cannot recover the
attempt. Mobile total is396. All native acceptance is repeated on the final
client, and each execution records Mobile and erasure-contract source fingerprints
at start; the gate compares the recorded values to current source. Earlier native
successes are retained as superseded evidence and cannot satisfy final gates.
