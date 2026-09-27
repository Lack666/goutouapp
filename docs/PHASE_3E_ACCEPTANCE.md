# Phase 3E acceptance — Relationship Analysis Runtime

Date: 2026-09-27

## PHASE / STATUS

Phase 3E — Relationship Analysis Runtime: **PASS** for engineering,
structured-output, offline replay and all active regression gates. This does
not assert live-model relationship analysis quality.

## RELATIONSHIP ANALYSIS NODE / GRAPH CHANGES

`relationship_analysis` calls the injected `LLMProvider.structured_output`
with `AnalysisResult`, validates the typed output and project-owned provenance
rules, then writes only `analysis_result`. Ordinary and boundary paths now
run `FIU → knowledge_router → load_references → relationship_analysis →
minimal_finalize`. High risk continues `safety_check → knowledge_router →
load_references → safety_finalize` and never enters analysis. The finalizer
remains fixed placeholder text; it does not generate advice.

## ANALYSIS RESULT / EVIDENCE GROUNDING / FIU INTEGRITY

`AnalysisResult` retains a core issue and adds optional core source IDs,
`insufficient_evidence`, and bounded typed points for observations,
dynamics, risks, constraints and uncertainties. Each point declares
`observed`, `tentative`, `framework` or `uncertainty`, a relevant dimension,
FIU IDs and/or reference aliases. Observed points can cite only F IDs;
tentative interpretations need F/I case evidence; framework points need a
loaded reference; uncertainty points need U IDs. The runtime rejects unknown
IDs, absent required provenance, missing user-evidence use when FIU is
present and unsupported boundary output. The analysis node cannot write or
change facts, inferences or unknowns. Narrow output checks also reject
obvious action directives, refusal-bypass wording and deterministic motive or
personality phrasing. Citation validity is mechanically checked; semantic
entailment of every sentence is **not** proven.

## KNOWLEDGE USE / SAFETY REGRESSION

Provider input contains actual bounded reference content, alias and
`truncated` flag in `reference_knowledge`, separate from `user_evidence` and
the current message. A test changes loaded content and confirms the provider
input changes. Reference injection text remains in the user data role; system
analysis rules are separate. Safety regression verifies high-risk graph runs
only `SafetyResult` on the provider, with no analysis call or result.

## GOLDEN ANALYSIS SUBSET / EVALUATOR / MOCK REPLAY VALIDATION

`evals/phase3e_subset.json` selects **30** Golden cases covering conflict,
imbalance, breakup/refusal, reconciliation, betrayal, online/chat evidence,
MBTI/attachment, practical constraints, reciprocity, identity and manipulation
boundaries. `scripts/check_analysis_replay.py`: **30/30 PASS** using Golden-
derived Mock safety/scenario/FIU and analysis fixtures, the actual router and
loader, and the structural evaluator. It checks supported required dimensions,
some structurally detectable forbidden patterns, FIU integrity, provenance,
reference use, safety bypass, and empty action/memory output. Mutation tests
detect a lost boundary and invalid core citation. This is a wiring/evaluator
replay, not independent model interpretation.

## LIVE MODEL VALIDATION

**NOT RUN / DEFERRED.** No live provider request or live analysis accuracy
claim is included in this stage.

## STANDALONE DEMO

`uv --cache-dir .cache/uv --no-managed-python run --locked python
apps/server/agent_demo.py` completed offline with Mock LLM. It printed
scenario, route, FIU, selected reference aliases and structured analysis;
it printed no full reference content and produced no ActionPlan or advice.

## TESTS / VALIDATION

- `8 passed` Phase 3E focused analysis tests, including grounding,
  reference/truncation input, prompt boundary, error/timeout, MBTI and safety.
- `186 passed` full backend tests; `86 passed` contract tests, `8 passed`
  runtime, `8 passed` semantic, `18 passed` knowledge, `32 passed` LLM,
  `7 passed` backend integration and `13 passed` repository tests.
- 81-case Golden routing evaluator and 81-case static validator passed.
  Frozen upstream validator, isolated Alembic cycle/check, repository secret
  boundary, Ruff check/format and `git diff --check` passed.
- `.\make.cmd verify`: **PASS** for all active Phase 0–2 and 3A–3E gates.

## ARCHITECTURE DECISIONS / FILES CHANGED

[ADR 0013](adr/0013-grounded-analysis-contract.md) records typed points,
F/I/U and reference IDs, separated prompt data and the analysis-only scope.
Key files: Agent contracts, `analysis_validation.py`, `prompts/analysis.py`,
`nodes.py`, `runtime.py`, the Phase 3E Golden subset/evaluator, focused tests,
verification script, demo, phase marker and runtime/architecture/analysis
documentation. The frozen `knowledge/goutoujunshi` tree and lockfile were not
changed. No new service or external dependency was introduced.

## KNOWN ISSUES / DEFERRED / NEXT

Structured provenance catches missing/invalid source IDs and some obvious
forbidden wording, but it cannot verify that every natural-language claim
follows from a cited source. Mock fixtures are oracle-derived, so live model
quality remains unknown. ActionPlan, reply text, contact timing, observation
windows, stop conditions, memory persistence, RAG, WebSocket, business HTTP
endpoints and mobile are deferred. The next phase is **Phase 3F — Action Plan
and Response Generation**; it was not started here.
