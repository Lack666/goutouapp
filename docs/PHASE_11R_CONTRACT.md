# Phase 11R semantic contract v1

Contract-first decision, 2026-10-28, baseline `7dffd45`. This supplements
[SKILL_CONTRACT](SKILL_CONTRACT.md) sections 3, 4, 7 and 9, using the frozen U1–U7
catalog in [the audit](PHASE_11_SKILL_SEMANTIC_AUDIT.md). It does not update upstream.
Test expectations added in Phase11R follow this decision; historical oracles remain unchanged.

## Scope and compatibility

No public Pydantic field, enum, REST DTO, database migration or schema_version is changed.
SafetyResult.risk_categories already accepts strings; the following **versioned category
vocabulary** is a behavioral contract change, not a silent new schema. Readers of old
results must retain unknown categories and must never infer contact permission from them.
`explicit_refusal` remains the compatibility boundary category. `refusal_dating`,
`refusal_private`, `refusal_all`, `refusal_unknown` refine it. Unscoped legacy
explicit_refusal and consent_withdrawal retain conservative unknown/no-outreach behavior.
Conflicting scopes use the strictest interpretation; a scope cannot downgrade high risk.
`user_exit` describes the user's own choice; `schedule_only` does not erase a refusal.
`necessary_classroom` / `necessary_work` describe established shared obligations,
not authorization to initiate contact. They permit only controlled explanatory text
under dating/private scopes. Never synthesize these categories from language/locale alone.

The input Safety classifier identifies current applicable boundaries from user-authored
reports and history. Attributed old/hypothetical examples are not current consent.
Boundaries apply to the person and behavior actually described; a changed schedule is
not changed romantic consent. Only freely explicit new evidence from that same person
can change a prior refusal. Ambiguous identity, timing, conflicting evidence, or scope
requires clarification/no outreach; assistant claims cannot manufacture permission.
The runtime does not infer dates, expiry, or all-target permission from silence.

| Situation | Forbidden | Allowed / conservative handling | Route |
| --- | --- | --- | --- |
| Refused dating/pursuit | New invitations, private romantic pursuit, proxy/channel bypass | Respect the refusal, normal public courtesy; describe necessary course/work communication only if shared obligation established, no extra message or meeting | boundary |
| Refused private contact | Personal messages/calls, pursuit, invented practical pretexts | Necessary brief public/official practical communication only where actually established; no unsolicited private draft | boundary |
| Refused all proactive contact | All proactive target outreach, including proxy/final explanation or practical pretext | Self-care, seek independent trusted support; clarify formal obligations through appropriate independent process, no target-contact instructions | boundary |
| Refused a time only | Repeated pressure at that time, invented consent | One honest low-pressure new arrangement when no other boundary; do not clear historical refusal | ordinary unless other boundary/risk |
| User chooses exit | Forcing continued reply/pursuit, punitive manipulation | Stop private contact or pause at user's choice, optional self-care; no message required | ordinary unless another boundary/risk |
| Necessary class/work interaction | Extra private exchanges, one-to-one date pretexts, reopening pursuit | Brief task-limited interaction when unavoidable, respect avoidance/discomfort; no proactive new outreach authorization | boundary when refusal exists |
| Unknown refusal scope | Assuming permission or less restrictive scope | No outreach; ask only clarification that changes safe advice | boundary |

U1/U4 require stopping the refused direction; U5 section III.4 explicitly allows necessary
class/work/co-parenting practical communication; U6 makes consent behavior-specific.
The finite category vocabulary, controlled templates, fail-closed policy checks and
approval digests are new App engineering rules implementing those principles.

## Node responsibilities and enforcement

SafetyResult is input risk/boundary classification; high risk always takes safety route.
Route is the execution path, Scenario only the task/reference taxonomy. `boundary` is
never a valid Scenario. Node prompts reference actual Pydantic schemas and enums.
ActionPlan describes one controlled next step; stop_contact on boundary means stop
the refused direction. It never authorizes a new target message. Boundary plans are
runtime-owned text; practical-communication explanation is limited to dating/private
scope plus an established obligation, never generated outreach or an invitation.
User-chosen exit may use stop_contact on ordinary; a reply topic cannot force contact.

CONTACT cues become a trigger for contextual contact-effect classification, not a
verdict. Full candidate and context must be reviewed; capability denial, rejected quote,
conditions describing when to stop, and returning attention to one's life are not
endorsed outreach. No blanket negation/quotation exemption. Any actual target outreach
under observe/pause, or prohibited outreach under boundary, remains program-blocked
even if a generic model verdict says allow. The exact runtime-owned boundary template
can be deterministically verified instead of model-authorized. Invalid/unclear review
fails closed. Approvals bind complete candidate, input/history, safety/scope, IDs and
policy version; changes require validation again. High-risk final equality guards,
strict schemas and source ID checks remain in force.

## Memory authorization

Natural-language discussion/quotation/negation is not a trusted command. Use a closed,
anchored explicit command grammar for current user controls and save envelopes;
unsupported language produces no mutation and can use the existing signed control UI.
Saving still requires actual consent, source-grounded bounded candidate, same Owner
and selected object, and all service/storage barriers. Pause/resume/revoke/delete
must also be explicit commands; destructive confirmation requirements do not change.
User-authored text cannot select another Owner or escape the selected relationship.
Real SQL/signed-service canaries, not only mock classification, must establish zero
side effects. A reproduced unauthorized state change is P0 regardless of row count.

## Acceptance and limits

Freeze new independently named SA01–SA18 cases after this contract, keep all old
failures/ratings/Golden83 intact. Offline replay first; then one finite paid batch,
no generation retries following failure: maximum80 calls, 1.2M conservative reserved
tokens, actual usage160k (checked before next call), CNY3. Preserve actual failures.
Only affected module tests and necessary integration checks; no full Root Verify or
Android. Phase11R TARGETED PASS requires evidence for core semantic fixes and no
safety/authority regression. Otherwise PARTIAL / REMAINING BLOCKERS. Neither outcome
changes Phase11 QUALITY FAIL, formal9/9H marker, Phase10 DEFERRED, or starts ICA/Phase12.
