# Engineering instructions

This repository turns `upstream/goutoujunshi` into an independent AI Agent
Runtime and Expo mobile app. Read `docs/MASTER_PLAN.md`, `docs/ARCHITECTURE.md`,
and `docs/SKILL_CONTRACT.md` before changing behavior.

- Follow phases 0 through 12 in order. A phase closes only after code, tests,
  docs, a real demo, full applicable regression, and an acceptance report.
- Treat `upstream/goutoujunshi` as an immutable specification. Update it only
  through an explicit upstream sync with a new commit and manifest; retain MIT
  attribution. Put interpretation in contracts and ADRs.
- Keep Agent Runtime independent of FastAPI. Nodes take structured state and
  services, never HTTP request or response objects.
- Route knowledge deterministically to 1–3 references before considering RAG.
  Keep `FEATURE_RAG=false` fully functional.
- Put model credentials and calls on the server behind `LLMProvider`; support a
  keyless mock. Do not log private chat content or hidden chain of thought.
- Run safety before ordinary relationship analysis. Facts, inferences, and
  unknowns remain separate. Never turn an inference into a stored fact.
- Long-term memory requires explicit consent and person isolation. Never store
  entire chat records as long-term memory.
- The `evals/golden_cases.jsonl` examples are synthetic. Preserve their
  coverage and add cases for every behavior change.
- Use `uv` for Python and `pnpm` for TypeScript; commit lockfiles when a package
  is introduced. Do not invent success for unavailable external services.
