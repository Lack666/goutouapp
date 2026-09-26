# Phase 0 acceptance

PHASE: 0 — Repository Bootstrap / Architecture  
STATUS: PASS

IMPLEMENTED: Immutable 63-file upstream snapshot; commit and SHA-256 manifest;
MIT attribution; monorepo boundaries; `AGENTS.md`, master plan, architecture,
initial Skill contract and ADRs; Make targets and portable verifier.

TESTS: `python scripts/verify.py verify` passed. Three Phase 0 unit tests
passed; the upstream `validate_skill.py` passed. The Phase 1 test was skipped
by the explicit phase gate. Snapshot hash and 20 knowledge / 23 practical
reference counts were checked.

ACCEPTANCE: Demo commands `python scripts/verify.py doctor` and
`python upstream/goutoujunshi/scripts/validate_skill.py` run locally without
credentials. Regression is the full active gate. Future backend, Agent,
mobile and Docker gates are named as deferred by the verifier.

ARCHITECTURE DECISIONS: ADR 0001 freezes upstream and preserves MIT; ADR 0002
separates transport, Agent, knowledge, import and mobile, with phase-aware gates.

KNOWN ISSUES: GNU Make and Docker are not installed in this Windows workspace;
`make.cmd` and the portable Python command execute the same gate. No service or app exists
in Phase 0. uv uses workspace-local cache/install paths in this environment
because the default Windows uv directories are inaccessible. No paid or
private credential is needed.

NEXT PHASE: 1 — finish and validate synthetic Golden Cases and Skill Contract.
