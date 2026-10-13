# ADR 0036 — Preserve upload contracts while closing private error boundaries

Date: 2026-10-13. Status: accepted for Phase 9A.

The upload design already separates transport, deterministic parsing, explicit
owner binding and atomic merge. Negative inputs revealed UTC date overflow,
PostgreSQL-incompatible NUL text, incomplete cleanup exception handling and
Uvicorn logging of exception details after the safe HTTP 500 handler. A check
followed by rename also allowed a publication race to overwrite on POSIX.

Keep the architecture and public schema. Reject NUL as fatal invalid encoding,
report time conversion overflow as invalid timestamp, use linear blank trimming,
publish artifacts by exclusive hard link, handle cleanup store faults with generic
warnings and normalize uploaded metadata DB failures to existing import_failed.
Sanitize Uvicorn exception records at the logger before its handlers; retain
operational non-exception startup messages and generic failure signals. Extract
the native private subprocess wrapper to test timeout/exit/OS failure suppression.

Consequences: the local store requires same-filesystem hard-link support and a
private OS root. No Python dependency, migration, format, Agent behavior or OpenAPI
operation is added. Detailed private exception traces are intentionally unavailable
in normal logs; privileged diagnosis must use a separately reviewed mechanism.
Existing Expo dependencies receive narrow compatibility patches required by
the unchanged root gate; see the Phase9A dependency audit for provenance,
exact release-age exceptions and native evidence limits.
Aggregate quotas/rate limits, active-body deadlines, bounded artifact maintenance
and production backup/restore remain explicit subsequent Phase 9 deployment work.
