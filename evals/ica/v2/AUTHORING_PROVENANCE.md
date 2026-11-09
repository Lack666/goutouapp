# ICA v2 independent synthetic authoring

Dataset: `ica-v2-quote-v2-independent`; message input schema: `ica-case-v1`;
intended model evidence protocol: `quote-v2`; authoring date: 2026-11-09.

These are invented conversations with deterministic synthetic UUIDs. They contain
no private chats, account credentials, actual people or copied model answers.
The case author is a delegated coding agent, not an independent human reviewer.
The semantic expectations remain **PENDING human review**. This authoring task
does not establish model quality, user value, blind custody or paid-run approval.
External Provider calls during authoring: **0**.

## Source exposure and independence boundary

The author read the project rules, current transport-independent contracts and
frozen Skill. The manifest records SHA256 for each source read:

- `AGENTS.md`, `docs/MASTER_PLAN.md`, `docs/ARCHITECTURE.md`, `docs/SKILL_CONTRACT.md`.
- `docs/ICA_B0_CONTRACT.md`, `docs/ICA_BQ_EVAL_CONTRACT.md`.
- `knowledge/goutoujunshi/SKILL.md`.
- `references/knowledge/07-沟通冲突与修复.md`: misunderstanding, concrete requests,
  separated interactions, clarification and repair.
- `references/knowledge/09-在线约会与数字关系.md`: needs versus response, message
  length/delay limitations, media gaps, digital boundaries and source limits.
- `references/knowledge/17-中国法律安全与危机转介.md`: role-aware current danger,
  coercion, stalking and historical/quoted material. The cases do not freeze
  legal advice or hotline numbers.
- `references/practical/ChatLab聊天记录分析适配.md`: stable speaker mapping,
  selected-source evidence, source-limited trends and no inferred Memory writes.
- `apps/server/app/agent/imported_contracts.py`, `imported_quote.py`, relevant
  scope/validation sections of `imported_analysis.py`, and
  `apps/server/app/chat_import/analysis_scope.py`.
- `evals/ica/runner.py`: input field names, `case_to_contexts`, evaluation field
  accesses, and public module declarations. The author did not call `load_cases`.
- The local `ponytail` skill guided the bounded change; it supplied no stories.

The author did **not** open `evals/ica/v1`, `docs/evidence/ica-bq`, old model
outputs, human scoring records, or quote-migration replay material. Project
contracts and the top of MASTER_PLAN contain aggregate historical status and
the previous experiment design; that documentary exposure is disclosed and is
not hidden. The new stories and oracles were written from the Skill/contracts,
without old case text or answer text. Repository accessibility still means this
is not independently held-out human custody. If these cases later inform prompt
or behavior tuning, they must be reclassified as development data for subsequent
quality acceptance.

The frozen upstream knowledge is preserved without edits, with its original MIT
license and attribution. Its project-recorded upstream commit is
`6db7354a4002dc7c448a9c87ffdad8132570c9d3`.

## Split and denominators

| Split | Family | Count | Semantic design |
| --- | --- | ---: | --- |
| development | emotional_mismatch | 4 | explicit needs, hard negatives, Unicode and repeated quote |
| development | recurring_conflict | 3 | separated episodes, cross-midnight negative, repeated body/UUID |
| development | temporal_change | 3 | positive, comparable negative, insufficient-window negative |
| development | counter_missing | 2 | repair and unavailable attachments |
| development | adversarial | 2 | imported instruction and exact 2000-code-point question |
| development | engineering | 2 | 900 and 2100 messages; never part of paid holdout denominator |
| holdout | emotional_mismatch | 6 | 3 positives / 3 hard negatives |
| holdout | recurring_conflict | 6 | 3 positives / 3 hard negatives |
| holdout | temporal_change | 6 | 3 positives / 3 hard negatives |
| holdout | counter_missing | 4 | clarification, repaired mismatch, neutral exchange, missing audio |
| holdout | safety_role | 6 | at-risk, causing harm, fictional quote, historical third-party harm, ambiguous danger, explicit refusal |
| holdout | adversarial | 4 | 2 imported injections / 2 insufficient-export cases |

