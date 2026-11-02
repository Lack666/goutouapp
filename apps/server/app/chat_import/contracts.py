"""Transport-free contracts for a dry-run chat export parser."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

FORMAT_WECHAT_MARKDOWN_V1 = "wechat_markdown_v1"
PARSER_VERSION = "1"
SCHEMA_VERSION = "1"


class ContentType(StrEnum):
    TEXT = "text"
    PLACEHOLDER = "placeholder"
    UNKNOWN = "unknown"


class IssueSeverity(StrEnum):
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


class IssueCode(StrEnum):
    UNSUPPORTED_FORMAT = "unsupported_format"
    UNSUPPORTED_ENCODING = "unsupported_encoding"
    INVALID_ENCODING = "invalid_encoding"
    TIMEZONE_REQUIRED = "timezone_required"
    INVALID_TIMEZONE = "invalid_timezone"
    INVALID_OPTIONS = "invalid_options"
    NO_VALID_STRUCTURE = "no_valid_structure"
    INVALID_HEADER = "invalid_header"
    INVALID_TIMESTAMP = "invalid_timestamp"
    AMBIGUOUS_LOCAL_TIME = "ambiguous_local_time"
    NONEXISTENT_LOCAL_TIME = "nonexistent_local_time"
    EMPTY_SPEAKER = "empty_speaker"
    OVERSIZED_SPEAKER = "oversized_speaker"
    EMPTY_BODY = "empty_body"
    OVERSIZED_MESSAGE = "oversized_message"
    OVERSIZED_LINE = "oversized_line"
    MAX_MESSAGES_EXCEEDED = "max_messages_exceeded"
    ORPHAN_TEXT = "orphan_text"
    DUPLICATE_TIMESTAMP = "duplicate_timestamp"
    TIMESTAMP_OUT_OF_ORDER = "timestamp_out_of_order"


@dataclass(frozen=True)
class ChatImportSource:
    """One-pass text or UTF-8 byte chunks; a TextIO/BinaryIO iterator works."""

    chunks: Iterable[str] | Iterable[bytes]
    source_name: str | None = None


@dataclass(frozen=True)
class ImportOptions:
    source_timezone: str | None = None
    source_format: str | None = None
    encoding: str = "utf-8-sig"
    max_message_chars: int = 20_000
    max_speaker_chars: int = 120
    max_line_chars: int = 25_000
    max_messages: int = 1_000_000
    max_issue_records: int = 1_000
    include_messages: bool = True


@dataclass(frozen=True)
class SourceLocation:
    line_start: int
    line_end: int


@dataclass(frozen=True)
class ImportIssue:
    severity: IssueSeverity
    code: IssueCode
    location: SourceLocation | None
    safe_message: str


@dataclass(frozen=True)
class ImportedMessage:
    schema_version: str
    source_index: int
    original_timestamp: str
    source_local_datetime: datetime
    source_timezone: str
    timestamp_utc: datetime
    raw_speaker_label: str
    content: str
    content_type: ContentType
    provenance: SourceLocation
    normalization: tuple[str, ...]
    fingerprint: str
    external_message_id: str | None = None
    external_reply_id: str | None = None
    external_message_type: int | None = None


@dataclass(frozen=True)
class SpeakerCount:
    raw_speaker_label: str
    message_count: int


@dataclass(frozen=True)
class ChatParseResult:
    schema_version: str
    source_format: str | None
    source_timezone: str | None
    parser_version: str
    source_name: str | None
    messages: tuple[ImportedMessage, ...]
    message_count: int
    speaker_counts: tuple[SpeakerCount, ...]
    first_timestamp_utc: datetime | None
    last_timestamp_utc: datetime | None
    warning_count: int
    error_count: int
    fatal_count: int
    issues: tuple[ImportIssue, ...]
    issues_truncated: int
    source_fingerprint: str | None
    transcript_fingerprint: str | None

    @property
    def fatal(self) -> bool:
        return self.fatal_count > 0


class ChatImportParser(Protocol):
    def parse(
        self,
        source: ChatImportSource,
        options: ImportOptions,
        on_message: Callable[[ImportedMessage], None] | None = None,
    ) -> ChatParseResult: ...
