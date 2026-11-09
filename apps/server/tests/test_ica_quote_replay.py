"""Historical output migration never fabricates a missing model stage or a new report."""

import asyncio
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.chat_import.analysis_scope import AnalysisScope, ScopeMessage, prepare_context
from evals.ica.quote_replay import (
    RecordedOnlyProvider,
    RecordingUnavailable,
    audit_output,
    load_recordings,
    migrate_quotes,
    replay_recording,
)
from evals.ica.runner import case_to_contexts, load_cases


def contexts(*bodies):
    owner, person, dataset = uuid4(), uuid4(), uuid4()
    start = datetime(2026, 1, 1, tzinfo=UTC)
    scope = AnalysisScope(owner, person, dataset, "Asia/Shanghai", start, start + timedelta(days=3))
    return (
        prepare_context(
            scope,
            [
                ScopeMessage(
                    uuid4(), owner, person, dataset, start + timedelta(seconds=index), "self", body
                )
                for index, body in enumerate(bodies)
            ],
        ),
    )


def ref(quote, **changes):
    return {
        "evidence_id": "w0-m00001",
        "speaker": "self",
        "start": 0,
        "end": len(quote),
        "quote": quote,
        **changes,
    }


def recording(case_id, arm):
    _, grouped = load_recordings()
    case = next(case for case in load_cases("holdout") if case["case_id"] == case_id)
    return case, grouped[case_id, arm]


def test_migration_removes_only_exact_legacy_evidence_offsets():
    original = {
        "decision": "normal",
        "risks": [{"evidence": [ref("literal😀")]}],
        "unrelated": {"start": 2, "end": 9},
        "extra_field_ref": {**ref("x"), "untrusted_extra": "keep"},
        "review": {"approved": True, "reason_codes": ["uncertain"]},
    }
    untouched = deepcopy(original)
    migrated = migrate_quotes(original)
    assert migrated["risks"][0]["evidence"] == [
        {"evidence_id": "w0-m00001", "speaker": "self", "quote": "literal😀"}
    ]
    assert migrated["unrelated"] == original["unrelated"]
    assert migrated["extra_field_ref"] == original["extra_field_ref"]
    assert migrated["decision"] == "normal" and migrated["risks"]
    assert migrated["review"] == original["review"]
    assert original == untouched


def test_fixed_call9_is_source_exact_despite_invalid_legacy_offsets():
    case, sequence = recording("ica-v1-em-ho-exam", "baseline")
    item = next(item for item in sequence if item["call_id"] == 9)
    details = audit_output(case_to_contexts(case), item, json.loads(item["visible_output"]))
    first = details[0]
    assert first["accepted"] is True and first["old_span_valid"] is False
    assert first["old_span"] == [0, 21] and first["new_span"] == [0, 17]
    assert first["message_id"] == case["messages"][0]["message_id"]


def test_audit_keeps_duplicate_message_occurrences_separate_and_rejects_ambiguity():
    ctxs = contexts("你好😀", "你好😀", "哈哈哈")
    chunk_id = ctxs[0].chunks[0].id
    details = audit_output(
        ctxs,
        {"chunk_id": chunk_id},
        [
            ref("你好😀"),
            ref("你好😀", evidence_id="w0-m00002"),
            ref("哈哈", evidence_id="w0-m00003"),
        ],
    )
    assert details[0]["accepted"] and details[1]["accepted"]
    assert details[0]["message_id"] != details[1]["message_id"]
    assert details[2]["accepted"] is False
    assert details[2]["reason"] == "quote_missing_or_ambiguous"


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"evidence_id": "w1-m99999"}, "unknown_alias"),
        ({"speaker": "person"}, "wrong_speaker"),
        ({"quote": "é"}, "quote_missing_or_ambiguous"),
    ],
)
def test_audit_does_not_expand_scope_guess_speakers_or_normalize_unicode(change, reason):
    ctxs = contexts("e\u0301")
    legacy = {**ref("e\u0301"), **change}
    details = audit_output(ctxs, {"chunk_id": ctxs[0].chunks[0].id}, [legacy])
    assert details[0]["accepted"] is False and details[0]["reason"] == reason


def test_unknown_chunk_rejects_reference_instead_of_falling_back_to_whole_scope():
    details = audit_output(contexts("hello"), {"chunk_id": "missing-chunk"}, [ref("hello")])
    assert details[0]["accepted"] is False
    assert details[0]["reason"] == "outside_recorded_chunk"


@pytest.mark.parametrize("stage,chunk", [("interaction", "fixed"), ("safety", "different")])
def test_recording_stage_and_chunk_must_match_before_consumption(stage, chunk):
    provider = RecordedOnlyProvider([{"stage": "safety", "chunk_id": "fixed", "call_id": 1}])
    with pytest.raises(RecordingUnavailable, match="stage_or_chunk_mismatch"):
        asyncio.run(provider.before(stage, chunk, (), type("Schema", (), {})))
    assert provider.cursor == 0 and provider.attempts[-1]["status"] == "not_recorded"


def test_real_trace_stops_at_unrecorded_counterevidence_without_fabricating_completion():
    case, sequence = recording("ica-v1-em-ho-exam", "baseline")
    result = asyncio.run(replay_recording(case, "baseline", sequence))
    assert result["migration_only"] and result["external_provider_calls"] == 0
    assert result["status"] == "recording_incomplete"
    assert result["incomplete_recording"] and result["error_code"] == "recording_exhausted"
    assert result["report"] is None
    assert result["recorded_stages_consumed"] == result["recorded_stages_available"] == 2
    assert [item["status"] for item in result["attempts"]] == [
        "validated",
        "validated",
        "not_recorded",
    ]
    assert result["attempts"][-1]["stage"] == "counterevidence"


def test_real_normal_with_risks_remains_rejected_after_offset_migration():
    case, sequence = recording("ica-v1-em-ho-exam", "event")
    result = asyncio.run(replay_recording(case, "event", sequence))
    assert result["status"] == "validation_rejected" and result["report"] is None
    assert result["error_code"] == "invalid_model_output"
    assert result["recorded_stages_consumed"] == 1


def test_real_uncertain_review_still_rejects_after_offset_migration():
    case, sequence = recording("ica-v1-rc-ho-different-topics", "event")
    result = asyncio.run(replay_recording(case, "event", sequence))
    assert result["status"] == "validation_rejected" and result["report"] is None
    assert result["error_code"] == "content_review_rejected"
    assert result["recorded_stages_consumed"] == len(sequence)
