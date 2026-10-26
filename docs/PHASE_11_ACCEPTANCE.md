# Phase 11 — Agent Evaluation & Observability

PHASE: Phase11 — Agent Evaluation & Observability. Date2026-10-26.

STATUS: **BLOCKED on quality acceptance and real human review.** Evaluation and
observability tooling is implemented and focused engineering tests pass. Do not
label Phase11 formally PASS or claim all functional/quality acceptance conditions
complete. FINAL REGRESSION PENDING. No Phase12 work starts.

ROADMAP: Phase10 OPTIONAL/DEFERRED by explicit user decision; Phase11 IN PROGRESS;
Phase12 PENDING. Original Phase10 requirements and all Phase0–9 evidence remain.

PROVIDER IMPLEMENTATION: existing OpenAI-compatible adapter, no new dependency.
Backend-only model/URL/key/timeout/output cap/temperature/thinking settings.
Formal schema sent with JSON mode; Pydantic and independent semantic guards stay
mandatory. Timeout/429/5xx/disconnect/empty/JSON/schema/truncation fail safely.
Provider calls have no automatic retries. Paid scripts explicitly opt in and
reserve requests/tokens/cost before sending; unknown price refuses admission.

DEEPSEEK LIVE CHAT: PASS, final-live-smoke.json, Chinese/Emoji, usage/model recorded.

DEEPSEEK LIVE STREAM: PASS, same artifact, incremental text, stop/DONE, usage and
TTFT. Hidden reasoning discarded. TTFT is measured only for streaming content.

DEEPSEEK STRUCTURED OUTPUT: PASS for formal SafetyResult smoke. This does not mean
all runtime schemas always succeed; the final50-call dataset validity is92%.

REAL AGENT E2E: actual signed JWT → FastAPI → AgentService → LangGraph → DeepSeek
→ disposable PostgreSQL. final-live-e2e.json contains high-risk REST completion,
ordinary SSE completion and another ordinary REST failure. Thus2/3 scenario runs
complete,13 provider requests. Every scenario has one persisted run; successful
ones have two messages, failed one no assistant message. All replay/no-Memory/
foreign-owner rejection checks pass. A successful ordinary SSE path executes
FIU/Analysis/Plan/Response and formal structured validation. The failed REST case
is retained, not relabeled success. REST and SSE completion are both demonstrated;
ordinary quality reliability is still failing.

EVAL DATASET:60 anonymous synthetic cases, category minima12/12/12/8/8/8; complete
expectations/forbidden behavior/routes/variations/assertions/review indicators.
Golden83 unchanged. Full new standalone dataset runs offline twice with60/60
expected contract outcomes, including8 deliberate failures. Mock fixtures are
oracles, not evidence that a real model understands all60 cases.

EVAL VERSION: agent-v1; behavior-structural-v1; graph phase3h-observed-v1;
prompt phase11-existing-guards-v2. Dataset hash and Git base commit8023df3 are
recorded in each artifact. Final20-case aggregation uses three distinct bounded
processes:12 safety requests,18 communication requests,20 grounding requests.
Every process stays below30 requests,500000 reserved tokens and5 CNY.

SAFETY METRICS: final12/12 explicit high-risk cases correctly route to safety,
zero severe misses, no ordinary analysis/plan/response or Memory persistence node
on those paths. Two high-risk repeats also pass. This small purposive sample does
not prove adversarial completeness. No unauthorized dangerous side effect observed.

GROUNDING METRICS: final ground cases2/4 complete; ground-01 fails independent
analysis guard, ground-07 fails Pydantic AnalysisPoint validation. All five final
failed cases remain in aggregate-final.json. Source-shape checks are automated;
semantic entailment, fabricated experience and stale-memory correctness require
review and are NOT RUN as human-scored metrics. Imported RelationshipMessage
attribution remains NOT IMPLEMENTED and is not claimed.

ADVICE QUALITY:20 representative unique live cases complete15/20=75%, below85%.
Communication1/4 complete. Six anchored1–5 dimensions and structure-only automatic
proxies are implemented; real human review0/15, **NOT RUN**. Review packet is
evals/agent/results/human-review-15.json; authentic reviewer/time/reason/six scores
and matching output hash are required. No AI is represented as a human evaluator.

MEMORY SAFETY: targeted consent, pause/revoke, no unauthorized write, natural-language
deletion/undo confirmation, exact owner/subject and signed API guards pass in the
338-test suite. Real E2E has zero Memory writes. Standalone60-case tests disable
Memory; they are not independently advertised as seeded-store authorization tests.

GRAPH NODE TRACE: actual node start/end UTC times, run UUID, durations, status,
route, safe error category and runtime outcome. Graph/prompt version recorded.
Database persistence outcome is distinct from graph completion. Failure/cancellation,
event order, correlation, bounded retention and failing sink are tested. No fake
load_profile/finalize nodes are introduced.

LATENCY: final20 cases mean5212.73ms, nearest-rank P50=1346.35ms, P95=14531.86ms.
These are measured whole-case runtimes, not production SLA or isolated vendor
server time. Per-node/provider and stream TTFT appear in raw traces.

TOKENS: final50 calls report54837 input,11471 output,66308 total;
cache-hit22272, cache-miss32565 input tokens. Per-call distributions are retained.

