"""Independent ChatLab v0.0.2 field adapter; no upstream implementation code."""

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.chat_import.contracts import (
    ChatParseResult,
    ContentType,
    ImportedMessage,
    ImportIssue,
    IssueCode,
    IssueSeverity,
    SourceLocation,
    SpeakerCount,
)
from app.chat_import.wechat_markdown import _canonical_json, _iter_lines

FORMAT_CHATLAB_JSONL = "chatlab_jsonl_v0_0_2"


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


class ChatLabJSONLParser:
    def parse(self, source, options, on_message=None):
        messages, issues = [], []
        speakers = Counter()
        source_hash, transcript = hashlib.sha256(), hashlib.sha256(FORMAT_CHATLAB_JSONL.encode())
        count = failures = warnings = truncated = 0
        first = last = previous = None
        header = in_messages = False
        members = set()

        def issue(code, line, fatal=True):
            nonlocal failures, warnings, truncated
            failures += int(fatal)
            warnings += int(not fatal)
            if len(issues) < options.max_issue_records:
                issues.append(
                    ImportIssue(
                        IssueSeverity.FATAL if fatal else IssueSeverity.WARNING,
                        code,
                        SourceLocation(line, line),
                        "Invalid or unsupported JSONL record",
                    )
                )
            else:
                truncated += 1

        try:
            zone = ZoneInfo(options.source_timezone or "")
        except (ValueError, ZoneInfoNotFoundError):
            issue(IssueCode.INVALID_TIMEZONE, 1)
            zone = ZoneInfo("UTC")
        if options.source_format not in (None, FORMAT_CHATLAB_JSONL):
            issue(IssueCode.UNSUPPORTED_FORMAT, 1)
        try:
            for line in _iter_lines(source, options.max_line_chars, source_hash):
                if line.text is None:
                    issue(IssueCode.OVERSIZED_LINE, line.number)
                    continue
                if header and (not line.text.strip() or line.text.startswith("#")):
                    continue
                try:
                    row = json.loads(line.text, object_pairs_hook=_unique_object)
                    if not isinstance(row, dict):
                        raise ValueError
                    kind = row.get("_type")
                    if not header:
                        meta, info = row["meta"], row["chatlab"]
                        if line.number != 1 or kind != "header" or info["version"] != "0.0.2":
                            raise ValueError
                        self._timestamp(info["exportedAt"])
                        if meta["type"] not in ("private", "group"):
                            raise ValueError
                        self._string(meta["name"])
                        self._string(meta["platform"])
                        header = True
                        continue
                    if kind == "member":
                        member = self._string(row["platformId"], options.max_speaker_chars)
                        self._string(row["accountName"])
                        if in_messages or member in members or len(members) >= 1024:
                            raise ValueError
                        members.add(member)
                        continue
                    if kind != "message":
                        raise ValueError
                    in_messages = True
                    sender = self._string(row["sender"], options.max_speaker_chars)
                    if members and sender not in members:
                        raise ValueError
                    self._string(row["accountName"])
                    timestamp = self._timestamp(row["timestamp"])
                    typ = row["type"]
                    if type(typ) is not int or typ < 0:
                        raise ValueError
                    content = row["content"]
                    if content is not None and not isinstance(content, str):
                        raise ValueError
                    if content is not None and "\x00" in content:
                        raise ValueError
                    content = (content or "").replace("\r\n", "\n").replace("\r", "\n")
                    empty = not content.strip()
                    if empty:
                        content = "[empty text]" if typ == 0 else f"[non-text:{typ}]"
                    if len(content) > options.max_message_chars:
                        issue(IssueCode.OVERSIZED_MESSAGE, line.number)
                        continue
                    external = row.get("platformMessageId")
                    reply = row.get("replyToMessageId")
                    for value in (external, reply):
                        if value is not None:
                            self._string(value, 1024)
                    count += 1
                    if count > options.max_messages:
                        issue(IssueCode.MAX_MESSAGES_EXCEEDED, line.number)
                        break
                    if len(speakers) >= 1024 and sender not in speakers:
                        raise ValueError
                    if previous is not None and timestamp < previous:
                        issue(IssueCode.TIMESTAMP_OUT_OF_ORDER, line.number, False)
                    if empty:
                        issue(IssueCode.EMPTY_BODY, line.number, False)
                    previous = timestamp
                    first = min(first, timestamp) if first else timestamp
                    last = max(last, timestamp) if last else timestamp
                    fingerprint = hashlib.sha256(
                        _canonical_json(
                            [sender, row["timestamp"], typ, content, external, reply, count]
                        )
                    ).hexdigest()
                    message = ImportedMessage(
                        "1",
                        count,
                        timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        timestamp.astimezone(zone).replace(tzinfo=None),
                        str(zone),
                        timestamp,
                        sender,
                        content,
                        ContentType.TEXT if typ == 0 and not empty else ContentType.PLACEHOLDER,
                        SourceLocation(line.number, line.number),
                        (),
                        fingerprint,
                        external,
                        reply,
                        typ,
                    )
                    transcript.update(fingerprint.encode())
                    speakers[sender] += 1
                    if options.include_messages:
                        messages.append(message)
                except (KeyError, TypeError, ValueError, OverflowError, OSError):
                    issue(IssueCode.INVALID_HEADER, line.number)
                    continue
                # Persistence/caller failures must abort the transaction, not become bad rows.
                if on_message:
                    on_message(message)
        except UnicodeError:
            issue(IssueCode.INVALID_ENCODING, 1)
        if not header or not count:
            issue(IssueCode.NO_VALID_STRUCTURE, 1)
        return ChatParseResult(
            "1",
            FORMAT_CHATLAB_JSONL,
            options.source_timezone,
            "1",
            source.source_name,
            tuple(messages),
            count,
            tuple(SpeakerCount(k, v) for k, v in speakers.items()),
            first,
            last,
            warnings,
            0,
            failures,
            tuple(issues),
            truncated,
            source_hash.hexdigest(),
            transcript.hexdigest(),
        )

    @staticmethod
    def _string(value, maximum=25000):
        if (
            not isinstance(value, str)
            or not value.strip()
            or len(value) > maximum
            or "\x00" in value
        ):
            raise ValueError
        return value

    @staticmethod
    def _timestamp(value):
        # Millisecond values, booleans, NaN and subsecond timestamps are rejected.
        if type(value) not in (int, float) or value != int(value) or not 0 <= value <= 253402300799:
            raise ValueError
        return datetime.fromtimestamp(value, UTC)
