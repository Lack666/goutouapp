# Phase 0 acceptance

PHASE: 0 — Repository Bootstrap / Architecture  
STATUS: PASS

IMPLEMENTED: Immutable 63-file upstream Skill snapshot in
`knowledge/goutoujunshi`; commit and SHA-256 manifest; MIT attribution;
requested monorepo boundaries; `AGENTS.md`, `.env.example`, master plan,
high-level architecture, initial Skill contract and ADRs; Make targets and
portable verifier.

TESTS: `make doctor` and `make verify` passed through the Windows Make shim.
Five unit tests passed, including Phase 1 regression; the upstream
`validate_skill.py` and the 55-case annotation validator passed. The snapshot
hashes match its manifest, and all 63 preserved files match the local upstream
checkout byte for byte (zero mismatches). Git ignore rules for `.env` and
`.env.local` passed.

ACCEPTANCE: `make doctor` reports installed Git, uv, Node, pnpm, Python and
the missing Docker dependency. `make verify` runs locally without credentials.
Regression is the full active Phase 0/1 gate. Future backend, Agent, mobile
and Docker gates are named as deferred by the verifier.

ARCHITECTURE DECISIONS: ADR 0001 freezes upstream and preserves MIT; ADR 0002
separates transport, Agent, knowledge, import and mobile, with phase-aware gates;
ADR 0004 aligns the Phase 0 directory layout and keeps architecture high-level.

KNOWN ISSUES: GNU Make and Docker are not installed in this Windows workspace;
`make.cmd` executes the same targets. The doctor reports Docker as missing,
which will block the PostgreSQL demo in Phase 2 until Docker is available.
No server, Agent or mobile app runs yet. No paid or private credential is needed.

NEXT PHASE: 1 — finish and validate synthetic Golden Cases and Skill Contract.
