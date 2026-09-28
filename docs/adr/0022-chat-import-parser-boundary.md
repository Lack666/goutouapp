# ADR 0022 — transport-free chat import parser boundary

Date: 2026-09-28. Status: accepted for Phase 5A.

## Context

Phase 4 has a trusted authenticated service and persistent run boundary, but
there is no canonical way to inspect a chat export. A future importer must not
turn a nickname into an identity, infer timezone from the server, lose source
order, or put parsing rules in a FastAPI endpoint.

## Decision

Introduce frozen typed contracts and a `ChatImportParser` protocol. The first
implementation recognizes only WeChat Markdown v1 and consumes a one-pass
text/UTF-8-byte iterable. Parsing, strict header detection, local-to-UTC
normalization, issue collection, speaker counts and SHA-256 fingerprints occur
without transport, database, runtime or model imports. The source timezone is
mandatory. Ambiguous/nonexistent DST times fail that block. Date-like malformed
headings close a block and produce an issue. A body with no content after
separator trimming is skipped with an issue. Anomalous timestamps keep file
order and warn. Raw speaker labels remain labels, with no User/Person link.

Message hashes cover canonical content, UTC time, raw label, type and
format/parser/schema versions, excluding source position and name. The
transcript hash covers the ordered message-digest sequence and versions;
the source hash covers consumed bytes/text. These definitions are versioned
because parser corrections can change canonical values. Summary-only mode
retains no message list and the issue list has a configurable cap. Limits
bound one line, one message, one label and total candidate headings.

## Consequences

The parser can be run and tested entirely offline against synthetic fixtures.
Future formats require another parser behind the protocol. The current
fingerprint can identify equal canonical messages, but identical repeated
messages share a fingerprint; Phase 5C must define import identity and
occurrence handling. The source hash is unavailable after early fatal stop.
The parser has no attachment recovery or speaker inference. Upload, ownership,
database jobs, binding and persistence remain Phase 5B/5C responsibilities.
