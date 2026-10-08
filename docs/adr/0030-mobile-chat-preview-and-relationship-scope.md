# ADR 0030 — Ephemeral Chat preview and scoped profile presentation

Date: 2026-10-08. Status: accepted for Phase 7B.

## Context

Phase 7A supplies a local Expo Stack/theme/provider. Phase 7B needs operable Chat
and Relationship UI without prematurely implementing Phase 8. Imported history
speakers differ from Agent conversation roles. Existing public REST/SSE carries
status and a complete answer, not token streaming or structured FIU/profile data.

## Decision

Extend the injected read-only ShellDataSource with typed feature templates.
Keep person/profile and Agent message domains separate. Screen code does not
import fixtures. A single FlatList scrolls Chat content, with a separate fixed
multiline composer. Append only a local user message, retaining a truthful Demo
notice; assistant messages require an explicit synthetic-template replacement.
Local state belongs to a mounted route; changed relationship scope remounts the
Chat controller. Profile selection derives all fields from one selected model.

Use a manually controlled finite run presentation union, independently of
messages. No timer/transport advances it. A completed preview renders only
synthetic FIU with provenance/alternative/unknown semantics. Safety is a neutral
reserved notice. Pending confirmation cannot execute anything. Retry resets
only the local presentation state. The future Phase 8 controller/adapter must
respect progress-then-final SSE and server-issued confirmation challenges.

Retain all 7A tests (update the intentionally enabled local-input expectation),
add dedicated Chat/Profile tests and an explicit focused root gate. Live Expo
Web smoke stays separate and covers both themes and three mobile widths.

## Consequences

No new dependency/SDK, server change, prompt, private fixture, network request,
auth store, message history or memory write is needed. Drafts disappear after
reload or scope remount, and this policy is explained to users. Large-list
checks establish bounded mounting and ordering, not device performance.
RN Web requires an explicit aria-pressed mapping for selected buttons; native
selected semantics remain. Android keyboard/Safe Area/TalkBack await hardware.
Real FIU/profile public contracts remain a Phase 8 coordination item.
