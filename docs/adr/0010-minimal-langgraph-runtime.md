# ADR 0010: Minimal standalone LangGraph execution

Date: 2026-09-27

Status: Accepted for Phase 3B

## Decision

Use LangGraph 1.2.12 `StateGraph` with the existing total `AgentState`, one
compile per `AgentRuntime` instance, and `ainvoke` for execution. The runtime
injects the Phase 2C LLM protocol and returns the Phase 3A `AgentResult` or
`AgentFailure`. Add only `run_id` and `run_status` to the internal state; the
public result schemas remain version 1. Compile without a checkpointer.
The version and Python requirement were checked against the official
[PyPI release](https://pypi.org/project/langgraph/1.2.12/); the builder,
compile, TypedDict state and conditional-edge usage follow the official
[Graph API documentation](https://docs.langchain.com/oss/python/langgraph/graph-api).

A synthetic metadata flag exercises the conditional safety edge. It is not
accepted as a real safety assessment. The ordinary branch uses a constant
scenario placeholder and a generic structured-output call. Nodes receive
projected read fields and must return exactly their declared write fields.

## Why

This verifies LangGraph compilation, async execution, dependency injection,
conditional safety precedence, failure mapping and run isolation without
claiming semantic competence. Runtime-owned state identity and status avoid
coupling execution to the database `AgentRun` row. Both branches terminate
without durable checkpointing or external service calls.

## Consequences

The demo result is not a production relationship response. Semantic safety,
scenario and FIU nodes must replace the fixtures before any user-facing
analysis API is introduced. Checkpointing, streaming transport, persistence,
knowledge routing and memory writes require separate designs and gates.
