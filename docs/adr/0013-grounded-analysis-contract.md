# ADR 0013: Source-linked, analysis-only result

Status: accepted for Phase 3E (2026-09-27)

## Decision

Extend the existing `AnalysisResult` minimally with typed analysis points,
optional core provenance IDs and an insufficient-evidence marker. Assign F/I/U
IDs deterministically from the current FIU lists and use the loaded reference
aliases as knowledge IDs. Keep model instructions in a separate system prompt;
place user evidence and reference excerpts in distinct JSON fields in the
user role. Run Pydantic schema validation and project-owned ID/role checks
before writing `analysis_result`. The node writes no action, memory or final
answer and is absent from the high-risk graph path.

## Why and limits

Plain strings could not show which case evidence or source supported a major
reading. A small point schema allows deterministic validation that references
exist and that an inference/unknown is not marked as an observed fact. It also
lets the 30-case replay inspect relevant dimensions without comparing fixed
prose. Keeping `core_issue` as a string preserves the Phase 3A contract shape;
the new core ID fields add traceability without a citation engine.

Source IDs establish provenance structure, not semantic entailment: a model
could cite an existing F ID while writing an unrelated claim. Narrow wording
guards catch obvious action, refusal-bypass and certainty phrases but cannot
guarantee complete safety or analysis quality. The Mock replay is explicitly
not a live-model accuracy result. A later phase must evaluate real model
outputs and build ActionPlan/response generation separately.
