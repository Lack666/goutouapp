"""Incremental, deterministic parser for the supported WeChat Markdown export."""

from __future__ import annotations

import codecs
import hashlib
import json
import re
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.chat_import.contracts import (
    FORMAT_WECHAT_MARKDOWN_V1,
    PARSER_VERSION,
    SCHEMA_VERSION,
    ChatImportSource,
    ChatParseResult,
    ContentType,
    ImportedMessage,
    ImportIssue,
    ImportOptions,
    IssueCode,
    IssueSeverity,
    SourceLocation,
    SpeakerCount,
)

_HEADER = re.compile(
    r"^## (?P<date>\d{4}-\d{2}-\d{2}) (?P<time>\d{2}:\d{2}:\d{2}) (?P<speaker>.*)$"
)
_HEADER_CANDIDATE = re.compile(r"^## \d{4}-\d{2}-\d{2}(?:\s|$)")
_PLACEHOLDERS = frozenset(
    {"[表情包]", "[图片]", "[语音]", "[视频]", "[文件]", "[位置]", "[小程序]"}
)
_BRACKET_MARKER = re.compile(r"^\[[^\[\]\n]+\]$")


@dataclass(frozen=True)
class _InputLine:
    number: int
    text: str | None
    crlf: bool = False
    bom: bool = False


class _HashWriter(Protocol):
    def update(self, data: bytes) -> None: ...


def _iter_lines(
    source: ChatImportSource, max_line_chars: int, source_hash: _HashWriter
) -> Iterator[_InputLine]:
    """Yield bounded logical lines from arbitrary text or UTF-8 byte chunks."""
    decoder = codecs.getincrementaldecoder("utf-8")("strict")
    kind: type[str] | type[bytes] | None = None
    pending = ""
    dropping = False
    number = 0

    def emit(raw: str, oversized: bool) -> _InputLine:
        nonlocal number
        number += 1
        if oversized or len(raw) > max_line_chars:
            return _InputLine(number, None)
        crlf = raw.endswith("\r")
        if crlf:
            raw = raw[:-1]
        bom = number == 1 and raw.startswith("\ufeff")
        if bom:
            raw = raw[1:]
        return _InputLine(number, raw, crlf, bom)

    def split(decoded: str) -> Iterator[_InputLine]:
        nonlocal pending, dropping
        cursor = 0
        while True:
            newline = decoded.find("\n", cursor)
            if newline < 0:
                rest = decoded[cursor:]
                if len(pending) + len(rest) > max_line_chars:
                    pending = ""
                    dropping = True
                elif not dropping:
                    pending += rest
                return
            fragment = decoded[cursor:newline]
            yield emit(pending + fragment if not dropping else "", dropping)
            pending = ""
            dropping = False
            cursor = newline + 1

    for chunk in source.chunks:
        if not isinstance(chunk, (str, bytes)) or (kind is not None and type(chunk) is not kind):
            raise TypeError("Source must contain one consistent text or byte chunk type")
        kind = type(chunk)
        if isinstance(chunk, bytes):
            source_hash.update(chunk)
            decoded = decoder.decode(chunk)
        else:
            source_hash.update(chunk.encode("utf-8"))
            decoded = chunk
        yield from split(decoded)
    if kind is bytes:
        yield from split(decoder.decode(b"", final=True))
    if pending or dropping:
        yield emit(pending, dropping)


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def _utc_from_local(local: datetime, zone: ZoneInfo) -> tuple[datetime | None, IssueCode | None]:
    possible: set[datetime] = set()
    for fold in (0, 1):
        candidate = local.replace(tzinfo=zone, fold=fold).astimezone(UTC)
        if candidate.astimezone(zone).replace(tzinfo=None) == local:
            possible.add(candidate)
    if not possible:
        return None, IssueCode.NONEXISTENT_LOCAL_TIME
    if len(possible) > 1:
        return None, IssueCode.AMBIGUOUS_LOCAL_TIME
    return possible.pop(), None


