# Golden evaluation data

`golden_cases.jsonl` contains 55 synthetic, anonymous examples. Each record
has a category and input, then expected scenario, safety route, selected
reference aliases, output assertions and maximum long-term memory writes.
`reference_map.json` resolves aliases to files in the frozen upstream snapshot.

Run `python evals/validate.py` or `make eval`. This Phase 1 command verifies
the quality and consistency of the **annotations**. It does not run a model or
grade an absent Agent. Phase 3 will execute safety, scenario, evidence and
response assertions against a MockLLM runtime; Phase 4 will grade actual
knowledge routing against the expected reference aliases. Do not convert a
Golden expectation into a hard-coded answer in the runtime.

Safety cases require the high-risk path and the safety reference before any
ordinary relationship analysis. Cases expecting a long-term write explicitly
include consent. The dataset contains no real chat records or identities.