COST: final20-case set known conservative peak-price estimate0.15778888 CNY;
mean per provider call0.0031557776 CNY, unknown0/50. Per-case average0.007889444 CNY.
Prices from official CNY documentation checked2026-10-26, version
deepseek-flash-2026-10-26-peak-cny. These are upper-bound estimates, not invoices.
All recorded development/smoke/E2E/repeat attempts total185 provider admissions,
known cost upper bound0.6326848 CNY, three unknown-cost initial network failures.
An additional three-call Smoke process reached result saving but Git ownership
failed before evidence write; outcome/usage/cost remain UNKNOWN, not zero or PASS.
Therefore the complete development invoice total is UNKNOWN. No repeated request
is hidden; see attempts.json. Each process had its own explicit bounded budget.

ERROR RATE: final4/50=8% provider operation failures, all structured-output
validation errors; zero observed HTTP429/5xx/timeout in the final set. One additional
independent graph validation rejection makes five failed cases total. These are
output quality errors, not an8% claim about vendor network availability.

REPRODUCIBILITY: final artifacts have identical start/end source fingerprint
c9f202002e6e6bde5a326158f2e37a5841362cebfce36e84aabd26fb74bcb30a.
evaluated-source.zip preserves that exact app/evaluator/dataset/lock snapshot.
Only review.py string formatting changed afterward; check_phase11 verifies all
other bytes and identical Python AST. Source archive hash is recorded in
docs/evidence/phase11/evidence-check.json. Both deterministic Mock runs agree after
removing run IDs. Four key live repeats all complete; ground-01 changes from fail
to complete, proving output variability. Repeats are not substituted into the20-case
75% score. Report recomputation to fresh paths matches original metrics exactly.

PRIVACY: api.txt ignored, never staged/printed; no client changes or EXPO_PUBLIC
keys. Trace fields omit private bodies, references, Memory, headers, credentials
and hidden reasoning. Exact private-key scan and forbidden trace-field check pass.
Only visible outputs from the fixed anonymous synthetic dataset are exported.
Trace buffer4096 events/24 hours, process-local; no production collector claim.

TARGETED TESTS:338 passed in20.33s, exit0. Raw output/exit in
docs/evidence/phase11/targeted-tests.txt and targeted-tests.exit. Covers providers,
new harness/trace/budget/privacy/cancellation, Golden83 contracts, actual graph,
analysis/action response, consent/deletion, JWT/owner isolation, same-key/unknown
outcome/disconnect and new real-adapter fault→signed API→PostgreSQL tests.
No production identity/deletion contract was weakened. Ruff and format are checked
on changed Python code. No TypeScript changes; no unrelated Mobile typecheck.
No Python static type checker is configured; no unsupported typecheck PASS claim.

LIVE MODEL TESTS: final chat/stream/structured Smoke3/3; final unique20 cases15/20;
repeat4/4; final real E2E2/3 scenario completions, with required completed REST and
ordinary SSE paths plus retained failure. Every live artifact has model, parameters,
time, version, budget, usage, latency, outcome and safe failure information.

QUALITY GATE: **FAIL** — completion75%<85%; structured validity92%<95%; human
review0/15. Safety gate passes for the measured cases. Do not convert this into
FUNCTION COMPLETE quality acceptance or formal Phase11 PASS.

KNOWN FAILURES: communication-02/04/05 and grounding-07 have malformed source-kind
relationships in AnalysisPoint; grounding-01 fails an independent analysis guard.
Initial20-case baseline was12/20 complete (all12 safety; zero8 ordinary/grounding).
Adding schema delivery and existing-guard instructions improves final outcomes
without deleting failures, changing expectations or weakening validators.

REMAINING RISKS: ordinary generation still unreliable; conservative regex guards
may reject benign discussion, and source-shaped JSON cannot prove truth. Fixed
English crisis text is too generic for a Chinese mobile product. Human quality
review is missing. Live representative coverage is20 of60, with no claim that all
privacy/Memory semantic attacks were run live. Trace retention is development-only.
Provider external retention/deletion policy and production identity/release risks
from Phase9 remain outside this acceptance. Early Smoke save failure has unknown
billing and cannot be repaired retroactively by inventing evidence.

FULL REGRESSION: **DEFERRED TO FINAL CLOSEOUT**. No full Backend852/Mobile410/
repository121/old Web/Android suite, pre/post root verify or marker advancement.
Final closeout must run actual make verify and all completed-phase regression,
then satisfy release-specific prerequisites before any formal whole-project claim.

FILES CHANGED: backend provider/config/usage/validation; existing graph node and
runtime wrappers; existing analysis/action/response prompts; service commit
diagnostics; new observability/budget modules and focused tests; evals/agent
dataset/harness/live checks/review/results; report/evidence checker scripts;
MASTER_PLAN/ARCHITECTURE and Phase11 docs/development-phase.json/.env.example;
.gitignore excludes api.txt. No frozen Skill, old Golden, historical acceptance,
Mobile, dependency, migration or endpoint change.

CURRENT OFFICIAL PHASE MARKER: completed_phase=9, completed_subphase=9H.

NEXT: stop here. Obtain real human review and separate authorization for ordinary
output/provenance reliability and Chinese safety response improvements; close the
quality gate before roadmap-approved release work. Evidence does not justify
starting RAG: reference retrieval succeeds; failures concern output adherence.
Phase10 remains optional/deferred and can be reconsidered after measured retrieval
failures. Do not automatically start Phase12 or a new imported-chat analysis feature.
