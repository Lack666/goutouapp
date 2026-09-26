# Master plan

Source specification: `knowledge/goutoujunshi`, commit
`6db7354a4002dc7c448a9c87ffdad8132570c9d3`. The snapshot is MIT
licensed and its content hashes are frozen in `knowledge/upstream-manifest.json`.

## Phase gate

A phase passes only with CODE, TEST, DOC, DEMO, and REGRESSION. `make verify`
checks the gates implemented so far and names future gates as deferred. A
phase report records the exact command and output. No future feature is counted
as implemented by a placeholder directory or a golden expectation.

| Phase | Deliverable | Status |
| --- | --- | --- |
| 0 | Repository bootstrap, upstream audit, monorepo, verification | PASS |
| 1 | Skill contract and at least 40 synthetic Golden Cases | PASS |
| 2 | FastAPI, PostgreSQL, Pydantic, SQLAlchemy, Alembic | PENDING |
| 3 | Standalone LangGraph runtime, provider abstraction, streaming | PENDING |
| 4 | Deterministic 1–3 document knowledge router | PENDING |
| 5 | Consent gated and isolated long-term memory | PENDING |
| 6 | TXT/Markdown/JSON import and ordinary-code statistics | PENDING |
| 7 | Expo React Native MVP | PENDING |
| 8 | API integration, generated client, WebSocket streaming | PENDING |
| 9 | Security, privacy, reliability and deletion | PENDING |
| 10 | Optional hybrid RAG with pgvector | PENDING |
| 11 | Agent eval and observability | PENDING |
| 12 | CI/CD, EAS preview, release preparation | PENDING |

## Exit criteria by phase

0. Preserve upstream exactly; inspect skill, README, documentation, references,
   scripts and license; record commit; run upstream validator and repository
   verifier. Demo: verified snapshot and `doctor` output.
1. Record behavioral, safety, evidence, memory, response, and knowledge
   contracts. Validate at least 40 anonymous synthetic cases with scenario,
   safety, references, and assertions. Demo: run the dataset validator. This
   phase tests the **evaluation specification**, not an absent Agent.
2. CRUD storage and migration with ownership checks; API/OpenAPI and database
   integration tests; local Compose demo.
3. Keyless MockLLM and OpenAI-compatible provider behind `chat`, `stream`, and
   `structured_output`; independent CLI/Python demo; individual node tests.
4. Scenario-based reference selection, exact document loading and router eval;
   no embeddings.
5. Explicit consent, inspect, pause, resume, delete one/all, source gates and
   person isolation with database tests.
6. Decoupled parsers, speaker mapping, timestamps, source provenance and
   deterministic metrics with representative fixtures.
7. Six mobile surfaces: home, chat, relationship/profile, import/analysis,
   history, settings. Typecheck and on-device or Expo web demo.
8. OpenAPI-generated TypeScript client and stable status/token/analysis/
   interrupt/error/done WebSocket events with run and idempotency IDs.
9. Upload limits and type checks, traversal prevention, access isolation,
   deletion, log redaction, and high-risk safety priority.
10. Optional metadata, keyword/BM25, vector and rerank retrieval; prove value
    against deterministic baseline. `FEATURE_RAG=false` remains complete.
11. Behavioral eval on the running Agent, observability of nodes, latency,
    provider, tokens, cost and outcome; optional LangSmith failure isolation.
12. Locked dependencies, CI, Docker/Compose, EAS preview and release checklist.

## Implementation log

### Phase 0

- Copied 63 upstream Skill files, including 20 knowledge and 23 practical
  references, scripts, documentation and MIT license, into an immutable snapshot
  at `knowledge/goutoujunshi`. The source checkout matches the recorded commit.
- Recorded the exact source commit and SHA-256 inventory.
- Created `apps/mobile`, `apps/server`, `knowledge/goutoujunshi`, `docs`,
  `evals` and `scripts`, plus `AGENTS.md`, `.env.example`, `README.md`,
  `Makefile`, `pyproject.toml`, pnpm workspace and phase-aware verification.
- Rechecked this structure against the explicit Phase 0 acceptance list on
  2026-09-26. Simplified `ARCHITECTURE.md` to the confirmed system boundaries;
  moved the snapshot without changing source file contents. See ADR 0004.
- Acceptance: [Phase 0 report](PHASE_0_ACCEPTANCE.md).
- Commit: `eccc633` (`chore: bootstrap standalone runtime monorepo and freeze upstream`).

### Phase 1

- Completed `docs/SKILL_CONTRACT.md` with intake, evidence, scenario route,
  safety, relationship, memory, import and evaluation obligations.
- Added 55 anonymous synthetic Golden Cases across 21 categories, including
  13 high-risk cases, and a 19-reference alias map linked to the frozen source.
- Validated uniqueness, coverage, reference existence, safety precedence,
  explicit memory consent and fact/inference annotation structure.
- Acceptance: [Phase 1 report](PHASE_1_ACCEPTANCE.md).
- On 2026-09-26, completed the narrower Phase 1A behavior-contract audit
  against the frozen upstream. Expanded the contract with 18 source-backed
  scenarios, 9 fact/inference/unknown examples, all 43 reference names,
  response and memory rules, safety priority, 18 anti-patterns and explicit
  source/script ambiguities. Added three document acceptance tests. The
  existing Golden dataset was not changed or re-scored in this subphase;
  a later explicit Phase 1B instruction can rebaseline it against the
  expanded contract. See [Phase 1A report](PHASE_1A_ACCEPTANCE.md).

## Dependency policy

Official documentation was checked before selecting the layout: uv's project
and lockfile guidance, FastAPI's request-model tutorial, SQLAlchemy's ORM
documentation, and Expo's SDK compatibility table. Exact application library
versions will be chosen at their implementation phase and committed in
`uv.lock` or `pnpm-lock.yaml`; no pre-release versions by default. Python
currently has no third-party runtime dependencies.
