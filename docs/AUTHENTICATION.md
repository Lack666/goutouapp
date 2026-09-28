# Phase 4B authentication

The Agent REST endpoint accepts one `Authorization: Bearer <JWT>` credential.
The Phase 4C POST streaming endpoint uses the identical FastAPI dependency and
verifier before any SSE headers are sent; it does not accept URL query tokens
or a trusted user header. See [Streaming API](STREAMING_API.md).
FastAPI's HTTP Bearer dependency extracts it. `JWTBearerVerifier` verifies its
HS256 signature using a server-only `AUTH_JWT_SECRET`, then requires `sub`,
`exp`, `iss` and `aud`. The issuer and audience must match
`AUTH_JWT_ISSUER` and `AUTH_JWT_AUDIENCE`. The algorithm allowlist is fixed to
HS256; token headers cannot choose another algorithm. `sub` must parse as a
UUID. The verifier returns a typed `VerifiedIdentity`; the trusted adapter
issues `AuthenticatedActor` from that identity. No request body or trusted user
header can issue an actor.

The secret must be at least 32 UTF-8 bytes. Missing or short configuration
leaves the business endpoint unavailable with a generic 503. App startup,
`/health`, `/ready` and `/api/v1/status` remain independent of authentication
configuration. No credential verification contacts an external identity
service. The user must already exist in PostgreSQL; a validly signed token for
an unknown UUID yields a generic 401 and never creates an account.

Authentication identifies the user. `AgentService` still checks Conversation
ownership and any expected relationship scope. The REST adapter maps both a
missing and foreign Conversation to the same 404 envelope, so it does not
reveal another user's identity or whether a guessed ID exists.

Missing, malformed, expired, incorrectly signed or invalid-claim credentials
yield `401` with `WWW-Authenticate: Bearer` and the same generic error body.
No JWT, Authorization header or signing key is written to normal logs or error
responses. A token is never issued by the production API. There is no
`X-User-ID` development bypass, refresh token, password login or OAuth UI.

The implementation follows [PyJWT's required-claim and decode guidance](https://pyjwt.readthedocs.io/en/latest/api.html)
and [FastAPI's HTTP Bearer security scheme](https://fastapi.tiangolo.com/reference/security/).
Dependency version `PyJWT>=2.15.0,<2.16` is pinned through `uv.lock`.

For local development, set a private random `AUTH_JWT_SECRET` in ignored
`.env`, apply Alembic migrations, then use the development-only CLI:

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env python apps/server/dev_auth_cli.py bootstrap
uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env python apps/server/dev_auth_cli.py token --user-id <UUID-from-bootstrap>
```

The CLI refuses `APP_ENV` other than `development` and signs only an existing
local user. It prints a 15-minute token to the invoking terminal so it can be
used for a manual request; do not paste it into logs or commit it. The fully
offline [REST demo](AGENT_API.md#offline-rest-demo) uses a separate synthetic
secret and disposable PostgreSQL database.
