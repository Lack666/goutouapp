# ADR 0012: Deterministic knowledge routing and frozen reference loading

Status: accepted for Phase 3D (2026-09-27)

## Decision

Route from the typed safety/route/scenario decisions to one stable alias, with
only narrow deterministic topic refinements. Put routing and loading in two
independent LangGraph nodes. Both high-risk and ordinary paths pass through
them; safety takes the first slot. Reuse the Phase 1B reference map and frozen
manifest as the only source registry. Resolve and hash-check selected files
inside the frozen tree, then return typed, explicitly truncated excerpts under
three bounded character limits. Public Agent results expose aliases only.

## Rationale and consequences

The source Skill calls for reading one to three relevant references after
scenario selection. The high-risk path has no scenario/FIU, so it must enter
the router directly from safety. A deterministic map can be evaluated against
all 81 Golden routing annotations without model variance. The split nodes
make wrong selection distinguishable from bad file loading. Hash verification
and path containment prevent user text or a changed local file from silently
becoming trusted knowledge. Character budgets are reproducible and require no
new dependency. Long documents may be truncated; `truncated=true` makes this
visible in internal state. The model does not consume these excerpts until a
later phase defines relationship reasoning and its evaluation.

This phase adds no RAG, embedding, vector store, model-based file picker,
knowledge-driven response generation, memory persistence or transport API.
