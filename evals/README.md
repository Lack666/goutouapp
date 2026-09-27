# Golden evaluation data

`golden_cases.jsonl` contains anonymous synthetic requests and **semantic**
expectations for a future independent Agent Runtime. Phase 1B validates these
annotations only. It does not call an LLM or grade an Agent that does not yet
exist. Run `python evals/validate.py` or `.\make.cmd eval` on Windows.

## Case format

- `id`: stable unique identifier. Existing Phase 1 IDs were retained.
- `category`: narrow dataset topic, including safety risk and memory operations.
- `input`: synthetic user request; no real private conversations.
- `contract_rules`: numbered sections/items in `docs/SKILL_CONTRACT.md`.
- `tags`: cross-cutting coverage such as `fiu` or `safety_precedence`.
- `minimal_pair`: optional group `A`–`F`, variant, and machine-checked contrast
  field. Both variants keep the same task and change a key fact.
- `expected.scenario`: primary handling family from the 18-scenario taxonomy,
  plus `memory` for the separate memory-control contract.
- `expected.safety`: `normal` or `high`. `expected.route` is `ordinary`,
  `boundary`, or `safety`. An explicit refusal may require a boundary response
  without an acute emergency; dangerous pursuit uses `safety`.
- `expected.assertions`: required behavior IDs. `expected.forbidden_behaviors`:
  disallowed behavior IDs. These describe meaning, not fixed prose. A future
  evaluator must inspect behavior and structured decisions, not search for a
  sentence or word.
- `expected.evidence`: optional `facts`, `inferences`, and `unknowns`. Every
  fact has a `source` such as `user_report_quote` or `chat_message`; every
  inference has an alternative explanation. These are propositions to preserve
  or keep uncertain, not required output strings. Empty `inferences` is valid
  when a user-reported quote requires no interpretation.
- `expected.knowledge`: `required_any` lists a suitable primary reference
  family; `allowed` lists accepted on-topic references; `forbidden` identifies
  specifically unrelated references; `max_count` is at most 3. The Phase 3D
  deterministic router passes when it selects a relevant primary reference, respects the count and
  excludes forbidden material. It need not choose an identical full set. Safety
  cases require the `safety` alias before ordinary relationship material.
  Aliases resolve through `reference_map.json` to existing frozen files.
- `expected.memory_writes`: maximum permitted long-term write candidates
  (`0` or `1`), **not** a claim that a database write occurred. Memory cases
  also give `expected.memory.decision` (`no_write`, `allow_candidate`, `pause`,
  `resume`, `revoke_keep`, `delete_item`, `delete_person`, `delete_all`, or
  `revoke_and_delete_all`). An allowed candidate still needs runtime consent,
  source and ownership checks in later phases.

Every behavior ID has a short rubric definition in `behavior_catalog.json`;
the validator rejects unknown IDs. Behavior IDs are stable semantic labels.
For example, `mind_reading` forbids
turning an unknown motive into a fact; `inference_as_fact` forbids promoting a
user or model guess; `ordinary_strategy_first` forbids leading with pursuit,
reconciliation or joint repair when safety handling is required;
`speaker_reversal` forbids changing the supplied speaker mapping;
`overload_references` forbids reading unrelated or excessive context. Positive
IDs such as `facts_inferences_split`, `stop_pursuit`, `safety_first` and
`person_isolation` specify observable behavior. Case input, evidence fields,
route and contract mapping define the precise context of each ID.

`docs/GOLDEN_DATASET.md` contains the baseline audit and coverage matrix.
The validator checks IDs, schema, category/scenario, real reference paths,
contract rule references, safety precedence, memory decisions, FIU annotation
shape and all six minimal-pair contrasts. It cannot prove an LLM would follow
the contract. Future runtime evaluation should use these records as a rubric
without hard-coding their output wording.

Phase 3E selects 30 analysis-heavy cases in `phase3e_subset.json`. Its
`phase3e_analysis.py` evaluator checks structured FIU/reference provenance,
selected required dimensions, several forbidden structured patterns, safety
bypass and absence of action/memory output. Mock outputs are derived from
Golden annotations and behavior IDs. Passing this replay checks wiring and
evaluator consistency; it is not an independent assessment of a live model's
relationship analysis or nuanced language quality.
