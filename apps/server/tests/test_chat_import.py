"""Phase 5A contract and streaming parser tests using synthetic text only."""

from datetime import UTC, datetime
from io import BytesIO, StringIO
from pathlib import Path

import pytest

from app.chat_import import (
    FORMAT_WECHAT_MARKDOWN_V1,
    ChatImportParser,
    ChatImportSource,
    ContentType,
    ImportOptions,
    IssueCode,
    IssueSeverity,
    WeChatMarkdownParser,
)

FIXTURE = Path(__file__).parent / "fixtures" / "wechat_markdown_v1.md"
ZONE = "Asia/Shanghai"


def parse(text: str | bytes, **kwargs: object):
    stream = StringIO(text) if isinstance(text, str) else BytesIO(text)
    return WeChatMarkdownParser().parse(
        ChatImportSource(stream, "synthetic.md"), ImportOptions(source_timezone=ZONE, **kwargs)
    )


def codes(result) -> list[IssueCode]:
    return [entry.code for entry in result.issues]


def test_protocol_fixture_unicode_speakers_and_provenance() -> None:
    parser: ChatImportParser = WeChatMarkdownParser()
    with FIXTURE.open("rb") as stream:
        result = parser.parse(ChatImportSource(stream), ImportOptions(source_timezone=ZONE))
    assert not result.fatal
    assert result.source_format == FORMAT_WECHAT_MARKDOWN_V1
    assert result.parser_version == result.schema_version == "1"
    assert result.message_count == 4
    assert [m.source_index for m in result.messages] == [1, 2, 3, 4]
    assert [m.raw_speaker_label for m in result.messages] == ["怡宝🥰"] * 3 + ["我"]
    assert [(s.raw_speaker_label, s.message_count) for s in result.speaker_counts] == [
        ("怡宝🥰", 3),
        ("我", 1),
    ]
    assert result.messages[0].provenance.line_start == 1
    assert result.messages[0].provenance.line_end == 4
    assert result.messages[-1].provenance.line_end == 15
    assert result.messages[0].original_timestamp == "2023-11-09 07:51:23"
    assert result.messages[0].source_local_datetime == datetime(2023, 11, 9, 7, 51, 23)
    assert result.messages[0].timestamp_utc == datetime(2023, 11, 8, 23, 51, 23, tzinfo=UTC)
    assert result.messages[0].source_timezone == ZONE


def test_multiline_preserves_internal_blank_and_header_like_body() -> None:
    result = parse("## 2023-11-09 07:51:23 A\n\n第一行\n\n## hello\n第二行\n\n")
    assert result.message_count == 1
    assert result.messages[0].content == "第一行\n\n## hello\n第二行"
    assert result.messages[0].normalization == ("surrounding_blank_lines_removed",)


@pytest.mark.parametrize(
    ("marker", "expected"),
    [
        ("[表情包]", ContentType.PLACEHOLDER),
        ("[图片]", ContentType.PLACEHOLDER),
        ("[语音]", ContentType.PLACEHOLDER),
        ("[未识别]", ContentType.UNKNOWN),
    ],
)
def test_marker_is_preserved_without_inventing_media(marker: str, expected: ContentType) -> None:
    result = parse(f"## 2023-11-09 07:51:23 A\n\n{marker}\n")
    assert result.messages[0].content == marker
    assert result.messages[0].content_type == expected


def test_bom_crlf_and_split_byte_chunks() -> None:
    raw = "\ufeff## 2023-11-09 07:51:23 怡宝🥰\r\n\r\n你好\r\n".encode()
    result = WeChatMarkdownParser().parse(
        ChatImportSource(raw[i : i + 1] for i in range(len(raw))),
        ImportOptions(source_timezone=ZONE),
    )
    assert result.message_count == 1
    assert result.messages[0].content == "你好"
    assert result.messages[0].normalization == (
        "bom_removed",
        "crlf_to_lf",
        "surrounding_blank_lines_removed",
    )
    assert result.source_fingerprint == parse(raw).source_fingerprint


def test_duplicate_out_of_order_keeps_source_order() -> None:
    result = parse(
        "## 2023-11-09 10:00:00 A\n\na\n"
        "## 2023-11-09 10:00:00 B\n\nb\n"
        "## 2023-11-09 09:00:00 C\n\nc\n"
    )
    assert [m.raw_speaker_label for m in result.messages] == ["A", "B", "C"]
    assert [m.source_index for m in result.messages] == [1, 2, 3]
    assert codes(result) == [IssueCode.DUPLICATE_TIMESTAMP, IssueCode.TIMESTAMP_OUT_OF_ORDER]
    assert all(i.severity == IssueSeverity.WARNING for i in result.issues)
    assert len(result.speaker_counts) == 3
    assert result.first_timestamp_utc > result.last_timestamp_utc


def test_malformed_empty_and_invalid_blocks_are_reported_and_skipped() -> None:
    result = parse(
        "## malformed\n"
        "## 2023-11-09 wrong A\n\nbad\n"
        "## 2023-11-09 07:51:23 \n\nno speaker\n"
        "## 2023-13-09 07:51:23 A\n\nbad date\n"
        "## 2023-11-09 07:51:23 A\n\n"
        "## 2023-11-09 07:51:24 A\n\ngood\n"
    )
    assert result.message_count == 1
    assert result.messages[0].source_index == 5
    assert {
        IssueCode.INVALID_HEADER,
        IssueCode.EMPTY_SPEAKER,
        IssueCode.INVALID_TIMESTAMP,
        IssueCode.EMPTY_BODY,
    } <= set(codes(result))
    assert result.error_count == 5


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (b"\xff\xfe", IssueCode.INVALID_ENCODING),
        ("plain export", IssueCode.UNSUPPORTED_FORMAT),
        ("## 2023-11-09 07:51:23 A\n\n", IssueCode.NO_VALID_STRUCTURE),
    ],
)
def test_fatal_bad_sources(text: str | bytes, expected: IssueCode) -> None:
    result = parse(text)
    assert result.fatal
    assert expected in codes(result)


