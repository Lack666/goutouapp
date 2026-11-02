"""Explicit format selection shared by registration and atomic reparse."""

from app.chat_import.chatlab_jsonl import FORMAT_CHATLAB_JSONL, ChatLabJSONLParser
from app.chat_import.contracts import FORMAT_WECHAT_MARKDOWN_V1
from app.chat_import.wechat_markdown import WeChatMarkdownParser

SUPPORTED_FORMATS = {FORMAT_WECHAT_MARKDOWN_V1, FORMAT_CHATLAB_JSONL}


def parser_for(source_format):
    if source_format == FORMAT_CHATLAB_JSONL:
        return ChatLabJSONLParser()
    if source_format in (None, FORMAT_WECHAT_MARKDOWN_V1):
        return WeChatMarkdownParser()
    raise ValueError("unsupported format")
