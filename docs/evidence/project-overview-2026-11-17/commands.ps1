# Commands actually used during the 2026-11-17 read-only implementation audit.
# Run from repository root. Test selection is offline/Mock; no paid evaluation.
# Historical result: root verify exit1; targeted tests passed. Not a stage advance.

.\make.cmd verify
# FAIL: 9H current-source/baseline scope drift (exit1, before complete regression).

$overviewTests = @(
    'test_ica_cases.py', 'test_ica_cases_v2.py',
    'test_ica_eval.py', 'test_ica_eval_v2.py',
    'test_ica_review.py', 'test_ica_review_v2.py',
    'test_ica_live_budget.py', 'test_ica_live_v2.py',
    'test_ica_bq_replay.py', 'test_ica_quote.py',
    'test_ica_quote_runtime.py', 'test_ica_quote_replay.py',
    'test_ica_runtime.py', 'test_ica_foundation.py',
    'test_agent_runtime.py', 'test_agent_knowledge.py', 'test_safety_roles.py'
) | ForEach-Object { 'apps/server/tests/' + $_ }
uv --cache-dir .cache/uv --no-managed-python run --locked --offline pytest @overviewTests -q --basetemp=.cache/pytest-overview-20261117
# 309 passed in 6.71s.

# First pnpm attempts failed on AppData temp-directory access before checks ran.
# These process-local settings allowed the following successful invocations.
New-Item -ItemType Directory -Force -Path .cache/tmp-overview | Out-Null
$env:TEMP = (Join-Path (Get-Location) '.cache/tmp-overview')
$env:TMP = $env:TEMP
pnpm --filter @goutou/mobile run typecheck
pnpm --filter @goutou/mobile test
# 29 suites, 413 tests passed in 21.553s.
pnpm api:check
# 52 operations, 3 codegen tests passed.
uv --cache-dir .cache/uv --no-managed-python run --locked --offline python scripts/export_openapi.py --check
# 52 operations, all 26 Phase7D contracts preserved.

# Demo initially needed repository root on the import path; successful command:
$env:PYTHONPATH = '.;apps/server'
$env:PYTHONUTF8 = '1'
uv --cache-dir .cache/uv --no-managed-python run --locked --offline python apps/server/agent_demo.py
# saved_count1; new-conversation historical_memory_loaded1; final answer produced.

# Repository audit also ran 74 overlapping tests; do not add to the 309 count.
uv --cache-dir .cache/uv --no-managed-python run --locked --offline pytest -q --basetemp=.cache/pytest-audit-runtime-20261117 apps/server/tests/test_agent_runtime.py apps/server/tests/test_agent_knowledge.py apps/server/tests/test_ica_quote.py apps/server/tests/test_safety_roles.py
