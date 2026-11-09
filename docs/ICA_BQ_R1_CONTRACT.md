# ICA-BQ-R1: offline quote protocol repair (2026-11-09)

This bounded continuation follows ICA-BQ batch-v1 QUALITY FAIL / PARTIAL.
It changes evidence transport and verifies engineering with Mock and signed
PostgreSQL. It does not regrade model quality or reuse the prior CNY20 paid-batch
authorization. No external Provider calls, ICA-C UI, long-range expansion,
Phase12 or marker changes are in scope. Historical evaluations remain intact.

## Versioned protocol

`span-v1` remains an explicit legacy replay protocol: model evidence includes
alias, speaker, quote and numeric start/end. Existing rejection regressions still
exercise it. New Runtime and server Mock executions use `quote-v2`: model evidence
contains exactly alias, speaker and a nonempty quote of at most160 code points.
Additional numeric span fields are rejected, never silently accepted or retried.

For quote-v2, the server first resolves the alias within the current trusted
context, checks the local chunk core/halo allow set and speaker, then searches
only that message's unmodified body for a unique exact substring. Zero matches,
multiple matches (including overlapping matches), unknown aliases and wrong
speakers fail closed. No fuzzy matching, Unicode normalization, trimming,
cross-message search or guessing. Distinct UUIDs with identical bodies remain
distinct occurrences. The resulting canonical start/end use Python Unicode
code-point indexing and pass the existing source/range validator.

All model stages with evidence use strict quote-only wire schemas. Internal
candidate state, stored reports, evidence HTTP requests and generated clients
retain the canonical span schema. Model-visible candidate/report payloads project
canonical refs to quote-only refs. Server checks still compare canonical facts
exactly. Resolver code and protocol are bound to execution fingerprints, consent,
actual serialized input admission and callback accounting. Resolution and all
validators precede successful call receipts. No new permissions or migrations.

Normal safety decisions require no risks; all nonnormal decisions require risks.
Content Review requires all four checks true and no reason codes. A hypothesis
may be explicitly uncertain, but unsupported attribution, omitted counterevidence
or unresolved safety still rejects publication. No validator is relaxed.

## Evidence and acceptance

Run parser/scope/evidence and existing ICA/Agent safety regressions, new Unicode
and adversarial quote tests, signed PostgreSQL execution/lifecycle and Memory P0,
OpenAPI/client consistency and targeted formatting/type checks. Preserve prior
signed-demo artifacts: test outputs go to temporary or new R1 directories.

Replay only actually recorded stages from the disclosed batch-v1 responses.
Explicit migration removes span fields only from complete v1 evidence objects;
retain original and migrated hashes. Exhausted recordings remain incomplete;
never synthesize later candidates, safety verdicts or approving reviews. These
cases are development data now, not independent holdout quality evidence. Any
future live batch requires a fresh frozen holdout and separate budget approval.

Engineering acceptance requires deterministic quote resolution, strict schema
and source boundaries, signed DB lifecycle regression and Provider calls0.
Engineering PASS cannot change ICA-BQ QUALITY FAIL / PARTIAL or human-review
pending. Stop after R1 delivery.

## References and independent implementation

The [W3C Web Annotation TextQuoteSelector](https://www.w3.org/TR/annotation-model/#text-quote-selector)
documents exact quotation as an anchoring approach and distinguishes position
selectors. R1 borrows that concept only; it is not a W3C implementation or
conformance claim. [Python str.find](https://docs.python.org/3/library/stdtypes.html#str.find)
supports deterministic substring location. The resolver is an independent,
dependency-free implementation. No external project source is copied. The
frozen MIT Skill and existing knowledge routing remain unchanged.