def test_timezone_required_invalid_and_dst_edges() -> None:
    source = ChatImportSource(StringIO("## 2023-11-09 07:51:23 A\n\nx\n"))
    missing = WeChatMarkdownParser().parse(source, ImportOptions())
    assert codes(missing) == [IssueCode.TIMEZONE_REQUIRED]
    invalid = WeChatMarkdownParser().parse(
        ChatImportSource(StringIO("## 2023-11-09 07:51:23 A\n\nx\n")),
        ImportOptions(source_timezone="Bad/Zone"),
    )
    assert codes(invalid) == [IssueCode.INVALID_TIMEZONE]
    spring = WeChatMarkdownParser().parse(
        ChatImportSource(StringIO("## 2024-03-10 02:30:00 A\n\nx\n")),
        ImportOptions(source_timezone="America/New_York"),
    )
    assert IssueCode.NONEXISTENT_LOCAL_TIME in codes(spring)
    autumn = WeChatMarkdownParser().parse(
        ChatImportSource(StringIO("## 2024-11-03 01:30:00 A\n\nx\n")),
        ImportOptions(source_timezone="America/New_York"),
    )
    assert IssueCode.AMBIGUOUS_LOCAL_TIME in codes(autumn)


def test_timezone_changes_canonical_utc_and_fingerprint() -> None:
    text = "## 2023-11-09 07:51:23 A\n\nx\n"
    china = parse(text)
    utc = WeChatMarkdownParser().parse(
        ChatImportSource(StringIO(text)), ImportOptions(source_timezone="UTC")
    )
    assert china.messages[0].timestamp_utc != utc.messages[0].timestamp_utc
    assert china.messages[0].fingerprint != utc.messages[0].fingerprint


def test_limits_skip_bad_record_and_issue_cap() -> None:
    result = parse(
        "## 2023-11-09 07:51:23 A\n\n123456789012345\n## 2023-11-09 07:51:24 A\n\nok\n",
        max_message_chars=10,
    )
    assert result.message_count == 1
    assert result.messages[0].source_index == 2
    assert IssueCode.OVERSIZED_MESSAGE in codes(result)
    capped = parse("orphan\n" * 5 + "## 2023-11-09 07:51:23 A\n\nx\n", max_issue_records=2)
    assert len(capped.issues) == 2
    assert capped.issues_truncated == 3
    assert capped.error_count == 5


def test_oversized_line_and_max_messages() -> None:
    text = "## 2023-11-09 07:51:23 A\n\n" + "x" * 30 + "\n"
    result = parse(text, max_line_chars=25)
    assert IssueCode.OVERSIZED_LINE in codes(result)
    limited = parse(
        "## 2023-11-09 07:51:23 A\n\nx\n## 2023-11-09 07:51:24 B\n\ny\n",
        max_messages=1,
    )
    assert IssueCode.MAX_MESSAGES_EXCEEDED in codes(limited)
    assert limited.source_fingerprint is None


def test_fingerprints_are_stable_and_not_based_on_name_or_source_index() -> None:
    a = "## 2023-11-09 07:51:23 A\n\nx\n"
    b = "## 2023-11-09 07:51:24 B\n\ny\n"
    one = parse(a + b)
    same = parse(a + b)
    prepended = parse("## 2023-11-09 07:51:22 C\n\nz\n" + a + b)
    assert one.transcript_fingerprint == same.transcript_fingerprint
    assert one.source_fingerprint == same.source_fingerprint
    assert [m.fingerprint for m in one.messages] == [m.fingerprint for m in prepended.messages[1:]]
    assert one.transcript_fingerprint != prepended.transcript_fingerprint
    assert one.messages[0].source_index != prepended.messages[1].source_index
    assert one.messages[0].fingerprint == prepended.messages[1].fingerprint


def test_summary_mode_and_10k_incremental_generator() -> None:
    class NoRead:
        def __iter__(self):
            for index in range(10_000):
                yield f"## 2023-11-09 10:00:00 S{index % 3}\n"
                yield "\n"
                yield f"synthetic {index}\n"

        def read(self, *_args: object) -> None:
            raise AssertionError("whole-source read must not be used")

    result = WeChatMarkdownParser().parse(
        ChatImportSource(NoRead()), ImportOptions(source_timezone=ZONE, include_messages=False)
    )
    assert result.message_count == 10_000
    assert result.messages == ()
    assert [s.message_count for s in result.speaker_counts] == [3334, 3333, 3333]
    assert result.warning_count == 9999
    assert result.fatal_count == 0
    assert result.source_fingerprint and result.transcript_fingerprint


def test_issue_messages_do_not_echo_private_content() -> None:
    private = "PRIVATE_CHAT_SECRET_712"
    result = parse(f"{private}\n## 2023-11-09 07:51:23 A\n\nx\n")
    assert result.error_count == 1
    assert private not in repr(result.issues)
