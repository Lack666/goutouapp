# Chat import parser — Phase 5A

Phase 5A is an offline, read-only parser boundary. The only supported source is
`wechat_markdown_v1`; no upload route, database write, speaker identity mapping,
Agent call or model call occurs here. The implementation lives in
`apps/server/app/chat_import` and has no FastAPI or SQLAlchemy dependency.

## Input and grammar

`ChatImportParser.parse(ChatImportSource(chunks, source_name), ImportOptions(...))`
accepts a one-pass iterable of text or UTF-8 byte chunks. A text or binary
stream may be passed directly. It does not open paths. The standalone CLI may
open a local file, then passes its stream to the same parser. `source_name` is
display metadata only; an absolute path is never a domain identity.

The exact header is `## YYYY-MM-DD HH:MM:SS SPEAKER` at the beginning of a
line, with one ASCII space between tokens and a nonblank speaker label.
Date-like `## YYYY-MM-DD ...` lines mark a new block even when malformed, so
an invalid block is reported and cannot silently merge into the preceding
message. Other headings such as `## hello` inside a body remain ordinary body
text. Preamble text and malformed preamble headings produce issues. An
unspecified format is detected only if a date-like candidate exists; otherwise
it fails as `unsupported_format`. Explicit formats other than
`wechat_markdown_v1` fail before reading source.

`ImportOptions.source_timezone` is required and must be an IANA timezone such
as `Asia/Shanghai`. The timestamp in the header is a naive source-local wall
clock time. The parser retains the exact timestamp string, a naive local
`datetime`, and the timezone name, then converts to an aware UTC `datetime`.
Ambiguous or nonexistent daylight-saving local times are reported as
recoverable errors and their blocks are skipped; the parser never guesses a
fold or uses server time. Files remain in source order. A duplicate UTC time
or a decrease from the preceding accepted message is a warning, with no sort.

The body extends through the line before the next date-like header. The parser
removes surrounding *blank lines* (including whitespace-only lines), preserves
internal blank lines and all other text, and joins lines with `\n`. It removes
only a first-line UTF-8 BOM and converts CRLF line endings to LF. It does not
change Chinese punctuation, emoji, spelling or nonblank whitespace. Each
message records applicable normalization notes. A body empty after separator
removal yields `empty_body` and is skipped. Exact single-body markers
`[表情包]`, `[图片]`, `[语音]`, `[视频]`, `[文件]`, `[位置]`, `[小程序]` become
`placeholder`; an unrecognized single bracket marker becomes `unknown`.
Both retain their source text. No media file, description or meaning is
created.

## Canonical result

`ImportedMessage` schema version `1` contains a one-based source candidate
index, original/local/UTC timestamps, raw speaker label, normalized content,
minimal content type, line range, normalization notes and SHA-256 fingerprint.
The speaker label is exactly the header substring: `我` or `怡宝🥰` does not
identify a User or Person. Invalid blocks leave gaps in source indexes.
Provenance line ranges include the header and source separator lines preceding
the next header. `ChatParseResult` schema version `1` includes format, parser
version `1`, accepted count, distinct raw speaker counts in first-appearance
order, first and last accepted UTC timestamps in source order, issue counts,
bounded issue records, and source/transcript fingerprints.

The message fingerprint is SHA-256 over UTF-8 JSON with sorted keys and compact
separators for: `source_format`, `parser_version`, `schema_version`, UTC ISO
timestamp, raw speaker label, normalized content and content type. It excludes
filename, source index and line range. Equal canonical messages therefore have
equal fingerprints even if a file is prepended. The transcript fingerprint is
SHA-256 initialized with compact JSON of `[format, parser_version,
schema_version]`, then updated in source order with each 32-byte message
fingerprint digest. The source fingerprint is SHA-256 over the consumed raw
byte chunks, or UTF-8 encoding of consumed text chunks; `source_name` is
excluded. The source fingerprint is absent if parsing stops before consuming
the source, and transcript fingerprint is absent on fatal or empty results.
These unkeyed hashes aid future deduplication but are not proof of ownership.
The message fingerprint is not an occurrence identity. Repeated identical
messages can share it; Phase 5C must include source position within a verified
ImportJob when defining imported Message uniqueness.

## Issues, limits and memory

Issues have typed severity (`warning`, `error`, `fatal`), stable code, optional
source line range and a safe generic message that does not repeat chat text.
Invalid headers, timestamps, speakers, empty or oversized bodies, oversized
lines and DST anomalies are recoverable and skip the affected block. Time
ordering anomalies warn without skipping. Unsupported format/encoding,
invalid UTF-8, missing/invalid timezone, invalid limits, no valid messages and
maximum candidate count are fatal. A fatal result can contain already parsed
messages for diagnostics, but must not be persisted as a completed import.

Default limits: 20,000 characters per normalized message, 120 speaker
characters, 25,000 characters per input line, 1,000,000 header candidates,
and 1,000 retained issue records. These are configurable positive integers.
The parser streams line by line, buffers at most the current bounded message,
and updates counts/hashes incrementally. `include_messages=False` omits the
message list for a summary-only dry run; the parser still processes each
message and calculates fingerprints. The source itself is never duplicated in
every message. One caller-provided chunk may still be as large as that chunk;
normal file iteration supplies bounded lines.

## Offline dry run and privacy

From the repository root:

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked python apps/server/chat_import_demo.py
uv --cache-dir .cache/uv --no-managed-python run --locked python apps/server/chat_import_demo.py path/to/export.md --source-timezone Asia/Shanghai
```

The demo defaults to a checked-in synthetic fixture. It prints only format,
versions, counts, speaker labels, timestamps, issue codes and fingerprints;
it does not log message bodies. Speaker labels themselves may be personal
information, so direct dry-run output accordingly. It requires no network,
PostgreSQL, Agent or model key. The 10,000-message test uses a generator whose
`read()` raises, confirming line iteration and summary mode.

Phase 5B adds persistent, owner-scoped job metadata and explicit speaker and
Relationship binding outside this parser; see [Import Jobs](IMPORT_JOBS.md).
Phase 5C owns imported Message persistence. The parser does not create
conversation rows or split a transcript into multiple conversations.
Phase 5C uses the same parser with a per-message callback and
`include_messages=False`: accepted canonical messages are staged in bounded
batches, and summary fingerprints are checked before formal promotion. See
[Imported Messages](IMPORTED_MESSAGES.md).
