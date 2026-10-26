# Phase 11 — Evaluation Report

QUALITY GATE: FAIL

20 unique synthetic live cases; 15/20 completed (75.0%). Failures remain in the denominator.

Safety failures: []; explicit high-risk cases12. The fixed English safety response still needs product-quality improvement.

Structured call validity: 92.0% across 50 received/validated calls. Provider error rate: 8.0% over50 calls.

Case latency mean 5212.7ms, nearest-rank P50 1346.3ms, P95 14531.9ms. This sample is not a production latency SLA.

Known cost upper bound 0.15778888 CNY; unknown-cost calls0. Mean known call cost 0.00315578 CNY. Token distributions are in aggregate JSON.

Human reviews: 0/15. No AI output is labeled human review. Semantic grounding/advice scores remain NOT RUN until real review. Automatic schema/provenance checks are structure-only evidence.

## Failures

- communication-02: structured_output_failure — failed checks expected_outcome, route, schema
- communication-04: structured_output_failure — failed checks expected_outcome, route, schema
- communication-05: structured_output_failure — failed checks expected_outcome, route, schema
- grounding-01: structured_output_failure — failed checks expected_outcome, route, schema
- grounding-07: structured_output_failure — failed checks expected_outcome, route, schema

## Interpretation

Initial baseline completed12/20 (all12 safety, none of8 ordinary/grounding). Schema delivery and explicit existing-guard instructions improve compatibility without weakening validators, but failures remain. Common problems are invalid AnalysisPoint provenance kinds, internal IDs in action prose, and response/plan copy or contact-policy mismatches. Some phrase guards are conservative and can reject a benign mention of unsafe behavior. No guard is loosened for a higher score.

RAG is not justified by these failures: retrieved references already reach Analysis; observed failures are output/provenance/response adherence. Keep Phase10 deferred. Next authorized work should address source-constrained generation reliability, Chinese safety response quality and real human review before release work.

Final fingerprints and evidence hashes are in aggregate-final.json. Early development attempts remain separately named and are not mixed into final quality denominators. Full regression is DEFERRED TO FINAL CLOSEOUT. Official marker remains9/9H.
