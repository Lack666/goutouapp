"""Anonymous ICA v3 preparation and exchange format regressions."""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.chat_import.analysis_scope import (
    AnalysisScope,
    ScopeMessage,
    calendar_window,
    prepare_context,
    preview,
    validate_evidence,
)
from app.chat_import.chatlab_jsonl import FORMAT_CHATLAB_JSONL, ChatLabJSONLParser
from app.chat_import.contracts import ChatImportSource, ImportOptions


def fixture_rows():
    return [
        {
            "_type": "header",
            "chatlab": {"version": "0.0.2", "exportedAt": 1793577600, "generator": "WeFlow"},
            "meta": {"name": "Synthetic", "platform": "wechat", "type": "private"},
        },
        {"_type": "member", "platformId": "sender-a", "accountName": "Same nickname"},
        {"_type": "member", "platformId": "sender-b", "accountName": "Same nickname"},
        {
            "_type": "message",
            "sender": "sender-a",
            "accountName": "Same nickname",
            "timestamp": 1793577600,
            "type": 0,
            "content": "好😀",
            "platformMessageId": "a",
        },
        {
            "_type": "message",
            "sender": "sender-b",
            "accountName": "Same nickname",
            "timestamp": 1793577601,
            "type": 0,
            "content": "好😀",
            "platformMessageId": "b",
            "replyToMessageId": "a",
        },
    ]


def parse(rows):
    raw = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows)
    return ChatLabJSONLParser().parse(
        ChatImportSource([raw.encode()]),
        ImportOptions(source_timezone="Asia/Shanghai", source_format=FORMAT_CHATLAB_JSONL),
    )


def test_jsonl_occurrences_and_provenance():
    result = parse(fixture_rows())
    assert not result.fatal and result.message_count == 2
    a, b = result.messages
    assert a.raw_speaker_label != b.raw_speaker_label
    assert a.content == b.content and a.fingerprint != b.fingerprint
    assert b.external_reply_id == "a" and b.external_message_id == "b"
    assert a.provenance.line_start == 4 and b.provenance.line_end == 5
    assert a.timestamp_utc.tzinfo == UTC


@pytest.mark.parametrize("change", ["version", "milliseconds", "bool", "sender", "badline"])
def test_jsonl_negative(change):
    rows = fixture_rows()
    if change == "version":
        rows[0]["chatlab"]["version"] = "0.0.1"
    elif change == "milliseconds":
        rows[-1]["timestamp"] *= 1000
    elif change == "bool":
        rows[-1]["timestamp"] = True
    elif change == "sender":
        rows[-1]["sender"] = ""
    else:
        rows.append("bad")
    assert parse(rows).fatal


def test_nontext_and_reverse_time():
    rows = fixture_rows()
    rows[-1].update(timestamp=1793577599, type=1, content=None)
    result = parse(rows)
    assert not result.fatal and result.warning_count == 2
    assert result.messages[-1].content_type == "placeholder"


def sample(n=900, body="好😀"):
    now = datetime(2026, 11, 2, 10, tzinfo=UTC)
    start, end = calendar_window("Asia/Shanghai", now, days=3)
    scope = AnalysisScope(uuid4(), uuid4(), uuid4(), "Asia/Shanghai", start, end)
    messages = [
        ScopeMessage(
            UUID(int=i + 1),
            scope.owner_id,
            scope.person_id,
            scope.dataset_id,
            start + timedelta(seconds=i),
            "self" if i % 2 else "person",
            body,
        )
        for i in range(n)
    ]
    return scope, messages


@pytest.mark.parametrize("n,k", [(900, 5), (2100, 11), (6400, 32)])
def test_full_core(n, k):
    scope, messages = sample(n)
    context = prepare_context(scope, list(reversed(messages)))
    assert preview(context)["messages"] == n
    assert len(context.chunks) == k
    assert sum(len(c.core) for c in context.chunks) == n
    assert context == prepare_context(scope, messages)
    assert all(len(c.halo_before) <= 20 and len(c.halo_after) <= 20 for c in context.chunks)


@pytest.mark.parametrize(
    "n,body",
    [(10000, "x"), (6401, "x"), (1, "x" * 49153), (100, "x" * 30000)],
    ids=["10k", "6401", "oversized", "bytes"],
)
def test_admission_rejects_whole(n, body):
    scope, messages = sample(n, body)
    with pytest.raises(ValueError):
        prepare_context(scope, messages)


def test_owner_dataset_window_unicode():
    scope, messages = sample(2)
    context = prepare_context(scope, messages)
    assert validate_evidence(context, messages[0].id, 1, 2, "😀") == messages[0]
    for args in [(uuid4(), 0, 1, "好"), (messages[0].id, 1, 3, "😀")]:
        with pytest.raises(ValueError):
            validate_evidence(context, *args)
    for change in [
        {"owner_id": uuid4()},
        {"dataset_id": uuid4()},
        {"person_id": uuid4()},
        {"timestamp": scope.end},
    ]:
        with pytest.raises(ValueError):
            prepare_context(scope, [replace(messages[0], **change)])


def test_dst_window():
    now = datetime(2026, 11, 2, 12, tzinfo=UTC)
    start, end = calendar_window("America/New_York", now, days=3)
    assert start == datetime(2026, 10, 31, 4, tzinfo=UTC)
    assert end == now
    start7, _ = calendar_window("America/New_York", now, days=7)
    assert start7 == datetime(2026, 10, 27, 4, tzinfo=UTC)


def test_session_gap_and_halo_bounds():
    scope, messages = sample(201, "x" * 1000)
    messages[40:] = [replace(m, timestamp=m.timestamp + timedelta(hours=1)) for m in messages[40:]]
    context = prepare_context(scope, messages)
    assert len(context.chunks[0].core) == 40
    sizes = {m.id: m.size for m in messages}
    for chunk in context.chunks:
        assert sum(sizes[i] for i in chunk.core) <= 48 * 1024
        for side in (chunk.halo_before, chunk.halo_after):
            assert sum(sizes[i] for i in side) <= 4096


def test_parser_callback_failure_propagates():
    raw = "\n".join(json.dumps(r) for r in fixture_rows())

    def fail(_):
        raise ValueError("transaction failure")

    with pytest.raises(ValueError, match="transaction failure"):
        ChatLabJSONLParser().parse(
            ChatImportSource([raw]), ImportOptions(source_timezone="UTC"), fail
        )
