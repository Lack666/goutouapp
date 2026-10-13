# Evidence privacy review — Phase 9B

Read-only automatic scope: all130 files in docs/evidence/phase8f-closeout plus
its matrix (131); all20 Phase9A execution files plus its matrix (21). Initial
152-file inventory digest: d437cd9084ed468aca78d186b89822e96e6e291ddd5004a9f2775e9ac87381ad.
Types: JSON58, log47, exit47, no binary/screenshot evidence in that scope.
Source: scripts/audit_evidence_privacy.py (extends retained9A historical scanner).
Rules cover JWT header/shape, Bearer values, provider-key and database-password
patterns; only counts/categories/paths/hashes are output, never matched values.
Initial automatic result: no pattern hits. New9B evidence is also scanned on
each root run. The current output is execution evidence, not a universal proof.

Separate human-assisted sampling performed in9B: representative owner-isolation,
Memory-restart, Import-lifecycle and SSE native steps/report sections, including failed
attempts; 9A first failed pre-marker tail and successful post-marker tail;
current9B resource/SSE/Memory reports and session-failure transcript. Compared
case commands/fixtures against scripts/native/*, mobile_connected_fixture.py,
resource_demo_support.py, memory_phase6_support.py and private native helper.
Samples contain anonymous synthetic names, fixed synthetic chat/Memory facts,
fixture UUIDs, counts and status/observer metadata. Identity source is the local
development CLI through private pipes, not a production credential or auth override.
Helper state output excludes password nodes and replaces current fixture tokens.
SSE observer retains only event types/timing/reader counts, not payloads/tokens.
No private WeChat source was used. Test faults/invalid inputs are synthetic.

Review limits: full arbitrary prose was not manually certified file-by-file;
regex cannot establish absence of all personal information. Old tracebacks and
execution paths contain operator/workspace metadata; this is retained engineering
evidence, not end-user chat, and requires repository/access/retention governance.
No confirmed credential or real-chat leak was found in reviewed samples. New9B
secret markers are generated at runtime and not committed. Native picker shows
only known synthetic test filenames on this controlled emulator; a future device
with personal files must avoid capturing its picker inventory.

Historical artifacts and hashes are unchanged. If a real disclosure is found:
classify credential/private-data severity, restrict distribution and revoke
credentials where applicable; document affected immutable hashes and create a
separate restricted archive/redacted replacement plus governance record. Do not
silently edit already hashed acceptance bytes. Production collectors/backup
retention remain R-06/R-09 and are not closed by this review.

Logging review is separate: new application output has a fixed whitelist and
strips parameters/exception/stack/extra fields; Uvicorn access stays disabled.
Tests inject runtime markers into HTTP/SQL/Agent/storage/subprocess failures and
assert output privacy. Production log collectors are not deployed/certified.
