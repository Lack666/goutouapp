# ADR 0032 — Generated client, development credential and resource boundaries

Status: accepted for Phase 8B.

Use the unchanged 8A OpenAPI as the sole TypeScript generation input. A separate
pnpm workspace pins the generator and its compatible TS5 peer, preserving Mobile
TS6/SDK57. Generate contracts and callable openapi-fetch client together, with a
byte-level check, source hash and LF. No second wire schema or generated-file patch.

Native SecureStore and volatile Web storage implement one injected credential
interface. User-entered development JWTs require a real resource probe. Server
verification remains authoritative; there is no production login, signing or
refresh. Credential writes/deletes are serialized. Session epochs cancel requests,
clear controller caches and remount forms; delayed responses and old 401s cannot
cross an identity switch.

Generated DTO adapters feed existing UI ViewModels. Async controllers own resource
pages, details, explicit binding and immutable same-ID create retry. Pending actions
are in-memory; server retry reservations are row lifetime. Deferred business paths
fail closed rather than use Demo in Connected Mode. Transport has a resource-only
allowlist. No Agent, stream, imported history, upload or Memory network integration.

The only server change is explicit loopback development/test CORS configuration,
with no wildcard or deployment allowance and no JWT/ownership/contract change.
Real socket/CLI JWT/PostgreSQL/Chrome gates establish 8B integration. Native storage
and Android connected behavior require separate on-device evidence; Web or export
cannot substitute. The whole Phase 8 remains in progress.
