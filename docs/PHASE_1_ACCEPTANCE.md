# Phase 1 acceptance

PHASE: 1 — Skill Contract + Golden Evaluation Dataset  
STATUS: PASS

IMPLEMENTED: Completed versioned Skill Contract, 55 synthetic Golden Cases,
19 source reference aliases, an annotation validator, and ADR 0003. The cases
cover 21 categories and 13 high-risk inputs, including reply, ambiguity,
invitation, conflict, imbalance, breakup, reconciliation, betrayal, online
relationship, chat import, MBTI, manipulation, memory, violence, coercion,
stalking, fraud, privacy and self-harm.

TESTS: `make verify` through the Windows `make.cmd` shim and
`python scripts/verify.py verify` passed after setting
`completed_phase` to 1. Four unit tests passed, including the dataset gate;
upstream validation passed. `python evals/validate.py` passed with 55 cases,
21 categories, 13 high-risk cases and 60 distinct assertion labels.

The Phase 0 directory alignment was revalidated later with five unit tests;
the Golden Case count and upstream file hashes remain unchanged.

ACCEPTANCE: `python evals/validate.py` is the runnable Phase 1 demo. It checks
data shape, IDs, breadth, real upstream reference paths, safety-first routing,
zero high-risk memory writes, consent for positive memory writes, and evidence
annotation structure. It does not claim behavioral Agent correctness before
the Agent exists. Earlier Phase 0 tests remain green.

ARCHITECTURE DECISIONS: ADR 0003 uses synthetic contract evaluation before
implementation; actual behavioral scoring starts when the runtime exists.

KNOWN ISSUES: The current eval checks annotations, not model output. The
backend, LangGraph, mobile, Docker and full live streaming gates begin in
their scheduled phases. No private credentials or paid services are needed.

NEXT PHASE: 2 — FastAPI + PostgreSQL Backend Foundation.
