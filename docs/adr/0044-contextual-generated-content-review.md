# ADR0044 — Contextual review of generated actions and responses

Accepted 2026-10-27 for the bounded Phase11 communication-03 repair.

## Problem and decision

SafetyResult classifies input risk and controls routing. It does not certify later
generated text. The ActionPlan validator mixed deterministic structure validation
with a substring-based harmful-content verdict. Its optional deception suffix
allowed bare 编造 to match; an honest expression without fabricated excuses failed.
Adding negation exceptions cannot reliably handle scope, attribution or mixed advice.

Keep the formal Pydantic contracts, input safety gate and all deterministic
contact/provenance/response checks unchanged. Run those checks before content review.
Retain and extend HARMFUL_CUES as review signals; remove NO_FAKE_REASON entirely.
Inspect all action prose fields, including observation windows and stop conditions,
and independently inspect the final response. Never delete dangerous text from the
candidate or treat the presence of 不 or quotation marks as permission.

After a signal, make exactly one LLMProvider.chat call with the structured plan,
input SafetyResult/route, facts/unknowns, current request and six recent scoped
messages. All JSON is untrusted data. Request field-level action intent and violation
categories from the existing safety contract, without reasoning or a rewrite.
This private JSON protocol is strictly parsed in content_safety.py; no new or changed
Pydantic/public schema is introduced. Only complete, unique, unambiguously safe field
decisions with empty violations lists permit the candidate. Harm, ambiguity, invalid
data and transport/truncation failures close the run. Never regenerate on rejection.

Approval is an internal immutable digest bound to the entire candidate and context;
it cannot approve a modified plan, later response or changed input. Nodes re-run
deterministic validation with that approval. It is not stored in AgentState, a public
result, Memory or a database. The only new read scopes are existing input safety and
scoped messages in the two output nodes. No owner/resource ID or additional database
lookup is sent to the reviewer. High-risk input still skips both output nodes.

## Tradeoffs and stopping boundary

A flagged output node costs one additional call; a workflow adds at most two. A
reviewer outage may reject safe content. The same provider supplies generation and
review, so this is a separate decision, not independent-model assurance. Lexical
trigger coverage remains finite; harmful paraphrases without signals may evade this
layer. This is an existing class of coverage limit, not a claim of exhaustive safety.
CONTACT_CUES and certainty guards retain their separate conservative lexical limits.

If wider evaluation exposes misses or recurring ambiguity, the next separately
authorized design is an always-on action-intent verifier with calibrated coverage
and an independently evaluated reviewer. Do not add new sentence exceptions here.
No new infrastructure is needed. This task stops after the fixed live batch and its
offline regression/report; Phase11 overall quality and final regressions remain open.
