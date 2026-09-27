# Phase 3F acceptance — Action Plan and Response Generation

Date: 2026-09-27

## PHASE / STATUS

**Phase 3F — Action Plan and Response Generation: PASS** for the implemented
code, focused and regression tests, documentation, standalone Mock demo and
offline evaluator. Live-model advice quality is not included in this PASS.

## ACTION PLANNER / ACTION VALIDATION

`action_planner` independently requests a typed `ActionPlan` through
`LLMProvider.structured_output` and writes only `action_plan`. The contract
retains the recommendation, optional short message, observation window and
stop conditions; it adds `contact_policy` and supporting analysis point IDs.
The node reads bounded FIU, the validated analysis, selected aliases and
optional profiles, without reloading the reference corpus. Validation checks
point IDs, policy/field agreement, refusal handling, stop conditions and
detectable deception, manipulation or unsupported certainty. Invalid output
fails closed to the stable `structured_output_failure` result.

## RESPONSE GENERATOR / GRAPH CHANGES

`response_generator` independently requests typed `ResponseResult` and writes
only `final_answer`. The ordinary/boundary graph is now `normalize_input →
safety_check → classify_scenario → extract_fiu → knowledge_router →
load_references → relationship_analysis → action_planner → response_generator
→ END`. The high-risk graph remains `safety_check → knowledge_router →
load_references → safety_finalize → END`; no analysis, action or ordinary
response node runs there.

## ACTION / ANALYSIS GROUNDING / UNCERTAINTY

Action IDs must refer to current `AnalysisResult` points; the validator
rejects unknown/duplicate IDs. Prompt and guards retain FIU unknowns and
analysis uncertainty, including a regression for an invented motive after a
late reply. These checks establish structural traceability, not semantic
entailment of every recommendation.

## BOUNDARY / REFUSAL / MANIPULATION SAFETY

The boundary route requires `stop_contact`, no message suggestion and a
recommendation that respects/stops contact. The scheduling-conflict half of
minimal pair A stays ordinary and cannot be assigned `stop_contact` by this
validator. Tests reject contact through another platform, impersonation,
invented excuses and obvious pressure or manipulation language. Safety
finalization remains independent.

## MESSAGE SUGGESTION / OBSERVATION / STOP CONDITIONS

Reply and invitation plans carry short, direct wording; observation and pause
plans carry no message. Reply answers begin with the exact suggestion. Observe
plans require a bounded window, and all accepted plans require at least one
stop condition. Golden fixtures also exercise practical constraints, repair,
reciprocity, speaker mapping and a case without an unrequested message.

## ACTION / RESPONSE CONSISTENCY

`ResponseResult.contact_policy` must match the plan. The answer must contain
the approved message or, for no-message policies, the approved recommendation.
Refusal, observation and pause answers reject detectable new contact steps.
Internal provenance IDs, secret-shaped text, fabricated tool claims and
obvious unsupported certainty are rejected before the public result is built.

## GOLDEN 3F SUBSET / EVALUATOR / MOCK REPLAY VALIDATION

`evals/phase3f_subset.json` selects **38** cases across reply, invitation,
flirt, conflict, imbalance, breakup, reconciliation, betrayal, online/chat,
MBTI, manipulation, long-term and family constraints, plus all six minimal
pairs. `scripts/check_action_response_replay.py`: **38/38 PASS**. Its
deterministic evaluator checks route and earlier analysis gates, policy,
grounding IDs, required message/window/stop fields, selected behavior cues,
refusal and response consistency. Mutation tests detect refusal bypass and a
missing copyable reply. Outputs are Golden-derived Mock fixtures and prove
wiring/evaluator behavior only.

## LIVE MODEL VALIDATION / SAFETY REGRESSION

**NOT RUN / DEFERRED** for a live model. Phase 3E 30-case analysis replay,
Phase 3D 81-case routing replay, Phase 3C semantic tests and high-risk graph
bypass tests passed. No claim is made that an unseen model will reliably
understand refusal, factual grounding or all harmful paraphrases.

## STANDALONE DEMO

`uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env
python apps/server/agent_demo.py` completed without a real model or network.
It printed scenario `reply`, route `ordinary`, selected alias `reply`, FIU,
analysis, a typed reply plan and a copyable `final_answer`; it printed no full
references, secrets, prompts or hidden reasoning.

## TESTS / VALIDATION

- `16 passed` Phase 3F focused tests; `202 passed` full backend tests.
- `86 passed` contracts, `8 passed` runtime, `8 passed` semantics,
  `18 passed` knowledge, `8 passed` analysis, `32 passed` LLM and
  `7 passed` backend integration; `13 passed` repository tests.
- 38-case 3F replay, 30-case 3E replay, 81-case routing and 81-case static
  validator passed. Frozen upstream validation, isolated Alembic cycle/check,
  secret boundary, Ruff check/format and `git diff --check` passed.
- `.\make.cmd verify`: **PASS** for every active Phase 0–2 and 3A–3F gate.

## ARCHITECTURE DECISIONS / FILES CHANGED

[ADR 0014](adr/0014-action-response-boundary.md) records the two-node
contract, bounded prompt inputs, model/validator split and safety bypass.
Implementation: `contracts.py`, `action_validation.py`, separate action and
response prompts, `nodes.py`, `runtime.py`, demo, focused and regression tests,
3F subset/evaluator/replay script, phase marker, verifier and runtime,
architecture and plan docs. The frozen upstream tree and lockfile were not
changed.

## KNOWN ISSUES / DEFERRED / NEXT

Regex and ID checks catch only detectable errors. An existing analysis ID may
be cited for an unrelated sentence; a model could add a subtle new fact or
harmful paraphrase that the validator misses. Golden-derived fixtures do not
measure live-model quality. Memory persistence, RAG, WebSocket, business API,
authentication and mobile are deferred. **Next by separate instruction:
Phase 3G — Memory Candidate and Persistence Runtime.** No Phase 3G work was
started.
