# Relationship analysis runtime (Phase 3E)

## Inputs and graph position

`relationship_analysis` runs only after `extract_fiu → knowledge_router →
load_references` on ordinary and boundary routes. It reads scenario, safety,
route, current message, FIU lists, optional profiles and the actual typed
`LoadedReference` excerpts. High risk bypasses it. No profile reader or memory
store is invoked by this phase; optional profiles enter only if a trusted
caller has already supplied them to internal state.

The analysis prompt places immutable rules in the system role. The user role
contains JSON with separate `user_evidence` (F1/I1/U1 IDs and provenance),
`reference_knowledge` (alias, excerpt and `truncated` state), user message and
optional profiles. Both user text and reference text are data. A changed
reference excerpt changes the provider input; tests confirm this. A truncated
excerpt is explicitly marked, never represented as a complete source.

## Result, grounding and provenance

`LLMProvider.structured_output(AnalysisResult)` is the only model output path.
The core issue cites FIU or reference IDs. Each typed `AnalysisPoint` has a
statement, dimension, role (`observed`, `tentative`, `framework`,
`uncertainty`) and FIU/reference IDs. `observed` points can cite only F IDs;
tentative points need F/I case evidence; framework points need an actual loaded
alias; uncertainty points need U IDs. The runtime checks every ID against the
current FIU and loaded references. It rejects an analysis with no points,
no reference use or no user-evidence point when FIU exists. Boundary analysis
must include a boundary dimension. FIU lists are read-only to this node.

The source contract favors reciprocity, boundaries, communication, repeated
behavior, practical constraints, opportunity cost and uncertainty when
relevant. A single event or MBTI/attachment label cannot become a diagnosis.
Knowledge is an interpretive lens, not evidence about a particular person.
If evidence is thin, `insufficient_evidence` and uncertainties can remain
visible. A narrow output check also rejects obvious next-step imperatives,
refusal-bypass wording and unsupported certainty phrases. These mechanical
checks cannot prove that a cited sentence is semantically entailed by its
source or catch every harmful paraphrase; live semantic evaluation is deferred.

## Phase boundary and evaluation

The node writes only `analysis_result`. `minimal_finalize` returns fixed
placeholder text; it does not turn analysis into advice. `action` stays `None`,
memory candidates remain empty and no DB write occurs. Reply scripts,
contact timing, observation windows, stop conditions and ActionPlan belong to
Phase 3F or later.

`scripts/check_analysis_replay.py` runs 30 Golden cases through Mock semantic
fixtures, the actual router/loader, analysis node and a structural evaluator.
It uses existing required/forbidden behavior IDs where they map to observable
analysis dimensions and checks provenance, FIU integrity, reference IDs,
safety bypass and no action/memory. Mutation tests show it catches removed
boundary recognition and broken citations. The fixtures are derived from
Golden expectations; replay PASS is not live-model quality. No live model
request was made in this phase.
