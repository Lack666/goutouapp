# ADR 0029: Expo shell with injected local ViewModels

Status: accepted for Phase 7A, 2026-10-08 (Asia/Shanghai).

Phase 7 is the Expo React Native MVP; Phase 8 owns real Mobile transport.
Choose stable Expo SDK 57 with Router, strict TypeScript and the existing pnpm
11.25.0 workspace pin. Use SDK-recommended native versions and one root lockfile.
Do not copy a new standalone repository or add an API/auth framework in 7A.

Use a Home Stack launch surface with five reachable leaf routes and a not-found
recovery route. This keeps small-screen navigation readable and lets leaves
return through stack history or Home when deep linked. Native Android back
support comes from Stack; this phase's acceptance platform is Expo Web.

Inject a small synchronous read-only ShellDataSource at the root layout. Screens
consume a discriminated UI state/ViewModel through hooks, never import fixtures.
The sole implementation is explicitly local Demo, with no invented business
records or success states. Network DTOs, async loading, JWT/session storage,
OpenAPI client and progress SSE belong to Phase 8 adapters.

Use central light/dark design tokens and a session-scoped system/light/dark
preference. State preview and retry have real local effects; unimplemented
business actions are disabled. Avoid unused global state/query libraries and
persistent preferences until a feature requires them.

Static gates run in root verify even before the marker advances by detecting
the actual Mobile package. Real Expo Web smoke is a separate explicit gate,
not hidden behind a typecheck or silently replaced by an export. The marker
remains completed_phase=6 and advances only completed_subphase to 7A after
all gates pass. Android is NOT RUN and Phase 7B/8 stay deferred.
