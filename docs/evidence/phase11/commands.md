# Phase11 executed commands

All run from repository root using uv/locked dependencies. Python import root for
evaluation scripts: `$env:PYTHONPATH='apps/server;.'`. Live calls used private
EVAL_LIVE_OPT_IN=true and LLM_TIMEOUT_SECONDS=90. No key CLI argument. Native local
PostgreSQL test URL was supplied privately as TEST_DATABASE_URL (database namespace
ends `_test`); random disposable databases were migrated and dropped by the existing
helper. `.env` was loaded by `uv --env-file .env`; no secrets are reproduced here.

## Final focused suite

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env pytest -q --tb=short --basetemp=.cache/phase11-pytest-final apps/server/tests/test_eval_observability.py apps/server/tests/test_provider_fault_e2e.py apps/server/tests/test_llm_mock.py apps/server/tests/test_llm_openai_compatible.py apps/server/tests/test_agent_runtime.py apps/server/tests/test_agent_streaming.py apps/server/tests/test_agent_semantic.py apps/server/tests/test_agent_contracts.py apps/server/tests/test_agent_action_response.py apps/server/tests/test_agent_analysis.py apps/server/tests/test_agent_memory.py apps/server/tests/test_memory_mutation.py apps/server/tests/test_memory_control.py apps/server/tests/test_authorization_security.py apps/server/tests/test_security_priority_9g.py apps/server/tests/test_phase4_idempotency.py apps/server/tests/test_agent_stream_api.py apps/server/tests/test_agent_rest.py
```

Result:338 passed20.33s, exit0. Raw targeted-tests.txt/.exit. Earlier intermediate
focused suite182 passed14.97s. After formatting the review instruction string, the
new evaluator suite and frozen upstream inventory/license checks passed13 tests2.21s.
No claim of351 distinct tests: the13 overlap the338, plus two frozen-source checks.

## Offline and live commands

Run prefix: `uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env`.
Then these executable arguments (output path is inside evals/agent/results):

- `python -m evals.agent.harness --output evals/agent/results/final-mock-01.json`
- Same command, output final-mock-02.json. Full60 results equal with run IDs removed;
  all60 expected outcomes pass, including8 controlled failures.
- `python -m evals.agent.live_checks smoke --output evals/agent/results/final-live-smoke.json`
- `python -m evals.agent.live_checks e2e --output evals/agent/results/final-live-e2e.json`
- `python -m evals.agent.harness --live --ids safety-01,safety-02,safety-03,safety-04,safety-05,safety-06,safety-07,safety-08,safety-09,safety-10,safety-11,safety-12 --output evals/agent/results/final-live-safety.json`
- `python -m evals.agent.harness --live --ids communication-01,communication-02,communication-04,communication-05 --output evals/agent/results/final-live-communication.json`
- `python -m evals.agent.harness --live --ids grounding-01,grounding-03,grounding-07,grounding-12 --output evals/agent/results/final-live-grounding.json`
- `python -m evals.agent.harness --live --ids safety-01,safety-02,communication-01,grounding-01 --output evals/agent/results/final-live-repeat.json`

Every existing output path is refused before any new paid request. Reproduce to a
new path. Early diagnostic attempts use the same commands with separately named
paths; attempts.json lists all recorded admissions, unknown-cost calls and aborted
DB/failed-save attempts. No failed or superseded live artifact is removed.

## Reporting and privacy checks

`python scripts/agent_eval_report.py` generated aggregate-final.json, a readable
report and15-case review packet. Recomputed with
`python scripts/agent_eval_report.py --output .cache/phase11-recomputed.json --report .cache/phase11-recomputed.md`;
aggregate equality assertion passes.

`python scripts/check_phase11.py` passes source-archive fingerprint/AST binding,
unchanged official marker/Golden/upstream,60-case completeness, final aggregation,
budget bounds and trace credential/private-field checks. Output: evidence-check.json.
Additional exact-key scan of all evidence and decompressed source archive passes;
final live start/end fingerprints match; no credential value was printed.

Ruff check and `ruff format --check` pass on31 changed/relevant Python files across
app provider/config/runtime/prompts/service diagnostics, new tests, evals and report/
checker scripts. No new dependency or TypeScript source. No Python type checker is
configured. Full make verify, historical full suites and native scenes: NOT RUN,
explicitly deferred to final closeout.
