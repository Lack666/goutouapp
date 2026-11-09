# Historical commands for one authorized v2 batch, 2026-11-09. Not a rerun authorization.
# Repeated run/authorize/export against this directory must fail exclusive-create.
$env:PYTHONUTF8='1'
$env:UV_CACHE_DIR=Join-Path $PWD '.cache/uv'
$env:PYTHONPATH='apps/server;.'
$selected=@('apps/server/tests/test_ica_cases.py','apps/server/tests/test_ica_cases_v2.py','apps/server/tests/test_ica_eval.py','apps/server/tests/test_ica_eval_v2.py','apps/server/tests/test_ica_review.py','apps/server/tests/test_ica_review_v2.py','apps/server/tests/test_ica_live_budget.py','apps/server/tests/test_ica_live_v2.py','apps/server/tests/test_ica_bq_replay.py','apps/server/tests/test_ica_quote.py','apps/server/tests/test_ica_quote_runtime.py','apps/server/tests/test_ica_quote_replay.py','apps/server/tests/test_ica_runtime.py','apps/server/tests/test_ica_foundation.py','apps/server/tests/test_agent_runtime.py','apps/server/tests/test_agent_knowledge.py','apps/server/tests/test_safety_roles.py')
uv run --no-sync pytest @selected -q --basetemp=.cache/ica-v2-prepaid-final-1109
# 309 pass. All HTTP in offline admission tests uses MockTransport and synthetic keys.
uv run --no-sync ruff check evals/ica/live.py evals/ica/live_v2.py evals/ica/runner.py evals/ica/review.py apps/server/tests/test_ica_eval_v2.py apps/server/tests/test_ica_cases_v2.py apps/server/tests/test_ica_review_v2.py apps/server/tests/test_ica_live_v2.py
uv run --no-sync ruff format --check evals/ica/live.py evals/ica/live_v2.py evals/ica/runner.py evals/ica/review.py apps/server/tests/test_ica_eval_v2.py apps/server/tests/test_ica_cases_v2.py apps/server/tests/test_ica_review_v2.py apps/server/tests/test_ica_live_v2.py
uv run --no-sync ruff check evals/ica/v2/author_cases.py
uv run --no-sync ruff format --check evals/ica/v2/author_cases.py
uv run --no-sync python scripts/export_openapi.py --check
pnpm api:check
# Following three commands already consumed the user's one-batch authorization.
uv run --no-sync python -m evals.ica.live_v2 plan docs/evidence/ica-bq-v2/batch-v2
uv run --no-sync python -m evals.ica.live_v2 authorize docs/evidence/ica-bq-v2/batch-v2 --confirmed --approval-reference '2026-11-09 explicit user reply: authorize this batch at most CNY20; no automatic retries'
uv run --no-sync python -m evals.ica.live_v2 run docs/evidence/ica-bq-v2/batch-v2
# 233 actual sends; reserved CNY19.935784. Stop, no automatic retry/resume/second batch.
# Original successful export by parallel task:
uv run --no-sync python -m evals.ica.review render docs/evidence/ica-bq-v2/batch-v2/results.jsonl evals/ica/v2/cases.jsonl docs/evidence/ica-bq-v2/human-review
uv run --no-sync python -m evals.ica.review summarize docs/evidence/ica-bq-v2/batch-v2/results.jsonl evals/ica/v2/cases.jsonl docs/evidence/ica-bq-v2/human-review/reviewer/packet.json docs/evidence/ica-bq-v2/human-review-pending.json
# Root repeated these after a subagent limit error; both refused overwrite. Error logs retained.
# Root's temporary offline audit/cutoff scripts validated original packet and raw ledger,
# source equality,102 canonical references,233 calls,usage/cost and pre-send money cutoff.
# execution-audit.json and cutoff-diagnostic.json are automated diagnostics, not human judgments.
git diff --check -- .gitattributes docs/MASTER_PLAN.md docs/ARCHITECTURE.md evals/ica/live.py evals/ica/review.py evals/ica/runner.py
git diff --exit-code -- apps/server/app apps/mobile/src uv.lock pnpm-lock.yaml docs/evidence/ica-bq docs/evidence/ica-bq-r1 docs/evidence/ica-b1 evals/ica/v1 knowledge project-phase.json
# After real human work, preserve original unscored packet; save a new filled copy.
# summarize into a NEW output file; never overwrite original pending or old human scores.
