"""Deterministic, transport-independent chat import contracts and parser."""

from app.chat_import.contracts import (
    FORMAT_WECHAT_MARKDOWN_V1,
    ChatImportParser,
    ChatImportSource,
    ChatParseResult,
    ContentType,
    ImportedMessage,
    ImportIssue,
    ImportOptions,
    IssueCode,
    IssueSeverity,
)
from app.chat_import.wechat_markdown import WeChatMarkdownParser

__all__ = [
    "ChatImportParser",
    "ChatImportSource",
    "ChatParseResult",
    "ContentType",
    "FORMAT_WECHAT_MARKDOWN_V1",
    "ImportedMessage",
    "ImportIssue",
    "ImportOptions",
    "IssueCode",
    "IssueSeverity",
    "WeChatMarkdownParser",
]
