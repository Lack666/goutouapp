# ADR 0002: runtime boundaries and staged gates

Status: accepted, Phase 0.

The monorepo separates `apps/server`, `apps/mobile`, `packages/agent`,
`packages/knowledge`, and `packages/chat_import`. FastAPI is a transport around
the independent Agent. Phase-aware verification reports future stages as
deferred while still running every available gate and the upstream validator.
An empty placeholder directory never counts as a functional phase demo.

The pinned JavaScript package manager is pnpm. Python uses uv. The initial
Python project has no third-party dependencies; application versions will be
locked when their phase begins, after checking current official compatibility.
