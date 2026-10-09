# ADR 0031: Public resource acquisition and creation retries

Date: 2026-10-09. Status: accepted for Phase 8A.

Phase 7D correctly identified missing Person, Relationship, Conversation and
Agent history resources. Phase 2 persistence already supplies their owner-scoped
models, repositories and composite constraints. Phase 4 Agent runs require a
pre-existing Conversation. Mobile must obtain real resources before integration.

Expose ten minimal signed operations over those existing rows through a separate
transport-independent ResourceService. Reuse the repository creation/get helpers;
add bounded owner queries and public projections. Conversation remains optionally
relationship-bound. No inferred profile fields, new Agent behavior or migrations.

Require a caller-retained UUID v4 for every create. Existing primary keys serve as
durable reservations; under a cross-worker transaction advisory lock, matching
fields replay and changed fields conflict. Owner checks remain independent. This
avoids redundant receipts/fingerprint storage and AgentRun reuse. Replay lasts
while the resource row exists; future deletion must specify retry/tombstone policy.

Use bounded ascending timestamp/UUID keysets with opaque context-bound navigation
cursors. Every page enforces owner scope independently; cursors grant no authority.
Reads are committed/live per request, without a retained snapshot. Agent messages
and imported relationship messages keep distinct models and APIs.

Freeze the actual 26-operation Phase 7D contract hashes and export deterministic
OpenAPI with ten additions. This is 8B's generation input; client/session/SSE
consumption remains deferred. See [resource contract](../RESOURCE_API.md).
