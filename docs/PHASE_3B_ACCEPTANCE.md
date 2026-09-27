# Phase 3B acceptance — Minimal Standalone LangGraph Runtime

Date: 2026-09-27

## PHASE / STATUS / LANGGRAPH VERSION

Phase 3B — Minimal Standalone LangGraph Runtime: **PASS**. LangGraph
**1.2.12** is pinned in the root `uv.lock`; the existing Python project and
lockfile remain the single dependency source. Phase 3 semantic behavior is
not complete.

## GRAPH STRUCTURE / RUNTIME API / DEPENDENCY INJECTION

`AgentRuntime(dependencies=RuntimeDependencies(...))` compiles a real
`StateGraph(AgentState)` once per instance. `await runtime.run(AgentInput)`
returns `AgentResult | AgentFailure`. Nodes are `normalize_input`,
`safety_gate`, `classify_stub`, `minimal_analysis`, `finalize`, and
`safety_finalize`. A LangGraph conditional edge sends ordinary input through
the stub and analysis; the synthetic high-risk route goes straight to safety
finalization. Both reach `END`. The runtime uses the injected Phase 2C
`LLMProvider` only; no node reads settings, builds a provider or connects to
FastAPI/SQLAlchemy. No checkpointer or database write is present.

## SUCCESS PATH / SAFETY ROUTE / FAILURE HANDLING

Normal input initializes a new `run_id` and pending state, enters running
before `ainvoke`, calls Mock structured output, then returns a completed
version-1 result. JSON round-trip passes, and public output excludes the
internal state. The synthetic safety flag selects the conditional branch
before any ordinary analysis; a test runs it with an empty Mock queue to prove
the provider path was skipped.

Invalid input, normalized LLM dependency errors, malformed structured output
and unexpected node errors return safe `AgentFailure` codes and fixed text.
The run ID stays correlated through state and output or failure. Raw exception
content, including synthetic secret markers in tests, is not returned.

## RUN ISOLATION / STATE DISCIPLINE

Concurrent runs with separate scripted Mock providers return distinct run IDs
and correctly paired outputs. Sequential runs reuse one compiled graph while
receiving independent state and responses. Nodes receive only their declared
read fields and must return exactly their declared write fields; tests reject
both unauthorized reads and writes. `run_id` and `run_status` are runtime-owned
additions to the Phase 3A internal state. Public result version remains `1`.

## STANDALONE DEMO / GOLDEN SMOKE

`uv --cache-dir .cache/uv --no-managed-python run --offline --locked python apps/server/agent_demo.py`
ran successfully without an API key, network, FastAPI or PostgreSQL. It
printed completed `AgentResult` JSON with `schema_version=1`, a UUID run ID,
`route=ordinary`, and a synthetic Mock analysis result.

Golden `pair_e1`/`pair_e2` are used as graph architecture smoke inputs. The
test supplies the synthetic safety flag from the expected route; it does not
infer safety from their text or grade semantic responses. The 81-case
validator remains a static dataset check.

## TESTS / VALIDATION

- Focused Agent runtime tests: **10 passed** (individual nodes, scope guard,
  graph edges, completed run, safety bypass, failure categories, isolation,
  import boundary and Golden pair smoke).
- Phase 3A Agent contract tests: **86 passed**.
- `uv --cache-dir .cache/uv --no-managed-python run --offline --locked python apps/server/agent_demo.py`: **PASS**.
- `.\make.cmd verify`: **PASS** — 13 repository/contract tests, frozen upstream
  validator, isolated Alembic upgrade/downgrade/upgrade/check, 32 LLM tests,
  7 backend smoke tests, 86 Agent contract tests, 10 runtime tests, full backend
  suite (**154 passed**), Golden static validator (**81 cases**), repository
  secret boundary, Ruff check and format check.
- `git diff --check`: **PASS**; newly created files received a separate
  whitespace check because they are still untracked.

## ARCHITECTURE DECISIONS / FILES CHANGED

[ADR 0010](adr/0010-minimal-langgraph-runtime.md) records compile/reuse,
conditional routing, synthetic safety scope, error normalization and no
checkpoint. Phase 3B adds `app/agent/nodes.py`, `app/agent/runtime.py`,
`apps/server/agent_demo.py`, `test_agent_runtime.py`, this report and ADR;
updates the internal state, the root project/lockfile, verifier, phase marker,
architecture, runtime documentation and master plan. Existing uncommitted
Phase 1B–3A work was preserved, so no mixed-stage Git commit was created.

## KNOWN ISSUES / DEFERRED / NEXT

No known failing Phase 3B gate. The safety flag and constant scenario are
fixtures, not real classification. Semantic safety/scenario/FIU nodes,
knowledge routing, relationship reasoning, memory persistence, durable
checkpointing, streaming/API transport and mobile remain deferred.

Next authorized stage: Phase 3C — Safety, Scenario and FIU Semantic Nodes.
