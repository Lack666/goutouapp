# Agent observability

`app.observability` supplies context-local Run/Node/Provider events. Actual node
wrappers observe execution without adding nodes or changing read/write scopes.
Runtime run/stream wrappers emit graph outcome separately from PostgreSQL
`persistence_outcome`; a successful graph does not imply a successful commit.
SSE answer persistence can complete before optional Memory work; cancellation of
the latter is distinguishable from the already committed answer.

Events include UTC time, run UUID (no owner identity), node name, start/end,
duration, status, bounded error category, safety routing category and graph/prompt
versions. Provider events include operation/schema name, configured/returned
model, elapsed time, TTFT for nonempty streaming content, normalized usage,
cache-hit/miss tokens, conservative cost estimate and price version. Chat/structured
TTFT is unknown because the adapter receives a complete HTTP response. Provider
duration includes network and local decode/validation, not an invented vendor-only
server time. Node duration includes its validation and provider calls.

The process-local buffer retains at most4096 events for24 hours, expires on
snapshot and insertion, and disappears on process exit. No public trace endpoint
is introduced. `TRACES.snapshot()` is for trusted in-process operators/tests.
This is bounded development observability, not a durable production collector.
Evaluation JSON exports are immutable local synthetic artifacts; retain them for
this acceptance, review/delete locally after90 days, and do not deploy a synthetic
export path as production telemetry. No scheduler or production retention is claimed.

No event serializes messages, state, references, Memory content, keys, headers,
authorization, vendor error text or hidden reasoning. Schema diagnostics retain
only allowlisted Pydantic error types, never locations/inputs/messages. Synthetic
evaluation exports may separately contain visible model JSON for the fixed public
synthetic dataset. That is evaluation evidence, not application tracing. Hidden
vendor reasoning is discarded before either route. Diagnostic sink failures are
swallowed; business exceptions and cancellation propagate through existing guards.

Failure, generator close and task cancellation produce terminal diagnostics.
The process can be killed before a terminal event; missing events remain unknown,
not completed. Cross-process durable status remains the existing PostgreSQL
AgentRun. Source/prompt fingerprints bind reproducible evaluation exports.

Phase11 contextual output review adds only content-free `content_safety_review`
allow/block events. Its LLMProvider.chat calls use the existing usage/cost/provider
tracing and budget; they must be counted in addition to generation requests.
Invalid decisions and transport errors have no successful review event and cannot
be scored as correctly classified negative cases. Candidate text, field-level intent
decisions and payload digests are not added to application diagnostics. Fixed synthetic
evaluation exports retain visible JSON decisions separately; no reasoning is requested.

Phase11Q adds content-free `safety_presentation` events (policy version and
candidate_replaced/publication_rejected) and `response_composition` events
(changed boolean, retries=0). No discarded candidate or copied Plan text enters
application diagnostics. Prompt version is phase11q-core-safety-reliability-v1;
exact source manifests distinguish the changed behavior from historical runs.
The one-pass q11 evaluator separately checkpoints each normalized synthetic
visible response/usage before formal node validation, including invalid Schema
results. Journals and claims prevent a lost aggregate from justifying paid retries.
These files are synthetic evaluation evidence, not a new production log or data API.
