# Resource admission — Phase 9C

Scope: one local-filesystem deployment, sharing PostgreSQL, the canonical private
artifact root, its sibling OS fence directory and identical limits across workers.
No Redis, public quota/metrics endpoint, client Owner field or trusted X-Forwarded-For.
Application resource boundaries are tested locally; public production is NOT certified.

The ASGI admission layer precedes Multipart parsing. The existing outer body-size
guard first rejects an excessive Content-Length hint. Actual received bytes remain
independently capped, including chunked bodies. A valid signed subject and existing
User obtain upload/processing capacity before any request body is received. Invalid
credentials return401 without spooling; unknown signed upload subjects now return401.
The normal route verifier independently retains its Auth Contract.

All protected `/api/v1/*` attempts except status/OPTIONS share database-backed
fixed one-minute request windows; verified existing users also have Owner windows.
Uploads have additional independent global/Owner windows. Public liveness, readiness,
status and schema routes remain DB/auth-independent as their contracts require.
These exemptions and network/header/TLS budgets require the deployment ingress;
there is no claim of a whole-host/network DDoS limit. Minute boundaries permit a
two-window burst. Unknown/invalid subjects count globally, not as unlimited Owner keys.

Default configuration (positive Pydantic bounds; see Settings for permitted ranges):

- MAX_CHAT_IMPORT_BYTES:104857600. Multipart cap:105906176; one file/two fields.
- MAX_CHAT_IMPORT_SPEAKERS:1024 at workflow registration; exceeding returns422
  parse_failed with no Job. The standalone parser and exact-dataset semantics for
  admitted sources are unchanged. Streaming accepted-message callbacks stop the
  inventory after at most1025 distinct labels; no full-message collection is retained.
- ADMISSION_UPLOADS_GLOBAL:8; ADMISSION_UPLOADS_OWNER:4.
- ADMISSION_PROCESSING_GLOBAL:2; ADMISSION_PROCESSING_OWNER:2 for finalize/replay.
- ADMISSION_REQUESTS_PER_MINUTE:6000; ADMISSION_OWNER_REQUESTS_PER_MINUTE:600.
- ADMISSION_UPLOADS_PER_MINUTE:120; ADMISSION_OWNER_UPLOADS_PER_MINUTE:30.
- ADMISSION_STORAGE_GLOBAL_BYTES:8589934592; OWNER_BYTES:2147483648.
- ADMISSION_PENDING_GLOBAL:1000; OWNER:100, including active upload reservations
  and retained awaiting_binding/ready/importing Jobs. Historical completed receipts
  and formal PostgreSQL message storage are separate retained-data domains.
- ADMISSION_BODY_IDLE_SECONDS:15; TOTAL_SECONDS:120, counting from ASGI admission.
- ADMISSION_MIN_FREE_BYTES:268435456; INVENTORY_LIMIT:10000 files/rows/Owner keys.
- DATABASE_POOL_SIZE:5; MAX_OVERFLOW:10; POOL_TIMEOUT_SECONDS:1 per process.
  One active upload/finalize holds one admission DB connection; a business operation
  may require another. Default global held admission connections are at most10,
  plus bounded per-process pool capacity. Worker count multiplies possible business/
  short-window connections; align the deployment's DB connection budget with
  workers*(5+10), operator/readiness capacity and other clients. Exhaustion fails503;
  upload capacity does not promise reserved DB availability for other endpoints.

One upload reserves `2*file_limit + 1MiB + 16KiB`:210780160 bytes (201MiB+16KiB).
This covers framework spool plus application artifact plus conservative file/fence
overhead. Eight active uploads reserve1686241280 bytes before retained sources.
This is an accounted byte budget, not a measured RSS/whole-volume physical quota.
Inactive sources use filesystem byte size rounded to4KiB plus4KiB/file; hard-link
aliases may be conservatively charged twice after a crash. Sparse/native allocation,
filesystem cluster/metadata/page-cache costs are separate deployment assumptions.
Free-space checks cover both artifact and actual default-temp volumes, retaining
the configured headroom and conservative active reservations. Other host writers
can race these checks; ENOSPC remains a controlled dependency failure.

Admission transactions acquire a shared PostgreSQL transaction advisory guard,
with250ms lock and2s statement bounds. They recover dead fences, scan actual files,
include all retained cancelled/expired/cleanup-failed data, and atomically compare
capacity before issuing a reservation. Active file bytes are covered by the full
reservation instead of double charging. Missing raw files remove only inactive
attribution; Job status alone never releases stored bytes. Unknown-provenance files
are counted in operator snapshots and block uploads until grace-based cleanup or
explicit operator review restores attribution. Scan overflow/symlinks fail closed.

The sibling fence is a locked one-byte private file, not a time lease. PostgreSQL
session locks also remain held, but reclamation requires the OS fence to be free.
A terminated DB backend cannot release a still-writing live worker. Worker death
closes the OS handle; the next admission or privileged snapshot releases its slot
and converts its residual file to actual retained charges. Two workers serialize
recovery under the DB guard. No periodic scheduler is claimed to be deployed.

Workers with mismatched policy fingerprints fail503. To change limits: drain/stop
all workers, reconcile actual files and budgets, and explicitly migrate the private
state policy under the same guard before restart. Never delete reservation rows to
make a full disk appear empty. Multiple machines/network/object stores are unsupported:
the tested OS locking and common local root are mandatory topology assumptions.

Responses reuse ErrorResponse:413 upload_too_large;429 http_error+Retry-After;
408 http_error;503 artifact_unavailable+Retry-After for quota/capacity/storage/DB.
No remaining capacity, other Owner state, keys, paths or errors appear. Operation
count remains36 and generated DTOs do not change. Upload-specific exhaustion does
not consume the separate finalize capacity or apply its rate check to Memory/Agent.
The general request window still applies to all protected operations.

Operator `ResourceAdmission.snapshot()` returns only aggregate active/charged/
reserved/unattributed counts and a finite event whitelist. Worker event counters
are process-local diagnostics, reset on restart; reclaim_candidates counts observed
recovery candidates, not committed global releases. Access logs remain disabled.
No filename/Owner/resource ID/chat/token/error-text labels are accepted.

Evidence: test_resource_admission.py, retained upload/import/privacy suites,
Mobile resourceAdmission.test.ts and PHASE_9C_MATRIX. See UPLOAD_RELIABILITY and
ADR0038 for recovery, test coverage and explicit deployment blockers.
