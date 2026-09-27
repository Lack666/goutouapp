# Phase 1B acceptance — Golden Evaluation Dataset

Date: 2026-09-26. Source contract: [SKILL_CONTRACT.md](SKILL_CONTRACT.md),
based on the frozen MIT upstream commit
`6db7354a4002dc7c448a9c87ffdad8132570c9d3`.

PHASE: Phase 1B — Golden Evaluation Dataset

STATUS: PASS (static dataset specification; no Agent behavior score)

## Existing dataset audit

The starting file had **55** anonymous synthetic cases, **21** categories,
**13** high-risk annotations, and two explicit fact/inference/unknown triples.
All original IDs were reviewed and retained. The baseline primarily covered
replies, invitations, flirting, conflict, imbalance, breakup/reconciliation,
betrayal, online/chat evidence, MBTI, manipulation, memory and several hazards.
The baseline had no linked minimal pairs and required fixed reference lists.
One scam cue (`online_01`) was marked ordinary; `reply_04` required an unrelated
consent reference; `conflict_02` used an overly broad boundary request; memory
operations and FIU source provenance were under-specified. The full baseline
case-to-contract matrix, overlaps retained and gaps are in
[GOLDEN_DATASET.md](GOLDEN_DATASET.md).

## Changes

- **Added 26**, **modified 55**, **deleted 0** Golden Cases. Every original
  case received contract-rule mapping, tags, semantic behavior expectations and
  flexible knowledge-routing metadata. Targeted original inputs/routes were
  refined where the baseline expectation was ambiguous or incorrect.
- Final dataset: **81 cases**, **27 categories**, **18 taxonomy scenarios plus
  memory**, **16 high-risk cases**, **six linked minimal pairs**. The count is
  the result of filling concrete gaps, not a target quota.
- Added `behavior_catalog.json` to define every required and forbidden
  behavior ID. Assertions are semantic; no case requires an exact answer string.
- Added a coverage matrix and validator tests. The validator checks data
  quality, not an absent Agent.

## Coverage

| Area | Result | Evidence |
| --- | --- | --- |
| Scenario | PASS | All 18 §3 scenarios have a primary-route case; high-frequency themes have multiple inputs; memory is separate |
| FIU | PASS | 12 cases carry sourced fact, tentative inference and unknown annotations; pairs B, C and F test source, speaker and MBTI changes |
| Knowledge | PASS | Every case declares primary/allowed/forbidden aliases and a maximum of 3; all map to real frozen files; safety cases require K17 alias first |
| Memory | PASS | 13 cases cover consent/no consent, pause/resume, revoke, item/person/all deletion, inference separation, person isolation, full-chat and sensitive-data limits |
| Safety | PASS | 16 high-risk cases cover self-harm, violence, coercion, stalking, non-consensual action, manipulation, fraud, privacy and legal risk; ordinary-first handling is forbidden |
| Anti-patterns | PASS | All 18 numbered §10 items map to at least one case, including mind reading, fact promotion, stereotypes, refusal bypass, theory-only response and knowledge overload |
| Response rules | PASS | All numbered §4 and §7 items map to cases; SHOULD-style layout is assessed semantically, not by exact prose |

## Minimal pairs

| Pair | IDs | Controlled difference |
| --- | --- | --- |
| A | `pair_a1` / `pair_a2` | Clear refusal vs scheduling constraint |
| B | `pair_b1` / `pair_b2` | Reported statement vs user's guess |
| C | `pair_c1` / `pair_c2` | Same messages with speaker labels swapped |
| D | `pair_d1` / `pair_d2` | Explicit memory consent vs no consent |
| E | `pair_e1` / `pair_e2` | Ordinary household conflict vs blocking someone from leaving |
| F | `pair_f1` / `pair_f2` | INTJ label present vs absent |

## Validation and runnable demo

- `python evals/validate.py`: **PASS** — 81 cases, 27 categories, 19 primary
  scenario values including memory, 16 high-risk cases, six minimal pairs.
- `.\make.cmd verify`: **PASS** — 13 unit tests, upstream Skill validator,
  Golden validator and repository secret-boundary check; `PASS: all active
  Phase 0..1 gates`. The three later-phase gates were explicitly deferred by
  the verifier and were not counted as passed.
- `git diff --check`: **PASS** (exit code 0).
- `git diff --name-only -- knowledge/goutoujunshi`: **empty**. The upstream
  inventory/hash unit test passed, including preserved MIT license/attribution.
- Demo is the actual validator output, not an Agent execution. No real LLM key,
  database or external account was used.

## Architecture decision and remaining gaps

Golden data now describes a primary scenario, risk route, required and
forbidden **behaviors**, FIU propositions with provenance, memory decision,
and a reference family with a 1–3 file bound. A future evaluator can compare
behavior and structured decisions without fixed natural-language strings.
The knowledge route expresses a required relevant entry and explicit unrelated
references, not a single exact file combination.

Static validation cannot show that a model classifies or responds correctly,
that knowledge was actually loaded, that a memory item was stored/deleted, or
that a safety path executed first. Runtime tests belong to later scheduled
phases. Contract §11.4 leaves future single-item deletion and backup semantics
open; `memory_delete_item_01` states the user-facing expectation without
inventing a database implementation. Location-sensitive legal details and
ambiguous real-world risk thresholds also need later runtime review.

## Files changed

`evals/golden_cases.jsonl`, `evals/reference_map.json`,
`evals/behavior_catalog.json`, `evals/validate.py`, `evals/README.md`,
`tests/test_golden_dataset.py`, `docs/GOLDEN_DATASET.md`,
`docs/PHASE_1B_ACCEPTANCE.md`, `docs/MASTER_PLAN.md`.

RECOMMENDED NEXT STEP: Under a separate instruction, begin Phase 2 — FastAPI
and PostgreSQL backend foundation. Stop after Phase 1B now.
