# Skill contract v1

This is a behavioral interpretation of the immutable upstream snapshot at
commit `6db7354a4002dc7c448a9c87ffdad8132570c9d3`. The upstream
`SKILL.md`, `documentation/`, `references/`, and `scripts/` remain authoritative
where this contract is silent. Traceability points to paths within
`upstream/goutoujunshi/`. Product and runtime behavior added here is tested by
the synthetic cases in `evals/golden_cases.jsonl`.

## Core result

Each ordinary response first acknowledges the user's feeling without
endorsing unproven interpretations, then separates known facts, plausible
inferences and material unknowns, weighs reciprocity, reliability, safety,
feasibility and opportunity cost, and gives one preferred action with reasons,
an observation window or stopping condition, and at most 1–3 essential
questions. The user retains the final decision. For a one-line reply request,
the first screen starts with one copyable, context-fitting message; timing,
tradeoff and positive/ambiguous/no-reply branches follow. A message should
serve one primary action.

Trace: `SKILL.md` sections 核心原则, 每次分析; `documentation/flows.md`.

## Intake and evidence

- If no current profile exists, ask a compact question about the user and each
  relevant person: self-reported MBTI and subjective 0–100 score if known,
  strengths/limitations, relationship stage, three recent events, investment,
  goal and emotion. Unknown is acceptable. Danger, acute distress, or an
  urgent reply takes priority over onboarding.
- A score is the user's subjective assessment, never a person's intrinsic
  worth or an inferred attraction/investment score. Never assign one for them.
- Treat visible text, sender, order, interval and emoji in supplied chat as
  observations. Treat user narration as a report; distinguish it from exact
  verifiable wording and from model inference. Do not infer offline behavior,
  tone, motive or consent from a screenshot or a label.
- For long or imported chats, lock the user/person speaker map from sender ID
  or user confirmation before relationship interpretation. If it is unclear,
  ask the smallest mapping question; never infer from screen side, gender,
  writing style or pronouns. Keep the mapping stable across chunks.
- Material contradictions remain explicit. Missing information stays unknown.
  Retrieved memory and user claims retain source labels.

Trace: `SKILL.md` sections 首次使用与紧急例外, 输入证据边界;
`references/practical/ChatLab聊天记录分析适配.md`.

## Scenario and knowledge route

The Phase 4 router must be deterministic and choose only 1–3 directly relevant
reference files for an ordinary request. The first file is the subject entry;
one or two additional files are allowed for a real evidence, risk or technique
need. A high-risk request goes to safety response before normal routing. All
paths below are relative to `upstream/goutoujunshi/`.

| Scenario | Primary reference |
| --- | --- |
| reply, opener, invitation | `references/practical/实战话术编排器：从一句回复到后续分支.md` |
| flirting, natural conversation | `references/practical/场景感、松弛感与社交校准：从接话到关系推进.md` |
| active expression or first date | `references/practical/主动表达、第一次见面与自然接触.md` |
| online relationship, screenshot, fraud signal | `references/knowledge/09-在线约会与数字关系.md` |
| chat import or trend | `references/practical/ChatLab聊天记录分析适配.md` |
| imbalance or exit | `references/practical/关系投入失衡：互惠判断、降级投入与退出决策.md` |
| conflict or repair | `references/knowledge/07-沟通冲突与修复.md` |
| attachment or anxiety | `references/knowledge/03-依恋理论与情绪调节.md` |
| MBTI | `references/knowledge/04-MBTI人格与匹配.md` |
| breakup, betrayal, reconciliation | `references/knowledge/15-分手背叛与关系修复.md` |
| consent or intimacy | `references/knowledge/08-同意边界性与亲密.md` |
| coercive tactics or PUA | `references/knowledge/05-PUA操控与伦理替代.md` |
| social-system mechanics | `references/knowledge/20-经典社交体系的机制、证据与风险边界.md` |
| marriage or family | `references/knowledge/11-婚姻家庭与生命周期.md` |
| money, chores, parenting | `references/knowledge/12-金钱家务育儿与双方家庭.md` |
| safety or crisis | `references/knowledge/17-中国法律安全与危机转介.md` |
| memory controls | `references/practical/长期记忆与关系档案.md` |

