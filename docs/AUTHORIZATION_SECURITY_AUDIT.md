# Phase 9B authorization audit

Scope: existing 36-operation FastAPI application and development Auth Contract.
Machine inventory: [AUTHORIZATION_API_INVENTORY.json](AUTHORIZATION_API_INVENTORY.json),
generated from actual Router endpoints/OpenAPI and checked for complete coverage.
Each operation records method, JWT, actor source, path/body IDs, parent validation,
foreign response, public DTO, sensitive fields, side effects and service/test paths.

Public: GET /health, GET /ready, GET /api/v1/status. Readiness performs SELECT 1
and returns a fixed status; status exposes environment only. Framework /docs,
/redoc and /openapi.json are also public schema surfaces, outside these 36
operations; they expose no stored data. All other 33 operations are signed and
owner-scoped; Undo/delete execute additionally require server guards. Preparation
creates expiring owned confirmation metadata, not a deletion.

JWT remains HS256 only, private >=32-byte secret, exact issuer/audience,
required sub/exp/iss/aud and UUID subject. Existing PyJWT validates supplied
nbf/iat. Unsigned, forged, tampered, malformed, expired, future or foreign claims
cannot authorize access. No header/query owner authority or token issuer API.
Service User checks return401; owned FK-backed lookups may return owner-neutral
404 for an unknown signed subject. Neither creates an identity or grants access.
Development CLI is refused outside APP_ENV=development. Production account,
refresh and revocation work remains excluded; authentication policy is unchanged.

ResourceService validates owned parents, locks creation UUIDs and refuses foreign
reservations before replay/conflict. Repository lists/details filter owner.
Resource DTOs omit ORM owner/private fields. Conversation Message history
validates its parent; cursor binds owner/domain/Conversation. Composite DB
constraints preserve associations. Native positive tests create actual resources;
signed A/B negative tests verify detail/list/parent/UUID isolation.

AgentService validates owned Conversation before operation-key/run lookup;
fingerprints include actor/scope/payload and queries include owner/Conversation.
Expected Relationship and optional Person must match the owned binding.
REST/SSE share preparation: foreign errors occur before private SSE opening.
Recent/replayed Messages and AgentRun queries authorize independently. Both
first-REST/first-SSE and cross-transport replay are tested; B's same key is a
separate namespace, never a credential or route to A's replies/history.

Import queries/locks owned Job/speakers before revision/state/targets. Binding
validates owned Person/Relationship and their association. Finalize repeats
readiness/integrity under lock; History validates owned Relationship and filters
both owner and parent. No RelationshipMessage detail/mutation/download API
exists. Retained9A tests cover expired/cancelled/completed Jobs, stale revisions,
tampering, file limits and fault cleanup. Import remains outside Agent/Memory.

MemoryControl checks User and owned records/control; optional filters validate
owned Person/Relationship and association. MutationService locks User; Undo
requires the exact latest owner-bound operation/record and scoped key. Challenge
lookup includes owner, then action/target/scope/snapshot/count/expiry/consumption.
Receipt queries include owner+ID/key, expose metadata and never Memory content.
Foreign/missing IDs use uniform envelopes; foreign/missing challenges409 reveal
no private existence. Delete-one scope mismatch is not-found. Delete-person/all
erase scoped primary Memory/undo only, not identity/history/imports/backups.

Reproduced fixes: malformed Memory UUID cursor caused500; position-only Import
History/Memory cursors accepted another navigation scope while SQL stayed owned;
reusable Transport could invoke a stale SSE callback before rejecting changed
epoch. Controllers already cancelled/guarded generation; no new-owner UI leak
was observed. Minimal fixes: typed bounded opaque v2 owner/filter cursors and
epoch rejection before every SSE callback. Old cursors require Refresh; order,
page sizes and DTOs stay unchanged. Cursor digest is navigation consistency,
not authentication/integrity: owned SQL remains authoritative. See ADR0037.

Mobile: SecureStore-only token; serialized durable writes/clears; immediate
volatile invalidation; explicit storage_error when clear fails; local expiry UX
plus server authority; epoch/generation/cancellation on requests and callbacks;
scope/cache/cursor/pending/challenge purge on account switch; foreground check.
Retained sessionIsolation/connected*/full integration suites and new authPrivacy
test verify these controls. Restart loses volatile pending descriptors and needs
authoritative inspection; no automatic new-key replay or production guarantee.

New backend tests use actual signed JWT→FastAPI→services→migrated disposable
PostgreSQL. Only Mock/provider/fault sources are replaced; no authentication
dependency_override or Guarded Mutation bypass. Execution: PHASE_9B_ACCEPTANCE.
