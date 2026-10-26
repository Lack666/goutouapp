# Phase11 reliability follow-up — executed commands

2026-10-26, repository root, uv locked environment. No Root Verify, Android,
full historical suite or new DB E2E. Private api.txt/.env never reproduced here.

## Offline before paid requests

For v3, the new regression file plus test_agent_analysis, test_agent_action_response,
test_llm_openai_compatible and test_eval_observability:64 passed3.11s; Ruff passed.
For v4, the same selection including frozen v3 graph replays:67 passed4.79s.
For v5, added quotation-negative cases, frozen v4 replays, test_agent_semantic and
test_agent_memory:100 passed5.90s. No paid requests in pytest.

Final command additionally includes frozen v5 outputs and the separate packet/UI:

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked pytest -q apps/server/tests/test_phase11_structured_reliability.py apps/server/tests/test_agent_analysis.py apps/server/tests/test_agent_action_response.py apps/server/tests/test_llm_openai_compatible.py apps/server/tests/test_eval_observability.py apps/server/tests/test_agent_semantic.py apps/server/tests/test_agent_memory.py tests/test_human_review_ui.py --basetemp=.cache/reliability-final-tests
```

110 passed6.72s, exit0; raw reliability-targeted-tests.txt and .exit. These overlap
earlier selections; do not add their counts together as distinct tests.
Ruff check and format --check pass for changed Python files and prompt directory.

## Paid development retests — four explicit batches

Each invocation set backend-only EVAL_LIVE_OPT_IN=true, LLM_TIMEOUT_SECONDS=90,
EVAL_MAX_REQUESTS=30, EVAL_MAX_COST_CNY=5, PYTHONPATH=apps/server;.
No CLI key, no automatic retry. Source changed only between batches, never during
each run. Provider returned finish=stop for captured outputs; incomplete responses
remain rejected by the existing adapter.

All commands use this prefix, with output paths under evals/agent/results:

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env python -m evals.agent.harness --live
```

- v3: --ids communication-02,communication-04,communication-05,grounding-01,grounding-07
  --output evals/agent/results/reliability-fix-v3-original-five.json;3/5,27 calls.
- v4: same5 IDs, --output evals/agent/results/reliability-fix-v4-original-five.json;
  4/5,28 calls. Additional source/prompt changes and offline checks preceded it.
- v5: same5 IDs, --output evals/agent/results/reliability-fix-v5-original-five.json;
  5/5,30 calls. Narrow quotation fix and negative tests preceded it.
- v5 expansion, conditional on previous5/5:
  --ids communication-01,grounding-03,grounding-12,communication-03,grounding-02
  --output evals/agent/results/reliability-fix-v5-regression.json;3/5,28 calls,
  another completed case fails one behavior assertion. No further paid requests.

All four results and all failures retained. Total113 calls, no transport errors,
cost upper bound0.39533016 CNY. Each JSON contains its own conservative reservation
ledger and official peak price version; actual usage is not substituted by that
reservation. The individual per-batch budget is not a claim of30 total calls.

## Evidence and review

```powershell
$env:PYTHONPATH='apps/server;.'
uv --cache-dir .cache/uv --no-managed-python run --locked python scripts/diagnose_phase11_structured.py evals/agent/results/reliability-fix-v3-diagnosis.json
uv --cache-dir .cache/uv --no-managed-python run --locked python scripts/phase11_reliability_report.py
uv --cache-dir .cache/uv --no-managed-python run --locked python scripts/check_phase11_reliability.py
```

First two commands refuse existing evidence paths; use a disposable restored copy
to regenerate, rather than deleting existing evidence. Checker is read-only and
can be repeated. Three source ZIP fingerprints and historical result hashes checked.
Original formal schema, Golden83, frozen Skill, Phase9 acceptance and Marker unchanged.

Started hidden local review process on8766 with:

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked python scripts/human_review_ui.py --packet evals/agent/results/reliability-fix-v5-human-review-15.json --port 8766
```

Actual Chrome/Playwright read-only smoke:15 cases,6 empty selects,2 failed outputs,
source version shown,0 browser errors, no scores saved. UI isolation unit test uses
only disposable copies. Old8765 process and actual15/15 human ratings preserved.
No evidence, identity, timestamp or score was synthesized as a human review.
