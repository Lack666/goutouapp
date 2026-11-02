# ICA-A READINESS FAIL / PARTIAL

2026-11-02. Base HEAD `1f4e000` (working tree implementation, uncommitted).
This is an incomplete ICA-A delivery, not a completed stage or authorization for
ICA-B. Official marker remains 9/9H. Phase11 QUALITY FAIL, historical human scores,
11R Memory P0 evidence, Phase10 DEFERRED and Phase12 PENDING are preserved.

## Delivered and checked

- Independent Python ChatLab JSONL v0.0.2 adapter based on the fixed public field
  specification at ChatLab commit bf8d5ac77443512b9973ff3a236f258424202bbc.
  No ChatLab AGPL or Weport CC BY-NC-SA implementation copied. Existing local
  incremental UTF-8 line reader reused. No new dependencies or upstream edits.
- Header/member/message, stable sender binding labels, physical source lines,
  optional external message/reply/type provenance, seconds to aware UTC,
  normalized empty/media bodies, explicit fatal malformed records, bounded
  members/issues/lines, retained duplicate text occurrences, reverse-time warnings.
  WeFlow generator accepted. Ordinary JSON is not supported.
- Shared format selection at upload registration and merge reparse, API allowlist,
  optional SQL provenance migration and staging promotion, Mobile response adapter.
  Migration and JSONL HTTP/finalize/merge are **not verified against PostgreSQL**.
  Mobile picker/controller still submit Markdown: JSONL UI support is incomplete.
- Pure AnalysisScope, ChunkManifest, pending-only StageReceipt, ImportedChatContext,
  local 3/7/custom calendar windows, session/turn splitting, continuation, bounded
  halo, exact Core partition, UUID/code point evidence validation and snapshot hash.
- Single Dataset owner/person/relationship-filtered SQL keyset reader (500 rows/page,
  >10,000 rejects). Job lock requires a caller-owned transaction. SQL execution and
  EXPLAIN are unverified; this is not yet a signed scope API.
- Independent message/byte/chunk limits reject whole selections. No last-200 fallback.
  Versioned v3 contract preserves v2. 3K+8 budget planner includes serialized escaping,
  repeated halo, per-request prompt/output caps and conservative global-call reserves.
  Tariff is caller supplied; demo tariff is synthetic, not an actual model price.

## Actual Preview Demo

`uv run --no-sync python apps/server/ica_scope_demo.py` exited 0.
Artifacts: `evidence/ica-a-v3/preview-3d.json`, `preview-7d.json` include scope,
snapshot digest, full manifest, preview and synthetic budget plan.

- Asia/Shanghai, prepare 2026-11-02T10:00:00Z. 3-day window begins
  2026-10-30T16:00:00Z; 900 messages, 19,800 normalized bytes, 450/self and
  450/person, K=5, planned requests=23, exact Core union 900/900.
- 7-day window begins 2026-10-26T16:00:00Z; 2100 messages, 46,200 bytes,
  1050/self and 1050/person, K=11, planned requests=41, union 2100/2100.
- Both end at prepare. Export completeness explicitly unknown; demo days without
  exported records do not prove no real messages. Model stages remain pending.

## Commands and results

Use `UV_CACHE_DIR=<workspace>/.uv-cache` and an ASCII authorized pytest basetemp.
Initial default cache/temp paths were inaccessible. Oversized parametrized test IDs
also exceeded Windows path constraints; explicit short IDs fixed that test issue.

- `uv run --no-sync pytest apps/server/tests/test_ica_foundation.py
  apps/server/tests/test_chat_import.py apps/server/tests/test_agent_knowledge.py
  -q --tb=short --basetemp=<authorized ASCII path>`: **55 passed**, 1.12s.
  Covers 900/2100/6400 exact Core sets, 6401/10k rejection, long message/byte
  rejection, DST fall-back, reversed input, scope isolation, Unicode, halo bytes,
  session splitting and callback persistence error propagation.
- Ruff check of changed server/parser/migration/test/demo files: passed after
  import sorting and line wrapping; Ruff format applied.
- `uv run --no-sync python scripts/export_openapi.py --check`: PASS, 43 operations,
  all 26 Phase7D contracts preserved. No endpoint/schema added; generated client
  snapshot unchanged. No signed prepare endpoint is claimed.
- `pnpm --filter @goutou/mobile typecheck`: exit 0.
- Real Provider calls: **0**. No DeepSeek run, no root verify, no historical Android
  or Phase0–9 complete suite executed.

## Original five knowledge Mock failures

Reproduced personality, conflict, breakup, online and arbitrary-file-request failures
as structured_output_failure. Existing synthetic Action/Response fixture outputs
require content review, but their provider supplied only structured responses and
no chat review responses. Added the existing explicitly synthetic safe fixture review
helper to those test queues. All five now pass with the production validators intact.
No runtime safety/schema change. Separately probing test_agent_runtime.py revealed
three further failures; those are outside the five identified cases and were not
modified or claimed passing. Four initial knowledge setup errors were temporary-path
access errors and disappeared with the authorized ASCII basetemp.

## PostgreSQL and privacy evidence — NOT PASS

TEST_DATABASE_URL was unset. Historical local port15434 refused connection (10061).
Found the existing repository PostgreSQL16 binaries. Tried independent initdb in
`.cache/ica-v3-pgdata`, then elevated, then elevated ASCII visualization data path.
All failed during post-bootstrap with `invalid byte sequence for encoding UTF8: 0xb9`;
ordinary sandbox also emitted restricted-token errors. initdb removed its failed
clusters. No existing database was opened or altered. No PostgreSQL signed HTTP,
new migration, Memory P0, erasure or restore test passed in this session.

## Required work still missing

ICA-A4 is unimplemented: signed prepare/preview transport, question/model/budget/
scope/snapshot-bound challenge, explicit confirmation, durable independent grants,
revocation/TTL, re-read source evidence, persisted coverage receipts, deletion and
quarantined restore integration. No executable authorization or fake execute endpoint
was introduced. Preparation imports neither Memory nor Provider. Existing consent,
paused and outbound messaging code was unchanged, but that is not substitute evidence
for privacy regression execution.

Also missing: complete SQL count/byte/day/gap statistics before overlimit rejection,
comparison-window transport/halo tests, exact media/system breakdown in preview,
zero-count selected local days, grant-bound aliases, persisted provenance HTTP DTOs,
Mobile explicit format selection, signed JSONL import/merge canaries, PostgreSQL
10k bounded-read/EXPLAIN, lifecycle tests and required Memory P0 rerun. No claim that
export/parse gaps are fully computed. Core evidence function validates a supplied
snapshot only; it is not current-source authorization. Source hashes are recorded
in `evidence/ica-a-v3/source-manifest.json` excluding this self-referential report.

The next work remains **ICA-A**, not ICA-B. Public scope/grant endpoints must stay
absent until authorization/lifecycle boundaries are implemented and verified.
