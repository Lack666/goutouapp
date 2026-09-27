# Phase 3C acceptance — Safety, Scenario and FIU Semantic Nodes

Date: 2026-09-27

## PHASE / STATUS

Phase 3C — Safety, Scenario and FIU Semantic Nodes: **PASS for engineering
implementation and offline gates**. The runtime now requests typed semantic
results from the injected provider. Live model semantic accuracy was not
tested and is not included in this PASS.

## SAFETY NODE / SCENARIO NODE / FIU NODE

`safety_check` reads the current message and recent speaker-labeled context,
calls `LLMProvider.structured_output(SafetyResult)`, and writes only `safety`
and `route`. High risk takes the safety branch; explicit refusal or consent
withdrawal without higher danger takes `boundary`. Synthetic metadata no
longer controls routing. `classify_scenario` requests the existing 19-label
`ScenarioResult` and writes only `scenario`. `extract_fiu` requests
`FactExtractionResult` and writes distinct facts, inferences and unknowns.
Inference alternatives remain required; unsupported fact source labels fail
closed. All provider responses are schema-validated before entering state.

## GRAPH CHANGES / PROMPTS

The graph now runs `normalize_input → safety_check → classify_scenario →
extract_fiu → minimal_finalize` on ordinary/boundary input. High risk goes
directly from safety to `safety_finalize`, skipping scenario and FIU. The
Phase 3B synthetic flag, constant scenario and minimal synthetic analysis
were removed. Separate version-1 safety/scenario/FIU system prompts cite
`SKILL_CONTRACT.md`, receive user content as JSON data with role/speaker
labels, and do not request hidden chain-of-thought. No relationship strategy,
knowledge, memory or RAG prompt was added.

## MINIMAL PAIRS / GOLDEN SEMANTIC SUBSET / EVALUATOR

`evals/phase3c_subset.json` selects **24** of the 81 Golden cases, including
all six minimal pairs A–F. Tests check clear refusal vs scheduling, quoted
statement vs user guess, speaker direction, explicit vs absent memory consent,
ordinary conflict vs violence/coercion, and MBTI label vs observed reply.
Pair D tests recognition of consent language and confirms zero memory
candidates; no memory write is implemented.

The deterministic evaluator compares scenario, safety, route, canonical FIU
claims, fact provenance, inference alternatives, unknowns and forbidden
promotion. Mutation tests prove it detects route drift and an inference
inserted into facts. Its Mock replay data are **derived from Golden expected
annotations**, so a passing replay verifies wiring and evaluator consistency,
not independent model understanding. The 81-case validator remains a static
dataset validation, not full runtime evaluation.

## MOCK TESTS / LIVE MODEL VALIDATION / FAILURE HANDLING

Offline Mock tests cover eight safety categories, boundary routes, typed node
outputs, prompt placement under adversarial user text, schema failures at
each of the three semantic stages, provider timeout, graph scope and run
isolation. Invalid structured output returns `structured_output_failure`;
timeout returns `dependency_failure`, without raw provider content.

**LIVE SEMANTIC MODEL VALIDATION: NOT RUN / DEFERRED.** No real API key or
external model request was used. Prompt injection resistance and semantic
accuracy on unseen inputs remain unverified by the Mock/replay gates.

## VALIDATION

Commands ran from the repository root on Windows:

- `uv --cache-dir .cache/uv --no-managed-python run --locked pytest -q apps/server/tests/test_agent_semantic.py apps/server/tests/test_agent_runtime.py apps/server/tests/test_agent_contracts.py`
  — **102 passed**.
- `uv --cache-dir .cache/uv --no-managed-python run --offline --locked python apps/server/agent_demo.py`
  — PASS; emitted completed `AgentResult` JSON with scenario, safety and FIU.
- `.\make.cmd verify` — **PASS**: 13 repository/contract tests, frozen upstream
  validator, isolated Alembic upgrade/downgrade/upgrade/check, 32 LLM tests,
  7 backend smoke tests, 86 Agent contract tests, 8 runtime tests, 8 semantic
  tests including the 24-case replay, full backend suite (**160 passed**),
  81-case static Golden validator, repository secret check, Ruff check and
  format check.
- `git diff --check` and staged `git diff --cached --check` — PASS after
  staging the requested repository-wide commit.

## ARCHITECTURE DECISIONS / FILES CHANGED

[ADR 0011](adr/0011-semantic-entry-nodes.md) records safety precedence,
prompt separation and the replay/live distinction. Changed Agent graph/nodes,
added `app/agent/prompts/`, a 24-case selection and evaluator, semantic tests,
and updated the demo, verifier, phase marker, master plan, architecture and
Agent runtime documentation. The root dependency set and database schema did
not change in Phase 3C. The user requested a Git commit of all current work;
prior Phase 1B–3B uncommitted work is included after final staged review.

## KNOWN ISSUES / DEFERRED / NEXT

No failing engineering gate. Valid-looking model claims can still be wrong;
the fact-source check cannot independently verify truth or speaker attribution.
Live accuracy, broader adversarial evaluation, relationship reasoning,
knowledge loading, memory persistence, durable checkpointing, streaming/API
transport and mobile remain deferred.

Next authorized stage: Phase 3D — Knowledge Router and Reference Loading Runtime.
