# ADR 0007: Typed LLM boundary over HTTPX

Status: accepted for Phase 2C (2026-09-27).

## Decision

- Use a typed `LLMProvider` protocol and one `OpenAICompatibleProvider` built
  on stable HTTPX 0.28.1. The standard text Chat Completions wire format is
  sufficient for this foundation; vendor SDKs stay out of application code.
  HTTPX is a runtime dependency in the root uv project and single lockfile.
- Use `MockLLMProvider` queues as the keyless, offline contract test double.
  Tests inject chat responses, stream chunks, structured values and errors.
  Missing queued output is a configuration error, so tests do not silently
  pass with a generic response.
- Normalize response fields at the provider boundary. Drop unknown metadata
  and hidden reasoning fields. Validate structured content strictly against
  the caller's Pydantic model after requesting JSON object mode; the schema is
  not sent to the endpoint. Do not invent missing fields.
- Parse provider SSE frames into `StreamChunk`. Treat malformed frames and
  missing `[DONE]` as invalid responses. Preserve optional usage when supplied.
- Map transport/status/validation failures to fixed project exceptions without
  raw response bodies, request messages, URLs, or underlying exceptions. Do
  not retry automatically: timeout, authentication and rate limit failures need
  different future policies and retrying streams may duplicate output.
- Construct a default HTTPX client per operation and close it afterward. Tests
  may inject a caller-owned client/MockTransport; the provider does not close
  an injected client. No client or network call is created at server startup.

## Consequences

The current surface is text-only Chat Completions. Tool calls, multimodal
content, Responses API features, live provider certification, prompt design,
Agent behavior and API/WebSocket exposure are separate future decisions.
JSON object mode alone cannot enforce a schema at the model; strict local
validation turns mismatches into controlled errors. See
[LLM_PROVIDER.md](../LLM_PROVIDER.md) for configuration and error types.
