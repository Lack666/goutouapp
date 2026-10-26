# Targeted reliability closeout commands

Date: 2026-10-26. Base commit: 051d51d. Each live JSON records exact base Git
commit, source fingerprint, versions, timestamps, actual usage, call traces and
synthetic visible outputs. Each matching ZIP preserves that source (including the
additional two-case dataset). No prior outputs or user reviews were overwritten.

Offline command (PowerShell, repository root):

```powershell
$env:TEST_DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:5433/goutou_test'
uv --cache-dir .cache/uv --no-managed-python run --locked pytest -q --tb=short apps/server/tests/test_phase11_reliability_closeout.py apps/server/tests/test_phase11_structured_reliability.py apps/server/tests/test_agent_analysis.py apps/server/tests/test_agent_action_response.py apps/server/tests/test_agent_semantic.py apps/server/tests/test_agent_memory.py apps/server/tests/test_agent_runtime.py apps/server/tests/test_agent_streaming.py apps/server/tests/test_llm_openai_compatible.py apps/server/tests/test_eval_observability.py apps/server/tests/test_security_priority_9g.py apps/server/tests/test_provider_fault_e2e.py apps/server/tests/test_agent_rest.py apps/server/tests/test_agent_stream_api.py --basetemp=.cache/closeout-v8-tests
```

Final: 245 passed, 13.42s; closeout-v8-tests.txt and .exit. Frozen model-output
tests cover historical failures without making network requests. PostgreSQL uses
disposable fixture databases; Provider is Mock in those DB/transport tests.
Earlier local runs and failures are retained in closeout-*-tests logs. Initial DB
configuration errors were fixed by selecting the running local PostgreSQL16 on
5433, rather than using the unavailable default test DB on5432.

Live commands used the same opt-in below, once per version (no automatic retry):

```powershell
$env:PYTHONPATH='apps/server;.'
$env:EVAL_LIVE_OPT_IN='true'
$env:LLM_TIMEOUT_SECONDS='90'
$env:EVAL_MAX_REQUESTS='30'
$env:EVAL_MAX_COST_CNY='2.4'
uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env python -m evals.agent.reliability_closeout --live --repair-only --output evals/agent/results/closeout-v8-live.json
```

v6/v7 omitted --repair-only, used respective output filenames and cost ceilings
5 / 3.7 CNY. v8 uses2.4. Sum of all conservative reservations is3.617518 CNY,
within the cumulative5 CNY limit. Errors count toward request/usage budgets.
Credentials were read privately in the backend; no CLI key, hidden reasoning,
real user conversation, or additional memory permission was supplied.

Report creation (exclusive, refuses existing evidence) / read-only verification:

```powershell
$env:PYTHONPATH='apps/server;.'
uv --cache-dir .cache/uv --no-managed-python run --locked python scripts/phase11_closeout_report.py
uv --cache-dir .cache/uv --no-managed-python run --locked python scripts/phase11_closeout_report.py --check
```

Ruff check and format --check cover all16 changed/new Python files. No root
verification, full historical suite or Android scenarios ran. Final live path is
LangGraph/DeepSeek, not a new signed-JWT/PostgreSQL live-provider E2E claim.
