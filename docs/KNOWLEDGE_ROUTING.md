# Knowledge routing and loading (Phase 3D)

## Runtime flow

`safety_check` runs before all ordinary analysis. High risk goes directly to
`knowledge_router → load_references → safety_finalize`; normal and boundary
requests go through `classify_scenario → extract_fiu` first. The router reads
only safety, route, scenario and the current message. The loader reads only
selected aliases. Neither node creates relationship advice or memory writes.

## Deterministic router

`route_knowledge` maps the 19 Phase 1B scenarios to app-owned aliases. A small,
explicit set of topic cues refines broad labels: invitation wording, attachment
language and research evidence. High risk always selects `safety` first,
regardless of the message or missing scenario/FIU. Boundary generally selects
`consent`; a breakup/refusal scenario keeps `breakup` first to match the Golden
refusal pair. The function selects one primary reference today and enforces the
contract's one-to-three maximum. It makes no model, search or vector call.

## Registry and trusted resolution

`ReferenceRegistry` is built from `evals/reference_map.json` and
`knowledge/upstream-manifest.json`; aliases are unique and their canonical
relative source IDs must be manifest entries under
`knowledge/goutoujunshi/references/{knowledge,practical}`. Entries record
alias, source ID, title, topic/category, source type and frozen SHA-256. A user
message cannot become an alias or filesystem path. Registry paths reject
absolute paths, `..`, noncanonical separators, duplicate IDs and files outside
the frozen tree; resolved paths are checked again on every read to block
symlink escapes or files removed after startup. The selected file's hash is
checked before UTF-8 decoding. The separate `validate_integrity()` gate reads
all 22 registered files and detects any frozen-source drift.

## Loader and context budget

`load_references` preserves router order and returns typed `LoadedReference`
objects with alias, source ID, title, category, excerpt, original character
length and explicit `truncated`. Defaults: maximum three documents, 4,000
characters per document and 9,000 characters total. The first selected
reference receives the first available budget, so the safety primary cannot
be displaced by ordinary material. If a later selected document has no
remaining budget, loading fails rather than silently omitting it. Invalid
budgets, alias/count errors, missing files, path escapes, decode/read errors
and hash mismatches become `knowledge_failure`; `AgentFailure` gives fixed
public text without local paths or raw exceptions.

`AgentState.retrieved_context` holds the typed excerpts privately. The public
`AgentResult.knowledge` exposes only selected stable aliases, primary alias,
reason summary and count limit. The minimal finalizers do not reason over or
print source text.

## Golden and runtime validation

`scripts/check_knowledge_routing.py` evaluates all 81 Golden cases using their
expected scenario, safety and route fields as **fixtures**. For each case it
checks required primary, selected subset of `allowed`, no `forbidden`, maximum
count, real registry aliases and safety-first order. It accepts alternative
allowed combinations and does not compare exact alias lists. Separate Mock LLM
graph tests cover ordinary, boundary, safety, personality, conflict, breakup,
online and chat import paths and inspect actual loaded context. The 81-case
router PASS is not an end-to-end live model accuracy claim.

RAG, embeddings, BM25, vector stores and relationship advice remain deferred.
