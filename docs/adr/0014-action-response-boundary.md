# ADR 0014: Separate grounded action and user response

Status: accepted for Phase 3F (2026-09-27)

## Decision

Keep action planning and response wording in separate LangGraph nodes after
validated relationship analysis. Both use strict structured output from the
injected `LLMProvider` and project-owned validators. Action cites enumerated
analysis points and declares a contact policy; response must follow that plan.
Only the analysis node receives loaded reference excerpts. The high-risk path
continues through the independent safety finalizer.

## Rationale and limits

The separate contract makes a refusal or a one-line reply testable before
user-facing text is accepted. Bounded prompts avoid copying the full knowledge
corpus into later nodes, and exact state write scopes prevent advice from
changing the evidence. The validator deliberately handles detectable errors;
provenance IDs do not prove semantic entailment and phrase guards cannot cover
all paraphrases. Golden-derived Mock replay establishes wiring, not live-model
quality. No persistent memory or transport behavior is introduced here.