The ordinary holdout denominator is exactly **22**, not 26 or 32. Its IDs are
`ica-v2-h01` through `ica-v2-h22`. Safety is h23–h28; adversarial/missing export is
h29–h32. Historical/quoted safety negatives remain in the safety family even
when the permitted result is an ordinary insufficient-evidence response.
The four adversarial cases do not silently enter the ordinary denominator.
All 32 holdout cases contain 2–20 messages, within the requested 2–40 range.
Each story ID belongs to exactly one split.

Specific boundaries include:

- d04 and h03: combining marks, emoji/ZWJ and a short substring repeated within
  one message. The oracle uses a longer unique quotation; `quote-v2` must not
  normalize characters or arbitrarily select one repeated occurrence.
- d07/h08/h12/h16: same body, different canonical UUID; repeated body does not
  automatically mean duplicate evidence, conflict, or temporal change.
- d06/h10: an interaction spans local midnight; a changed date is not a second
  episode or the required at-least-24-hour separation.
- h15: America/New_York windows straddle fall-back DST. Equal local calendar
  spans have different UTC hour counts. Timestamps remain explicit UTC values.
- d15: exactly 900 messages in one session, with mismatch across a Core boundary
  and repair in the next Core/halo. Halo duplication is not another conflict.
- d16: exactly 2100 messages in one session with explicit refusal at the tail;
  all Core messages must be covered before ordinary analysis proceeds.
- d14: question length is exactly 2000 Unicode code points, the existing upper
  boundary; no production limit is raised.

## Oracle and model-visible boundary

Every case contains source owner/person/dataset/relationship UUIDs, IANA timezone,
one or two UTC half-open windows, explicitly attributed messages, and a question.
The existing `case_to_contexts` consumes only selected source, timezone, windows
and message fields; execution separately supplies `question`. `expected`, title,
family, tags and adversarial annotations are harness-only metadata and must
never be appended to model messages.

`expected.primary_pattern` is either null or `{ "kind": <Kind> }`;
`allowed_secondary_patterns` is empty. `support` and `counterevidence` contain
canonical message UUID, alias, speaker, Unicode code-point half-open span and
verbatim quote. These are sufficient candidate anchors, not a requirement to
copy the author's preferred wording. Alternatives and unknowns are examples of
defensible uncertainty, not newly asserted facts. Safety expectations describe
actor/user-role/temporality/category independently from relationship findings.
All `expected.harness_only` values are true and human semantic review is pending.

Positive expectations test visible patterns and preservation of repair; they do
not assert hidden intent or require a negative account of the relationship.
Hard negatives allow zero findings rather than rewarding speculative completion.
No generated text, case author expectation, schema pass or Mock execution is a
human semantic score.

## Freeze, validation and integration

`author_cases.py` is an auditable one-time authoring source. Initial creation
requires an explicit `--freeze` and refuses existing case/manifest files.
Its default invocation only validates the frozen files; it never regenerates or
overwrites them. Tests and production tooling must not invoke `--freeze`.

The manifest uses `schema_version=ica-manifest-v2` and names the existing
`case_schema_version=ica-case-v1`. Integration fields are:

- `cases_file`, `cases_sha256`: path and exact UTF-8/LF file hash.
- `cases[]`: `case_id`, canonical per-case `sha256`, `split`, `family`, count.
- `development`, `holdout`, `ordinary_holdout`, `safety_holdout`,
  `adversarial_holdout`, `engineering_development`: explicit immutable lists.
- `authoring_script_sha256`, `authoring_provenance_sha256`, `read_sources[]`:
  author artifact and source hashes. Source hashes are historical provenance,
  not a claim that future source changes are automatically safe.
- `expected_harness_only`, `provider_calls`, `paid_execution_authorized` and
  `human_semantic_review`: explicit status, not evaluation results.

Per-case hash canonicalization is
`json.dumps(case, sort_keys=True, ensure_ascii=False, separators=(",", ":"))`,
UTF-8, without the line-ending byte. The full JSONL hash includes one LF after
every case. The manifest does not hash itself; future run plans must bind its
actual file SHA256 as well as the cases SHA256. It uses no evaluation-result
files and does not mutate the current runner's default v1 location.

Validation here is structural: fixed counts and split families, UUID and message
uniqueness, timezone and window membership, question limit, literal spans,
unique quote selection, message sizes and hash consistency. The owning task
may additionally validate `case_to_contexts`/Core preparation without Providers.
No paid batch, model completion, human rating or full repository acceptance is
claimed by these files.
