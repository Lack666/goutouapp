# ICA-A READINESS PASS

2026-11-02. ICA-A targeted engineering readiness accepted on the evidence below.
The original ICA_A_V3_ACCEPTANCE.md PARTIAL report is preserved.

Base HEAD: `1f4e000eb4647240b65bd1ce5701058ce109186a`. Previous ICA implementation
was uncommitted and is reused. Original human-review data, review UI and 11R human
report are excluded from this delivery. Marker9/9H, Phase11 QUALITY FAIL,
Phase10 DEFERRED and Phase12 PENDING remain intact.

Delivery source/evidence fingerprint:
`0d0640541f84cc29f076bf526e9b42ab5b170b6185fa446f86cee485ef1ec555`.
Per-file hashes and the exact changed-file inventory are in source-manifest.json.

## PostgreSQL diagnosis and reproducibility

Windows culture zh-CN; LANG/LC_ALL/LC_CTYPE unset. Existing PostgreSQL16 config
uses locale C. Previous initdb reached **post-bootstrap initialization** then failed
with UTF8 byte0xb9. Changing only the data directory had not fixed it. This session
copied the **same existing binaries and support files** from `.cache/pg16/pgsql`
to an authorized ASCII installation path and initialized a fresh data directory
there. Initialization succeeded with C/UTF8. This establishes installation-path
encoding as the distinguishing cause; no claim about a PostgreSQL source-level fix.
The sandbox pg_ctl then failed on Windows restricted-token creation; one elevation
for that diagnosed process-launch restriction started the isolated server successfully.
Docker was present but its pipe unavailable in sandbox; it was not needed.

Exact setup (PowerShell; `$icaPgRoot` must be a fresh ASCII directory inside an
authorized writable root):

```powershell
Copy-Item -LiteralPath '.cache/pg16/pgsql' -Destination $icaPgRoot -Recurse
& "$icaPgRoot/bin/initdb.exe" -D "$icaPgRoot/data" -U postgres -A trust --encoding=UTF8 --locale=C --no-instructions
& "$icaPgRoot/bin/pg_ctl.exe" -D "$icaPgRoot/data" -l "$icaPgRoot/server.log" -o '-p 15435 -h 127.0.0.1' -w start
& "$icaPgRoot/bin/psql.exe" -h 127.0.0.1 -p 15435 -U postgres -d postgres -c 'SELECT current_database(), current_setting(''server_encoding'');'
$env:TEST_DATABASE_URL = 'postgresql+psycopg://postgres@127.0.0.1:15435/ica_test'
$env:PG_BIN_DIR = "$icaPgRoot/bin"
$env:UV_CACHE_DIR = Join-Path $PWD '.cache/uv'
```

Actual installation root was the authorized visualization root plus `/pg16`.
Server listens only on127.0.0.1:15435. No production connection, existing role or
unknown database was modified. Every pytest database has a generated `_test_<uuid>`
name and is dropped by the existing fixture. A dedicated test downgrades the two new
migrations to20261014_01, upgrades again, verifies clean table isolation, then checks
that its own disposable database was dropped. No production infrastructure dependency.

## Implementation and boundaries

Reused original parser, scope/chunk/Unicode functions, canonical import staging,
JWT verifier, owner/Dataset transaction ordering, lifecycle deletion, maintenance
and native quarantined restore. New table imported_analysis_grants stores temporary
request/source digests, aliases, manifests and pending stage ledger in JSONB, with
unique(owner,operation_key). It does not duplicate raw message bodies. Migrations
20261102_01 (provenance/index) and20261102_02 (authority) run on PostgreSQL.

Five signed operations under /api/v1/imported-analysis: POST prepare, POST confirm,
GET grants/{id}, POST grants/{id}/revoke, POST grants/{id}/evidence/{alias}.
The POST evidence body keeps quotes out of URL/access logs. No execute or report API.
Prepare issues only a five-minute opaque challenge, not confirmed authority.
Confirm requires explicit true plus challenge, binding hash and operation key;
atomic owner serialization handles concurrent retries and conflicting keys. Confirm
does not initialize Agent. Grant TTL is24h; repeated confirmation does not extend it.

Every source read checks current actor/Owner/Person/Relationship/canonical Dataset,
grant status/TTL, recomputed source fingerprint and exact manifest. Source mutation,
revocation and expiration reject reads. Evidence uses stored UUID/window aliases and
code point spans with current content, source index, external/reply IDs and line spans.
Persistent model safety/extraction/counterevidence statuses remain pending.

Dataset, Person, Relationship and Owner erasure clear grant payloads in the deletion
transaction. Owner deletion uses the existing development operator service; no new
account privilege is exposed. Maintenance clears expired payloads under owner locks.
Restore holds existing table/writer fences, clears all restored grant authority and
preserves current operation fences; absent post-backup Dataset authority fails closed.

Mobile adds explicit Markdown/ChatLab JSONL selection, multipart source_format,
JSONL filename acceptance and format-neutral private cache copies. No analysis or
report screen. Generated client/OpenAPI now have48 signed operations (prior43 plus5).
ApiTransport has an independent opt-in ICA route guard; import permission does not
implicitly enable analysis, Memory or execute. No new runtime dependencies.

## Range and budget evidence

`test_ica_signed.py` imports actual anonymous WeFlow-compatible JSONL through signed
HTTP, binds stable IDs, finalizes/reparses and checks canonical duplicate import.
Real PostgreSQL snapshots:900 messages/3 days →5 chunks/23 planned requests;
2100/7 days →11 chunks/41 planned requests. Same-body occurrences have distinct UUIDs;
Core union equals all selected messages and every model stage is pending.
Daily counts include zero days, media/system/text breakdown, exact UTF8 bytes,
parser issues/ignored messages, actual min/max and explicit unknown export gaps.
Unexported history is never treated as nonexistent.