class WeChatMarkdownParser:
    """Parse a stream without transport, identity, persistence, or model dependencies."""

    def parse(self, source: ChatImportSource, options: ImportOptions) -> ChatParseResult:
        issues: list[ImportIssue] = []
        counts: Counter[IssueSeverity] = Counter()
        speakers: Counter[str] = Counter()
        messages: list[ImportedMessage] = []
        source_hash = hashlib.sha256()
        transcript_hash = hashlib.sha256(
            _canonical_json([FORMAT_WECHAT_MARKDOWN_V1, PARSER_VERSION, SCHEMA_VERSION])
        )
        accepted = 0
        candidates = 0
        first: datetime | None = None
        last: datetime | None = None
        previous: datetime | None = None
        source_complete = False

        def issue(
            severity: IssueSeverity,
            code: IssueCode,
            location: SourceLocation | None = None,
        ) -> None:
            counts[severity] += 1
            record_limit = (
                options.max_issue_records
                if isinstance(options.max_issue_records, int) and options.max_issue_records > 0
                else 1
            )
            if len(issues) < record_limit:
                issues.append(ImportIssue(severity, code, location, code.value.replace("_", " ")))

        def result() -> ChatParseResult:
            return ChatParseResult(
                schema_version=SCHEMA_VERSION,
                source_format=(
                    FORMAT_WECHAT_MARKDOWN_V1
                    if candidates or options.source_format == FORMAT_WECHAT_MARKDOWN_V1
                    else None
                ),
                source_timezone=options.source_timezone,
                parser_version=PARSER_VERSION,
                source_name=source.source_name,
                messages=tuple(messages),
                message_count=accepted,
                speaker_counts=tuple(
                    SpeakerCount(label, count) for label, count in speakers.items()
                ),
                first_timestamp_utc=first,
                last_timestamp_utc=last,
                warning_count=counts[IssueSeverity.WARNING],
                error_count=counts[IssueSeverity.ERROR],
                fatal_count=counts[IssueSeverity.FATAL],
                issues=tuple(issues),
                issues_truncated=sum(counts.values()) - len(issues),
                source_fingerprint=source_hash.hexdigest() if source_complete else None,
                transcript_fingerprint=(
                    transcript_hash.hexdigest()
                    if accepted and source_complete and not counts[IssueSeverity.FATAL]
                    else None
                ),
            )

        if options.source_format not in (None, FORMAT_WECHAT_MARKDOWN_V1):
            issue(IssueSeverity.FATAL, IssueCode.UNSUPPORTED_FORMAT)
            return result()
        if options.encoding.lower().replace("_", "-") not in ("utf-8", "utf-8-sig"):
            issue(IssueSeverity.FATAL, IssueCode.UNSUPPORTED_ENCODING)
            return result()
        if not options.source_timezone:
            issue(IssueSeverity.FATAL, IssueCode.TIMEZONE_REQUIRED)
            return result()
        try:
            zone = ZoneInfo(options.source_timezone)
        except (ZoneInfoNotFoundError, ValueError):
            issue(IssueSeverity.FATAL, IssueCode.INVALID_TIMEZONE)
            return result()
        if (
            any(
                not isinstance(value, int) or isinstance(value, bool) or value < 1
                for value in (
                    options.max_message_chars,
                    options.max_speaker_chars,
                    options.max_line_chars,
                    options.max_messages,
                )
            )
            or not isinstance(options.max_issue_records, int)
            or options.max_issue_records < 1
        ):
            issue(IssueSeverity.FATAL, IssueCode.INVALID_OPTIONS)
            return result()

        header: _InputLine | None = None
        speaker: str | None = None
        original_timestamp: str | None = None
        local: datetime | None = None
        utc: datetime | None = None
        body: list[str] = []
        body_chars = 0
        block_bad = False
        last_line = 0
        block_crlf = False
        block_bom = False

        def finish_block() -> None:
            nonlocal accepted, first, last, previous
            if header is None or speaker is None or local is None or utc is None:
                return
            location = SourceLocation(header.number, last_line)
            if block_bad:
                return
            trimmed = list(body)
            while trimmed and not trimmed[0].strip():
                trimmed.pop(0)
            while trimmed and not trimmed[-1].strip():
                trimmed.pop()
            content = "\n".join(trimmed)
            if not content.strip():
                issue(IssueSeverity.ERROR, IssueCode.EMPTY_BODY, location)
                return
            if len(content) > options.max_message_chars:
                issue(IssueSeverity.ERROR, IssueCode.OVERSIZED_MESSAGE, location)
                return
            if previous is not None:
                if utc == previous:
                    issue(IssueSeverity.WARNING, IssueCode.DUPLICATE_TIMESTAMP, location)
                elif utc < previous:
                    issue(IssueSeverity.WARNING, IssueCode.TIMESTAMP_OUT_OF_ORDER, location)
            if content in _PLACEHOLDERS:
                content_type = ContentType.PLACEHOLDER
            elif _BRACKET_MARKER.fullmatch(content):
                content_type = ContentType.UNKNOWN
            else:
                content_type = ContentType.TEXT
            notes = []
            if block_bom:
                notes.append("bom_removed")
            if block_crlf:
                notes.append("crlf_to_lf")
            if len(trimmed) != len(body):
                notes.append("surrounding_blank_lines_removed")
            canonical = {
                "source_format": FORMAT_WECHAT_MARKDOWN_V1,
                "parser_version": PARSER_VERSION,
                "schema_version": SCHEMA_VERSION,
                "timestamp_utc": utc.isoformat(),
                "raw_speaker_label": speaker,
                "content": content,
                "content_type": content_type.value,
            }
            fingerprint = hashlib.sha256(_canonical_json(canonical)).hexdigest()
            transcript_hash.update(bytes.fromhex(fingerprint))
            accepted += 1
            speakers[speaker] += 1
            if first is None:
                first = utc
            last = utc
            previous = utc
            if options.include_messages:
                messages.append(
                    ImportedMessage(
                        schema_version=SCHEMA_VERSION,
                        source_index=candidates,
                        original_timestamp=original_timestamp or "",
                        source_local_datetime=local,
                        source_timezone=options.source_timezone or "",
                        timestamp_utc=utc,
                        raw_speaker_label=speaker,
                        content=content,
                        content_type=content_type,
                        provenance=location,
                        normalization=tuple(notes),
                        fingerprint=fingerprint,
                    )
                )

        try:
            for line in _iter_lines(source, options.max_line_chars, source_hash):
                if line.text is None:
                    last_line = line.number
                    issue(
                        IssueSeverity.ERROR,
                        IssueCode.OVERSIZED_LINE,
                        SourceLocation(line.number, line.number),
                    )
                    if header is not None:
                        block_bad = True
                    continue
                if _HEADER_CANDIDATE.match(line.text):
                    finish_block()
                    last_line = line.number
                    candidates += 1
                    if candidates > options.max_messages:
                        issue(IssueSeverity.FATAL, IssueCode.MAX_MESSAGES_EXCEEDED)
                        return result()
                    header = line
                    speaker = None
                    original_timestamp = None
                    local = None
                    utc = None
                    body = []
                    body_chars = 0
                    block_bad = False
                    block_crlf = line.crlf
                    block_bom = line.bom
                    match = _HEADER.fullmatch(line.text)
                    if match is None:
                        issue(
                            IssueSeverity.ERROR,
                            IssueCode.INVALID_HEADER,
                            SourceLocation(line.number, line.number),
                        )
                        continue
                    speaker = match.group("speaker")
                    if not speaker.strip():
                        issue(
                            IssueSeverity.ERROR,
                            IssueCode.EMPTY_SPEAKER,
                            SourceLocation(line.number, line.number),
                        )
                        speaker = None
                        continue
                    if len(speaker) > options.max_speaker_chars:
                        issue(
                            IssueSeverity.ERROR,
                            IssueCode.OVERSIZED_SPEAKER,
                            SourceLocation(line.number, line.number),
                        )
                        speaker = None
                        continue
                    original_timestamp = f"{match.group('date')} {match.group('time')}"
                    try:
                        local = datetime.strptime(original_timestamp, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        issue(
                            IssueSeverity.ERROR,
                            IssueCode.INVALID_TIMESTAMP,
                            SourceLocation(line.number, line.number),
                        )
                        speaker = None
                        continue
                    utc, time_issue = _utc_from_local(local, zone)
                    if time_issue:
                        issue(
                            IssueSeverity.ERROR,
                            time_issue,
                            SourceLocation(line.number, line.number),
                        )
                        speaker = None
                    continue
                last_line = line.number
                if header is None:
                    if line.text.strip():
                        code = (
                            IssueCode.INVALID_HEADER
                            if line.text.startswith("## ")
                            else IssueCode.ORPHAN_TEXT
                        )
                        issue(IssueSeverity.ERROR, code, SourceLocation(line.number, line.number))
                    continue
                block_crlf |= line.crlf
                if block_bad or speaker is None:
                    continue
                body_chars += len(line.text) + (1 if body else 0)
                if body_chars > options.max_message_chars + options.max_line_chars:
                    block_bad = True
                    issue(
                        IssueSeverity.ERROR,
                        IssueCode.OVERSIZED_MESSAGE,
                        SourceLocation(header.number, line.number),
                    )
                    body = []
                    continue
                body.append(line.text)
            source_complete = True
            finish_block()
        except (UnicodeError, TypeError):
            issue(IssueSeverity.FATAL, IssueCode.INVALID_ENCODING)
            return result()
        if accepted == 0:
            issue(
                IssueSeverity.FATAL,
                IssueCode.NO_VALID_STRUCTURE if candidates else IssueCode.UNSUPPORTED_FORMAT,
            )
        return result()
