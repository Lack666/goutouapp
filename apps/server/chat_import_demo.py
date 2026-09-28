"""Offline Phase 5A dry run; prints summary metadata, never chat bodies."""

import argparse
import json
from pathlib import Path

from app.chat_import import ChatImportSource, ImportOptions, WeChatMarkdownParser


def main() -> int:
    cli = argparse.ArgumentParser()
    cli.add_argument(
        "source",
        nargs="?",
        type=Path,
        default=Path(__file__).parent / "tests" / "fixtures" / "wechat_markdown_v1.md",
    )
    cli.add_argument("--source-timezone", required=False, default="Asia/Shanghai")
    arguments = cli.parse_args()
    with arguments.source.open("rb") as stream:
        result = WeChatMarkdownParser().parse(
            ChatImportSource(stream, source_name=arguments.source.name),
            ImportOptions(source_timezone=arguments.source_timezone, include_messages=False),
        )
    print(
        json.dumps(
            {
                "format": result.source_format,
                "parser_version": result.parser_version,
                "schema_version": result.schema_version,
                "message_count": result.message_count,
                "speaker_counts": [
                    {"label": entry.raw_speaker_label, "count": entry.message_count}
                    for entry in result.speaker_counts
                ],
                "first_timestamp_utc": (
                    result.first_timestamp_utc.isoformat() if result.first_timestamp_utc else None
                ),
                "last_timestamp_utc": (
                    result.last_timestamp_utc.isoformat() if result.last_timestamp_utc else None
                ),
                "warning_count": result.warning_count,
                "error_count": result.error_count,
                "fatal_count": result.fatal_count,
                "issue_codes": [entry.code.value for entry in result.issues],
                "issues_truncated": result.issues_truncated,
                "source_fingerprint": result.source_fingerprint,
                "transcript_fingerprint": result.transcript_fingerprint,
            },
            ensure_ascii=True,
        )
    )
    return 1 if result.fatal else 0


if __name__ == "__main__":
    raise SystemExit(main())
