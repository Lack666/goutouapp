# ADR 0003: synthetic contract evaluation before implementation

Status: accepted, Phase 1.

Golden Cases are synthetic, anonymous inputs with expected scenario, safety
level, 1–3 reference paths for ordinary cases, response assertions, and memory
write expectation. High-risk cases require the safety path before ordinary
analysis. The Phase 1 evaluator validates annotations and source references;
it does not claim to test a runtime that has not been built. Phase 3 and 4
will execute these same cases against Agent nodes and outputs.

The fixed state fields match the user-specified minimum. Provenance and
`person_id` are planned additions, not substitutions.
