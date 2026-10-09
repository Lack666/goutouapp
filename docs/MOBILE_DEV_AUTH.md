# Mobile Development Session — Phase 8B

This is explicitly **Development Session / Connected Development Mode**. There
is no production login, registration, OAuth, token signer or refresh flow in the
App. JWT signature, issuer, audience, expiry and existing-owner checks belong to
the unchanged server verifier. Local payload decoding checks shape/expiry for UX;
it confers no authentication until an owned Person list probe succeeds.

Apply migrations and configure the private server `.env` as in
[authentication](AUTHENTICATION.md). Use the existing CLI in development:

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env python apps/server/dev_auth_cli.py bootstrap
uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env python apps/server/dev_auth_cli.py token --user-id <UUID>
.\make.cmd dev
```

The CLI signs an existing UUID for **15 minutes**, and prints it only to the
developer's invoking terminal. Transfer that credential manually into Settings →
Development Session → Connected Development Mode → hidden JWT input → verify.
Do not copy its terminal output into tickets, screenshots, committed fixtures,
public Expo configuration or logs. The input clears before validation begins.
The Mobile bundle holds no signer or global test token.

Native uses Expo SecureStore **57.0.4**, matching the installed SDK 57 compatibility
map, with iOS `WHEN_UNLOCKED_THIS_DEVICE_ONLY` and Android's system secure storage.
The plugin config retains its default encrypted-backup exclusions. SecureStore is
supported by Expo Go without biometric `requireAuthentication`; see
[official SecureStore API](https://docs.expo.dev/versions/latest/sdk/securestore/).
No AsyncStorage credential fallback exists. Native restart reads the secure item
and rechecks it with the server; logout/invalidation delete it. Actual native
storage persistence is **NOT RUN** on this host; adapter read/write/delete tests,
Expo Doctor and Android JS export are separate evidence.

Web/default uses only a closure-held volatile token, with no localStorage,
sessionStorage or cookies. A browser reload returns to Demo and needs a new manual
session. A failed storage operation is explicit `storage_error`, with a clear
session action to retry removal. Tokens are absent from UI state snapshots,
resource state, error messages, test snapshots, analytics and console output.

Session states: no token, checking, authenticated development session, expired,
invalid, network unavailable and storage error. A deadline timer expires idle
credentials; foreground resume and each HTTP request recheck expiry. Expiration
requires a new CLI credential; no silent refresh/bypass. A server 401 clears the
credential and all authenticated resource state. The active epoch prevents an old
401 invalidating a newly connected identity.

Logout, identity replacement and Demo/Connected switches synchronously clear all
lists, details, resource selection, cursors, create attempts and safe error state,
abort HTTP requests and remount scope-local form/controllers. The reset also
discards the old navigation stack and resource query IDs, returning to Settings.
Credential deletion is serialized with writes so delayed completion cannot resurrect an old
session. Old responses cannot update state after the epoch changes.

For Expo Web, set a restricted development origin in the **server** config:

```powershell
$env:DEV_CORS_ORIGINS='["http://localhost:8087"]'
```

Only explicit loopback origins with ports are accepted in development/test.
Wildcard, remote origins and development CORS in production/staging are rejected.
CORS does not allow cookie credentials or bypass JWT. Default is an empty list.
The automatic connected smoke uses localhost:8088 and its disposable backend
on 127.0.0.1:8018; it transfers CLI tokens over an internal process pipe only,
with tracing/video/screenshots disabled. It creates and drops a separate migrated
PostgreSQL database, and never reads a production credential or calls an LLM.