Synthetic body好😀 is7 UTF8 bytes:900→6300 bytes,2100→14700 bytes. Selected-day
windows include today through actual prepare time. Signed tests also cover custom,
non-overlapping comparison windows, cross-window halo containment, DST fall-back,
equal timestamps, reverse source order, media/system and zero-message dates.

The10k SQL probe yields21 pages (20×500 plus terminal empty page), no OFFSET;
whole-run prepare rejects K>32 instead of truncating. EXPLAIN ANALYZE/BUFFERS uses
ix_ica_dataset_keyset. Captured plan, peak Python memory and actual counts are retained
in evidence/ica-a-completion/sql-10k.json. Only one relevant Dataset keyset index is
introduced; no speculative infrastructure or extra vector/search indexes.

Planner binds actual escaped serialized payload/halo reserve, question overhead,
prompt and output ceilings, and3K+8 requests. Token budgets are planning upper bounds,
not observed token usage. Actual model pricing is unconfirmed: cost_cap is null and
execution is prohibited until priced. No synthetic demo tariff is presented as money.
All ICA Provider calls:0. Runtime tests use Mock only; no DeepSeek API or paid eval.

## Tests and failure diagnosis

Initial completion regression:193 passed in80.26s. New signed suite subsequently
expanded from9 to12 cases, all12 passed in8.97s. Final-source results recorded below.
The earlier three Runtime failures were reproduced as missing content-review chat
queues for historical safe Action/Response fixtures (including the second reused
run). Added only the existing explicit synthetic review helper to those queues;
runtime safety/schema code is unchanged. test_agent_runtime.py now8 passed.

Final-source targeted regression: **215 passed in90.97s**; includes the original
ICA unit cases,12 signed ICA database cases, Chat Import/Jobs/Merge/API, Memory11R,
erasure/full erasure/full restore, Runtime/knowledge and maintenance/data lifecycle.
After the final ORM index metadata alignment and SQL literal formatting, the signed
database suite was rerun: **12 passed in9.17s** (already included in215, not additive).
Mobile: **81 passed,5 suites** (imports/history/native picker/UI plus ICA transport).
Typecheck exit0; deterministic OpenAPI48 and generated client check pass, including
all3 codegen tests. All changed Python files pass Ruff, formatting and git diff checks;
changed Mobile files pass Prettier. No failures or skipped core database/privacy items.

Exact final regression command (environment above; authorized ASCII pytest basetemp):

```powershell
uv run --no-sync pytest apps/server/tests/test_ica_foundation.py apps/server/tests/test_ica_signed.py apps/server/tests/test_chat_import.py apps/server/tests/test_import_jobs.py apps/server/tests/test_import_merge.py apps/server/tests/test_import_api.py apps/server/tests/test_phase11r_memory.py apps/server/tests/test_erasure.py apps/server/tests/test_full_erasure_9h.py apps/server/tests/test_full_restore_9h.py apps/server/tests/test_agent_runtime.py apps/server/tests/test_agent_knowledge.py apps/server/tests/test_data_lifecycle.py -q --tb=short --basetemp=<fresh-authorized-ASCII-directory>
pnpm --filter @goutou/mobile exec jest --runInBand tests/icaTransport.test.ts tests/connectedImport.test.ts tests/connectedImportUI.test.tsx tests/filePicker.test.ts tests/connectedHistory.test.ts
pnpm --filter @goutou/mobile typecheck
uv run --no-sync python scripts/export_openapi.py --check
pnpm api:check
```

Evidence directory: `evidence/ica-a-completion/`. The source manifest inventories
actual delivery files and SHA256, with an aggregate fingerprint excluding its own
self-reference and this acceptance text. It binds the executable source rather than
claiming that the old base HEAD already contains these changes. Tests create their
own databases and use signed JWTs without persisting credentials. Anonymous Preview
and full manifests, SQL plan, test outputs and environment diagnosis are retained.
The final10k read measured3,431,046 Python peak bytes; first500-row EXPLAIN finished
in0.197ms on this local instance, using ix_ica_dataset_keyset. These are local samples,
not production latency guarantees. The2100 signed prepare measured10,208,966 peak
Python bytes and reserved4,804,174 planning tokens/41 requests; Provider calls0.

Intermediate test fixes: Owner deletion correctly returns401 rather than the test's
initial404/409 expectation; Mobile test used the old file-button label; React Native
FormData typing required the existing test cast; no runtime guard was weakened.
Content review is still enabled. Evidence was moved from a draft GET to POST before
finalization to avoid placing private quotes in query strings. Temporary unformatted
patches were Ruff/Prettier formatted. These failures are not counted as passes.

## Remaining ICA-B work / limitations

No semantic safety/extraction/counterevidence generation, synthesis, Agent execution,
paid Provider calls, analysis report or Android report UI is implemented. ICA-B must
obtain/validate a real tariff and execution ceiling, enforce grant/TTL on every read,
and separately authorize/verify any execution/writer lifecycle. Custom windows are
bounded to367 elapsed days for finite zero-day output. Export completeness and
legacy skipped-item counts that cannot be reconstructed are explicitly unknown.
No new on-device native build is claimed: JSONL Android picker/controller is tested
in Jest, TypeScript and transport checks as authorized. Original historical full
Android and Phase0–9/root verify were not run. Production deployment remains outside
this engineering readiness decision.
