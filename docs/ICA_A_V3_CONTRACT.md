# ICA-A contract — ica-long-range-v3 (2026-11-02)

This additive revision preserves IMPORTED_CHAT_ANALYSIS_MVP.md v2. Its whole-run
200 message/48KiB bound becomes a per-core bound. Independent admission limits
are 10,000 messages, 2MiB normalized UTF-8, 32 chunks, 200 messages/48KiB per
core, 20 messages/4KiB per halo side. Therefore 10,000 messages cannot be promised
coverage: the core count bound alone allows at most 6,400. Any failed bound rejects
the entire selection; no last-200 fallback. Oversized individual messages reject.

Order is (UTC timestamp, canonical UUID). Session gaps are strictly >30 minutes.
Prefer session and speaker turn boundaries; large sessions continue across chunks.
Halo belongs only to its selected window and never counts toward core coverage.
Core UUIDs must partition exactly the authorized snapshot. Same text is not identity.
Unicode spans use Python Unicode code point offsets, end exclusive.

3/7 day windows include today in an explicit IANA zone, from local midnight
N-1 days ago through prepare time, represented as UTC half-open bounds. Custom
dates are inclusive local calendar dates capped at prepare. Export completeness
is unknown unless independently established; absence in an export proves nothing.

Future ICA-B request planning uses 3K+8. Serialized inputs including repeated halo,
prompt reserve and maximum output require a conservative token and price ceiling;
these are planning estimates, never observed Provider usage. No model stage receipt
may be marked complete by deterministic preparation. No execute endpoint in ICA-A.

ChatLab JSONL v0.0.2 is independently implemented from its public field contract.
Weport JSONL uses the same adapter; native JSON is unsupported. Stable sender IDs
are explicit binding labels; account names and meta.ownerId do not establish self.
External IDs/replies and physical line numbers are provenance, not dedup keys.
No cross-format dedup guarantee. No third-party implementation code is copied.

Readiness requires signed PostgreSQL, lifecycle and transport integration evidence.
Pure functions alone do not establish trusted authorization or production readiness.

## Completion addendum (2026-11-02)

The original PARTIAL report is preserved; completion uses a separate acceptance.
Each calendar window is capped at 367 elapsed days to bound zero-count day output.
Two windows share all whole-run limits and never share halo. Prepare has a 5-minute
challenge, confirmed source-read authorization a 24-hour TTL. Confirm requires the
literal JSON boolean true, opaque challenge and exact binding hash. The whole private
question, selected model, token/request limits and source/manifest are bound server
side. Model pricing is explicitly unquoted (cost_cap=null); the confirmed record is
source-read/preparation consent, not permission to perform unpriced paid execution.
ICA-B must price and enforce its execution ceiling before introducing execution.

Evidence is POST with a bounded quote in the request body, avoiding private text in
URL/access logs. Its alias resolves exclusively through the stored grant. The full
snapshot is recomputed under owner/Dataset locks on confirm and every source read.
No caller-supplied message UUID, Dataset override or raw SQL tool is accepted.
Coverage manifests and model stages pending are persisted as version-bound JSONB;
no second raw transcript is persisted. Revocation/expiry/deletion remove question,
aliases and manifests while retaining minimal operation/hash fences. Restore grants
always become restore_invalid; missing current post-archive Dataset fences block
quarantine release. These are synchronous transactions, with no background ICA writer.
