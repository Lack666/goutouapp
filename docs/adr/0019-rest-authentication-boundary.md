# ADR 0019 — Signed Bearer authentication and thin REST execution

Date: 2026-09-28. Status: accepted for Phase 4B.

## Decision

The Agent business endpoint is `POST /api/v1/conversations/{id}/agent-runs`
and returns 200 after synchronous execution. FastAPI validates a signed Bearer
JWT through a dedicated verifier before issuing the typed actor. PyJWT checks
HS256 signature, UUID subject, expiration, issuer and audience; all claims are
required. The signing key is a server-only `SecretStr` of at least 32 bytes.
An unknown subject is refused by the application service without account
creation. Missing auth configuration leaves only the business endpoint
unavailable; process health stays available.

The route maps request and response schemas and calls `AgentService.execute`
once. Composition and a lazy per-app compiled runtime live in the dependency
layer. The endpoint does not query ownership, assemble history, persist rows or
call LangGraph. Foreign and missing conversation IDs share a 404 response.
All errors use the existing envelope, with a Bearer challenge on 401. A failed
run may expose its run ID and recovery status without raw exception detail.

`operation_key` can be passed through, but no persistent retry guarantee is
offered until Phase 4D. Phase 4C owns network streaming and disconnect policy.

## Consequences

A signing key and already-created User are required for business requests.
There is no account or token issuance HTTP API. The development-only CLI can
bootstrap a local user and sign a 15-minute test token; it refuses non-development
environment settings. App startup and the three public status endpoints remain
independent of JWT and PostgreSQL availability, except `/ready` keeps its
existing database check.
