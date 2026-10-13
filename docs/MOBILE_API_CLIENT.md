## Current Phase9E boundary

Backend-only guarded Dataset/Conversation erasure is documented in [ERASURE_API](ERASURE_API.md).
OpenAPI now has39 operations; the original36 contracts are preserved. Deleted
Conversation history/Agent REST/SSE returns404; erased canonical Dataset finalize
returns409 `dataset_deleted`, including duplicate same-scope transcripts.
App History/Settings disclose the absence of self-service chat/import/account
erasure. Existing Memory controls do not erase either history domain. External
erasure requires authoritative history refresh/reopen to clear cached rows/cursors.

# Generated Mobile API client — Phase 8B–8E

Phase8E explicitly enables the13 existing Memory operations on the same generated
36-operation client/session/transport. memoryAdapter validates public DTOs and
projects camelCase ViewModels; memoryErrors retains only safe public codes.
Owner/epoch/cancellation guards apply to reads and writes. Server confirmation
and idempotency remain authoritative. No generated schema/client edits or new
dependency are needed. See [Memory contract audit](MOBILE_MEMORY_INTEGRATION.md).

Phase8D also enables the existing generated ImportJob/binding/ready/finalize/cancel
and RelationshipMessage history routes through the same transport/session. Narrow
binary FormData serialization bridges the generator's binary-as-string field;
no second token manager or wire DTO. Import errors read only allowlisted public
codes. Memory routes were disabled at8D acceptance. See [8D](PHASE_8D_ACCEPTANCE.md) and
[import contract](MOBILE_IMPORT_UI.md). The earlier deferred-import text below
describes the8C historical boundary, superseded by8D.

Phase8C reuses the unchanged generated client for Agent REST and public Agent
History. App composition explicitly enables these paths and POST SSE in the same
authenticated transport. Import/Memory were disabled at8C acceptance;8D/8E now
explicitly enable the existing methods. Native streaming
uses installed expo/fetch with the same session/epoch/origin; the OpenAPI SSE string
has a separately audited V1 union. See [Chat](MOBILE_AGENT_CHAT.md) and
[streaming](MOBILE_STREAMING.md). The resource-only allowlist below is the8B default.

The only generation authority is `docs/contracts/openapi.json`, exported and
compatibility checked by `scripts/export_openapi.py`. Its 36 method/path operations,
including all 26 Phase 7D contracts, remain unchanged. No handwritten wire DTOs.

From the root, after `pnpm install --frozen-lockfile`:

```powershell
pnpm api:generate
pnpm api:check
pnpm --filter @goutou/mobile typecheck
```

`tools/api-codegen` owns openapi-typescript **7.13.0**, TypeScript **5.9.3** and
Prettier **3.8.1**. The generator's declared TS peer is 5.x, so this separate
workspace preserves Mobile TypeScript **6.0.3** without ignoring peers. All
versions and transitive dependencies use the root pnpm lock. Runtime uses
openapi-fetch **0.17.0**, the official typed client paired with generated `paths`.
See [official generation API](https://openapi-ts.dev/node) and
[official client usage](https://openapi-ts.dev/openapi-fetch/).

The generator emits `apps/mobile/src/api/generated/client.ts`: request/response
components, typed path/operation definitions, typed success and error statuses,
operation/auth inventory and callable `createApiClient`. OpenAPI required fields,
optional request association, required nullable response association, cursor and
JSON bodies retain their semantics. UUID formats become a template string type;
`asUUID` validates actual syntax at the application boundary and `asUUIDv4`
requires v4 creation IDs. Generation owns these outputs; never edit them manually.

Generated output includes the authority's SHA256 and uses explicit LF. `api:check`
regenerates in memory and compares every byte without writing files. Its three
Node tests prove two identical generations, changed input rejection and altered
output rejection. The drift case changes a schema in memory, leaving the formal
authority untouched. Compile-only negative cases cover required fields, null,
synthetic IDs and unknown routes under Mobile's strict compiler.

`ApiTransport` injects current Bearer credentials, strips caller Authorization,
captures session epoch, supports AbortSignal and a 12-second timeout through body
read, and cancels all scope requests on invalidation. Explicit cancellation/timeout
rejection races fetch/body reads, so an injected implementation that ignores abort
still releases its caller. Fetch is called without an
object receiver, required for Chrome's native implementation. HTTP errors become
owned safe messages; raw response error bodies and native exception text are
discarded. 401 invalidates only the initiating session epoch. 404, 409, 422, 503,
offline, cancellation, timeout and malformed response have distinct safe states.

Explicit logout/mode changes invalidate credentials and cancel requests immediately,
while `clearing` acknowledges pending durable credential removal. `no_token` follows
successful storage removal; a failure stays visible as `storage_error`. This avoids
claiming durable logout before an asynchronous SecureStore deletion finishes.

The default transport permits the nine resource create/list/detail paths.
Phase8C application composition also enables generated Agent REST, Agent History
and the existing POST SSE path using the shared session. SSE has its independent
V1 parser and run tracking. Generated Import/Memory types do not enable uploads
or Memory HTTP mutations. Native core SSE evidence is recorded in the 2026-10-10
revalidation section of [8C acceptance](PHASE_8C_ACCEPTANCE.md).

`EXPO_PUBLIC_API_BASE_URL` is a public origin, without credentials/query/path.
HTTP is permitted only in a development runtime for controlled local connections;
the origin must be loopback or a private IPv4 address for cleartext HTTP.
production requires HTTPS. No key, JWT, signing secret or database setting is read
from public Expo variables. Root verification includes generation, typed contracts,
Mobile tests and a real generated-client HTTP/PostgreSQL/browser gate.
