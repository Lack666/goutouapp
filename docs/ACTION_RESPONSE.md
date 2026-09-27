# Action planning and response generation (Phase 3F)

Ordinary and boundary input follows `relationship_analysis → action_planner →
response_generator`. High-risk input follows the separate safety path and
never calls either node. The action node writes only `action_plan`; the
response node writes only `final_answer`. Neither may alter FIU or analysis.

The planner uses scenario, route, bounded FIU statements, the analysis summary
and enumerated points `A1..An`, reference aliases and optional small profile
read models. It does not receive loaded reference text. `ActionPlan` contains
`contact_policy`, a recommendation, supporting analysis IDs, optional short
message/observation window and stop conditions. The policy distinguishes a
copyable reply, invitation, observation, pause and explicit stop of contact.
The validator requires a structured stop condition for continuing observation,
pause and stop-contact plans. A simple reply or invitation may leave that field
empty; the advice must still remain low pressure and stoppable under
`SKILL_CONTRACT.md` §7.4. This was clarified during the Phase 3G preflight.
The validator checks that IDs exist, refusal routes stop contact and contain no
message, scheduling conflicts do not automatically become a permanent stop,
and message/window fields match the policy. Narrow phrase guards reject
obvious coercion, deception, boundary bypass and unsupported certainty.

The response node receives bounded scenario, FIU, analysis summary and the
validated action. Its typed `ResponseResult` has `final_answer` and a repeated
contact policy. Validation requires policy agreement, exact suggested wording
in message cases, a copyable first line for reply requests, and the approved
recommendation in no-message cases. It rejects obvious contact drift after
refusal/pause/observation, internal provenance IDs, secret-shaped text,
fabricated tool claims and unsupported certainty. The safety response remains
independent and fixed. Validation failures return `AgentFailure` with a stable
code and no raw provider text.

`evals/phase3f_subset.json` selects 38 Golden cases across reply, invitation,
flirt, conflict, imbalance, breakup, repair, betrayal, online/chat evidence,
MBTI, manipulation, practical constraints and all six minimal pairs. The
evaluator checks route, structural grounding, required fields, specific
behavior cues, refusal and response consistency. Mock outputs are derived from
Golden expectations, so replay demonstrates graph and evaluator behavior,
**not** independent semantic accuracy. Regex and ID checks cannot prove every
claim is grounded or detect every harmful paraphrase. Live-model validation
was not run. Long-term memory, RAG and transport are deferred.
