# Phase 5A acceptance — Chat Import Contract and Parser Foundation

Date: 2026-09-28. **Status: PASS.** Phase 4 preflight marker was
`completed_phase=4`, `completed_subphase=4D`, with clean Git status and HEAD
`9cf255b feat: complete Phase 4D persistent idempotency and Phase 4 acceptance`.
This work is a separate Phase 5A checkpoint. `project-phase.json` now records
`completed_phase=4`, `completed_subphase=5A`; Phase 5 as a whole is not marked
complete.

## CODE

- Frozen typed `ChatImportSource`, `ImportOptions`, `ImportedMessage`,
  `ImportIssue` and `ChatParseResult`, plus a structural `ChatImportParser`
  protocol. Parser and canonical schema are version `1`.
- WeChat Markdown v1 is the sole supported format. The parser consumes a
  one-pass stream, recognizes strict dated headings, preserves multiline
  bodies and raw speaker labels, requires an IANA source timezone, converts
  to aware UTC and keeps source order. It reports recoverable malformed blocks
  and fatal source failures with typed codes and line ranges.
- Message fingerprints use canonical SHA-256; transcript fingerprints use
  ordered message digests; source fingerprints cover consumed input. A
  summary-only mode maintains incremental counts and hashes without retaining
  message objects. Configurable line, label, message, candidate and issue
  limits bound parser work. No migration or application endpoint was added.

## TEST

`uv --cache-dir .cache/uv --no-managed-python run --locked pytest -q
apps/server/tests/test_chat_import.py` → **19 passed**. Tests cover the
synthetic four-message fixture, exact emoji labels, multiline content, plain
headings in bodies, placeholders and unknown markers, BOM/CRLF split into
single-byte chunks, source order and anomalies, invalid/empty/oversized
blocks, invalid encoding, missing/invalid timezone, DST gap/fold rejection,
UTC conversion, stable message/transcript hashes, issue caps and privacy.
The 10,000-message generator has a `read()` method that raises; summary mode
processed all messages, all three speaker counts and 9,999 duplicate-time
warnings without loading a whole source or retaining message objects.

## DOC and DEMO

`docs/CHAT_IMPORT.md` defines grammar, normalization, timezone semantics,
hash inputs, issue severity, limits, privacy and deferred boundaries. ADR
0022 records the parser decision; Master Plan and Architecture identify the
new boundary. `uv --cache-dir .cache/uv --no-managed-python run --locked python
apps/server/chat_import_demo.py` parsed the synthetic fixture offline:
`message_count=4`, speaker counts `3/1`, no issues, first UTC timestamp
`2023-11-08T23:51:23+00:00`, last UTC timestamp
`2023-11-09T00:23:26+00:00`, with source and transcript SHA-256 values.
The demo prints summary metadata only. No PostgreSQL, network, Agent or LLM
is used by the parser or demo.

## REGRESSION and verify gate

The required `.\make.cmd verify` command was run from the repository root,
with `TEST_DATABASE_URL` targeting a disposable local
PostgreSQL 16 `goutou_test` namespace on `127.0.0.1:15433` and a separate
`DATABASE_URL` for `goutou_dev`. The Docker daemon was unavailable in the
previous phase, so the already prepared ignored workspace cluster was used.
Results: **PASS**, including isolated Alembic upgrade/downgrade/check,
Phase 3 Golden and replay checks, Phase 3 E2E, Phase 4 AgentService,
REST/Auth, SSE, persistent idempotency and real socket demos, the new Phase
5A tests and dry run, **347 passed** in the full backend test suite, secret
boundary and Ruff check/format. The verifier prints both Phase 4 and Phase
5A PASS and defers persistent import jobs, speaker binding, imported message
DB persistence and Mobile. `git diff --check` also passed.

## Architecture decisions and limits

Speaker labels are source text, never inferred person identities. The parser
has no FastAPI, SQLAlchemy, AgentRuntime or LLM dependency, writes no
Conversation/Message/Relationship/Memory row and cannot create attachments.
No real private chat was committed. An unkeyed canonical fingerprint can be
equal for repeated identical messages; occurrence identity and persistence
belong to later Phase 5 work. Fatal results must not become completed imports.
Live-model quality and future import APIs were not validated in this phase.

**Next:** Phase 5B — Persistent Import Jobs and Speaker/Relationship Binding,
only after a separate explicit instruction.
