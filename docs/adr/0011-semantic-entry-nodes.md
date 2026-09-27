# ADR 0011: Safety-first semantic entry nodes

Date: 2026-09-27

Status: Accepted for Phase 3C

## Decision

Replace Phase 3B synthetic routing and scenario/analysis stubs with three
independent typed `LLMProvider.structured_output` calls. Run safety first;
high risk ends through `safety_finalize`. Normal and boundary routes continue
to scenario classification and FIU extraction, then a fixed minimal answer.
Use Phase 3A public result schemas without a version change. Keep prompts in
three source-labeled modules separate from node code. Encode current and recent
speaker-labeled messages as untrusted JSON under each system instruction.

## Why

The `SKILL_CONTRACT` requires risk precedence, source-limited facts, tentative
inferences with alternatives, visible unknowns and speaker preservation.
Separate nodes and scoped updates let tests detect route and FIU regressions
without introducing relationship advice, memory or knowledge loading. The
current risk-category strings follow the contract's examples; they do not
freeze a complete risk ontology.

## Evaluation boundary

The 24-case Golden subset uses exact structured comparisons and detects
scenario/route/provenance mismatches or expected inferences promoted to facts.
Offline replay output is derived from Golden expectations; it exercises the
runtime and evaluator but cannot measure model accuracy. Prompt placement and
Mock routing tests likewise cannot prove resistance to unseen prompt injection.
Live model accuracy and broader semantic evaluation remain explicit gaps.

## Consequences

The graph is still stateless between runs, has no DB writes or checkpoint,
and emits a fixed minimal response. Later phases must evaluate live semantic
performance, add knowledge routing and relationship reasoning, and design
memory persistence separately.