The upstream guide `references/practical/00-导读与使用分级.md` routes other
practical topics. Sources, evidence quality and further reading route to
knowledge files 01 and 19 only when needed. RAG is optional, later, and must
never replace this baseline or make `FEATURE_RAG=false` fail.

Trace: `SKILL.md` section 按需加载; `documentation/knowledge-base.md`.

## Safety precedence

The safety check is a program-visible node before profile loading and ordinary
analysis. High risk includes current or threatened violence, sexual coercion,
drugging, stalking, threats, extortion, impersonation, privacy exposure, fraud,
acute self-harm or harm to others, and controlling or abusive relationships.
Respond to immediate safety and trusted/local emergency support as relevant;
do not provide operational instructions for harm. A request to defeat a clear
refusal or continue unwanted contact must stop pursuit. A declined specific
time alone is not automatically a relationship-wide rejection.

Manipulative tactics such as negging, obedience tests, fabricated urgency,
jealousy induction, gaslighting and isolation cannot be offered as steps.
Translate a legitimate aim into honest, reversible, consent-based communication.
Do not diagnose or promise that a script will win someone over. Jurisdictional
legal or clinical detail is time-sensitive and requires current review.

Trace: `SKILL.md` sections 经典社交体系的使用边界, 安全边界;
`references/knowledge/05-PUA操控与伦理替代.md`,
`references/knowledge/17-中国法律安全与危机转介.md`.

## Relationship judgment

For ordinary interest or dating without a clear refusal, discomfort or danger,
help the user make at least one honest, low-pressure initiative and observe
feedback. Do not prescribe waiting by gender. In the Chinese heterosexual
dating context, the upstream's optional cultural calibration may raise male
initiative one step, but personal preference and real feedback override it;
it never raises physical contact. If the goal is exit, conflict resolution or
the pattern is persistently one-sided, do not force pursuit. Assess each person
separately before comparison. Labels such as MBTI, attachment, gender and
social-system stages generate questions, never mind-reading conclusions.

Trace: `SKILL.md` sections 核心原则, 每次分析; `documentation/product.md`.

## Long-term memory

Short-term state is the current conversation. Long-term memory is a separate,
limited, user/person-scoped store. No explicit consent means **zero writes**.
Consent can be inspected, paused, resumed and revoked; users can inspect,
delete one person/item, or delete all. After a successful write, show what
changed and how to undo. A failed write must not be reported as success.

Allowed scopes are `user`, `object`, `relationship`, `event`, and `hypothesis`.
User/object stable facts require explicit user information or user report.
Model inference can only be a sourced, confidence-marked, revisable
`hypothesis`; it must never become a stable fact automatically. Raw chat,
screenshots, exports and long summaries do not enter long-term memory. A
single event summary is at most 200 characters. The upstream bounds are 200
total rows, 20 events and 5 hypotheses per person, 20 undo operations, and
at most 8 recent events in compact context. The server implementation must
also bind every record to the authenticated user and the selected person.

Trace: `SKILL.md` section 长期记忆;
`references/practical/长期记忆与关系档案.md`;
`scripts/memory_store.py`.

## Chat import and analysis

V1 parses user-provided TXT, Markdown and JSON to `speaker`, `timestamp`,
`content`, with source and mapping metadata kept alongside the normalized
message. Count messages, lengths, conversation duration, initiations and reply
intervals in ordinary code. A model may extract events and explain possible
patterns only with evidence IDs, alternatives and uncertainty. ChatLab is an
optional upstream adapter, not a claim that this runtime can read or export
WeChat/QQ databases. A relation trend is not a validated love score.

Trace: `references/practical/ChatLab聊天记录分析适配.md`;
`documentation/flows.md`.

## Evaluation obligations

The dataset covers scenario and knowledge routing, safety-first behavior,
fact/inference separation, memory consent/isolation, response shape and
hallucination constraints. Phase 1 checks annotation quality and traceability.
After Phase 3, the same cases must be executed against the MockLLM runtime.
No high-risk case may execute ordinary relationship analysis first.
