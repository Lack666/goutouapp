# ADR 0042 — Audit source binding and unresolved Run recovery limits

Date: 2026-10-14. Status: accepted for Phase 9G audit scope.

The 9F evidence fingerprint includes server tests and root verification tooling.
Adding audit tests changes this fingerprint despite identical executable Android,
Backend, migration, dependency and native-helper inputs. Historical matrices and
native execution transcripts must remain immutable. Treating an old transcript
as a newly executed Android test is prohibited.

9G records an exact executable-input manifest from clean committed 64afd5d and
requires equality with all current executable inputs, including set membership.
It separately binds fresh current-source full 27-case admission, 44-case lifecycle,
39-case erasure and 7-case discovery/publication regressions to complete captured
logs, independent exits and execution-time fingerprints. Historical native paths,
steps, SQL/wire proofs, hashes and recorded historical source bindings still pass
the original gate. Any executable-input change requires fresh native evidence;
the compatibility path must reject it. No historical matrix/hash is rewritten.

Phase marker accepts 8/9G only after a full current-source pre-marker exit0 under
8/9F; an independent full post-marker exit0 under 8/9G is required for closeout.
Completed Phase9 remains rejected while the current Roadmap's account/lifecycle
and production privacy/recovery prerequisites remain. Public production is never
approved by local test success. Phase 10–12 remains deferred.

Long unresolved Run recovery remains an explicit design boundary, not an age
reset or a direct SQL repair. Existing target_busy preserves writer exclusion;
future terminal transitions require deployment-wide writer proof, exact Run/key
identity and reconciled Message/Memory outcomes. See AGENT_RUN_RECOVERY and R-10.
No production graph, service, schema, dependencies, Mobile source or frozen
knowledge is changed in this audit.
