# Phase 1A acceptance — Skill Behaviour Contract

Date: 2026-09-26  
Upstream: `https://github.com/shengjidaguai-china/goutoujunshi` at
`6db7354a4002dc7c448a9c87ffdad8132570c9d3`, MIT.

PHASE: Phase 1A — Skill Behaviour Contract  
STATUS: PASS

## Implemented

- Replaced the short contract with a source-backed behavioral specification:
  purpose, scope, 18 scenarios, 12 normative reasoning principles,
  fact/inference/unknown rules with 9 worked examples, deterministic
  1–3-reference routing, response behavior, memory and safety contracts,
  18 anti-patterns, 8 open questions and source mapping.
- Recorded the distinction between upstream documentation and the executable
  local memory script: `--confirm` is not proof of user consent; the script
  has no multi-user authentication, and not every control operation applies
  the consent gate.
- Added `tests/test_skill_contract.py` to verify required sections, source
  commit, minimum scenario/example/anti-pattern counts, and coverage of all
  43 frozen reference filenames.

## Sources reviewed

- `knowledge/goutoujunshi/SKILL.md`, `README.md`, `SECURITY.md`,
  `LICENSE`, `agents/openai.yaml`.
- All 20 files in `references/knowledge/` and all 23 files in
  `references/practical/`; emphasis on evidence, consent, manipulation,
  safety, online/chat evidence, knowledge routing and long-term memory.
- All files in `documentation/`: `architecture.md`, `automation.md`,
  `flows.md`, `knowledge-base.md`, `permissions.md`, `product.md`,
  `variables.md`.
- `scripts/memory_store.py` and `scripts/validate_skill.py`.

## Acceptance check

| Criterion | Result | Evidence |
| --- | --- | --- |
| A. File completeness | PASS | Contract is an independent specification, not README duplication; source mapping and frozen commit present |
| B. Scenario taxonomy | PASS | 18 rows, each with definition/example, knowledge, goal, pitfall and source |
| C. Reasoning rules | PASS | MUST/SHOULD/MUST NOT, nine FIU examples, MBTI/gender limits, reciprocity, boundary, refusal and action |
| D. Knowledge routing | PASS | Direct scenario-to-reference map; 1–3 documents; safety priority; no RAG implementation |
| E. Memory | PASS | Allowed/forbidden data, consent, inspect/pause/resume/undo/delete, no full-chat storage, inference separation and script/document gaps |
| F. Safety | PASS | Violence, self-harm, coercion, stalking, manipulation, refusal, fraud and legal risk; safety precedes ordinary strategy |
| G. Anti-patterns | PASS | 18 project-specific failures with source citations |
| H. Testability | PASS | Concrete pass/fail language and three automated documentation acceptance tests |
| I. No scope creep | PASS | Diff limited to contract, its test, plan and this report; no Agent, API, RAG, database or mobile feature code |

## Validation and real demo

- `python -m unittest discover -s tests -v`: **8 tests passed**, including
  three Phase 1A acceptance tests.
- `.\make.cmd verify`: **PASS**, all active Phase 0–1 gates. Upstream
  validator passed; existing synthetic Golden annotation validator passed
  with 55 cases, 21 categories and 13 high-risk cases; secret boundary passed.
  The existing cases were not modified in this phase and this is not an
  executable Agent behavior evaluation.
- `git diff --check`: passed. Frozen upstream inventory/hash test passed;
  original source contents and MIT attribution remain unchanged.
- Plain `make verify` is not recognized by this PowerShell environment.
  The repository's Windows shim `.\make.cmd verify` invokes the same target
  and passed. This is an environment command-name limitation, not a skipped gate.

## Architecture decisions and uncertainties

The contract treats `SKILL.md` and focused knowledge safety/evidence rules as
higher authority than example wording in practical guides. It documents
observable behavior without claiming that the upstream prompt already provides
hard runtime enforcement. No architecture implementation was changed.

Open questions include verified consent and future user isolation, field-level
memory validation, deletion semantics, ambiguous risk thresholds, authenticity
filtering for some example scripts, ChatLab CLI drift and location-sensitive
legal resources. Details and source links are in
[SKILL_CONTRACT.md](SKILL_CONTRACT.md#11-open-questions-与已知差异).

NEXT: Stop after Phase 1A. Under a new Phase 1B instruction, compare the
existing 55 synthetic Golden Cases against the expanded normative contract,
especially clear refusal versus scheduling refusal, speaker identity,
inference-to-fact promotion, memory consent and safety precedence.
