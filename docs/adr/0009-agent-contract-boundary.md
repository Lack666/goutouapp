# ADR 0009: Agent state and public result boundary

Date: 2026-09-27

Status: Accepted for Phase 3A

## Decision

Use a total TypedDict for future LangGraph business state, initialized by one
function from a strict Pydantic input. Use separate strict Pydantic models for
public completed and failed results. Reuse the Phase 2C LLM protocol through
an injected dependencies value. Freeze only Golden-backed scenario, route,
risk, run status and memory decision vocabularies. Keep candidate type, risk
category and evidence provenance extensible until behavior work defines them.

## Why

This makes missing state defaults, FIU promotion, result serialization,
consent candidate confusion and database status drift testable before graph
execution. The existing AgentRun check already supports the four statuses, so
a schema migration would add risk without value. A completed result is not a
dump of conversation history or internal retrieved material.

## Consequences

Future nodes must obey the documented read/write matrix and safety-first
order. The result can be carried by API, WebSocket and eval code, but no such
transport is introduced here. Semantic behavior assertions and persistence
effects still require later runtime and memory phases.
