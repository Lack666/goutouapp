# Phase 11 — Agent Evaluation & Observability

Authorized 2026-10-26. Scope: assess the existing standalone Agent, not build
another analysis product. Optional Phase10 is DEFERRED by explicit user decision.
Its original requirements remain in MASTER_PLAN; evaluation can justify resuming it.
Official `project-phase.json` remains9/9H. No historical0–9 acceptance is changed.

## Gates and work sequence

Preflight → adapter/trace/budget → synthetic dataset/harness → focused unit and
signed PostgreSQL tests → live smoke → limited live evaluation → report and review
packet. Ordinary tests and root verify never opt into paid calls. Full root,
Mobile, Web and Android replay is deferred to final project closeout, as explicitly
authorized for this phase. Quality failure is reported independently of functional
tooling completion. Never claim formal Phase11 PASS or advance the official marker.

## Preflight findings

- Provider protocol already has chat/stream/structured_output. Mock uses queued,
  deterministic schema fixtures, not a semantic classifier. Compatible adapter
  uses HTTPX, JSON object mode, Pydantic validation, safe errors and discards vendor
  reasoning fields. Before11 no real model quality evidence existed. Structured
  schema was not sent to the vendor and structured call usage was inaccessible.
- Actual graph: normalize_input, load_memory, safety_check, classify_scenario,
  extract_fiu, knowledge_router, load_references, relationship_analysis,
  action_planner, response_generator, memory_intent_resolver,
  memory_candidate_extractor, memory_persist, safety_finalize. No load_profile
  implementation exists despite its design row. Runtime owns finalization.
- SafetyResult is model-classified, then a deterministic conditional edge skips
  all ordinary analysis/planning/Memory on safety. The final safety response is a
  fixed English template, not a generated Chinese crisis response. Schema checks
  cannot establish semantic classifier accuracy.
- FIU/Analysis/Plan/Response use separate prompts and formal Pydantic schemas.
  Independent validators enforce provenance IDs, kinds, contact policy, exact
  approved copy and conservative phrase guards. These guards remain unchanged.
- Reference routing is deterministic with bounded, hash-checked frozen excerpts.
  Imported RelationshipMessage never enters Agent context. No imported-source
  attribution or RAG claim is made.
- Memory load precedes safety but is scoped/read-only; writes follow the ordinary
  response, with server consent, pause, owner/subject/source/size guards. Destructive
  intents require the existing separate server confirmation API. Natural language
  cannot authorize owner changes or confirmed deletion.
- AgentService commits a user Message and AgentRun before graph execution, then
  atomically commits a validated assistant Message and completion. REST and POST
  SSE use signed JWT ownership. Immutable operation keys replay committed results;
  failed, active and unknown outcomes do not silently execute again. A post-answer
  SSE disconnect can preserve a committed answer while canceling later work.
- Golden83 and frozen upstream remain untouched. New60 cases live separately.
  Existing Mock Golden and safety tests prove wiring/guards, not external quality.

Read contracts: AGENTS, MASTER_PLAN, ARCHITECTURE, SKILL_CONTRACT,
PHASE_9_FINAL_ACCEPTANCE, AGENT_RUNTIME, LLM_PROVIDER, MEMORY, AGENT_SERVICE,
STREAMING_API and IDEMPOTENCY; inspected implementation and targeted tests.

## Boundaries

No dependencies, DB migration, endpoint, Mobile behavior, new infrastructure,
RAG, imported analysis, public deployment or Phase12. Local native PostgreSQL16.15
is the tested disposable database environment; Compose18 is not claimed tested.
The existing local server was started on loopback5433; the `.env` Compose user did
not exist there, so isolated tests explicitly used the native `postgres` role.
Existing databases were not erased. Git initially had only untracked api.txt;
it is now ignored and is never staged or printed.
