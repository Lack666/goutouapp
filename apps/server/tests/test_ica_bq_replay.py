"""Replay fixed visible synthetic live failures offline; never retry a paid request."""

import asyncio
import hashlib
import json
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.agent.imported_contracts import ChunkInteractions, ChunkSafety, ContentReview
from app.chat_import.analysis_scope import validate_evidence
from app.llm.mock import MockLLMProvider
from evals.ica.runner import case_to_contexts, evaluate_case, load_cases

CALLS = Path(__file__).resolve().parents[3] / "docs/evidence/ica-bq/batch-v1/calls.jsonl"
OUTPUT_HASHES = {
    7: "83d6793b69c94aca4af0d5b7076a03020119930c0de2b1399bcf62f37934ddf2",
    9: "082e2cdf9141e75aa6919c93c1a70ad58948f8c8e6f8986964a2578e567a7e07",
    42: "eb9febbf2e34f7ce8d80f503b0ebec30c1db02f4bf6ef4d018f7d9599b7f3498",
}


def recorded_call(call_id):
    rows = [json.loads(line) for line in CALLS.read_text(encoding="utf-8").splitlines()]
    admissions = [row for row in rows if row["call_id"] == call_id and row["status"] == "admitted"]
    returns = [row for row in rows if row["call_id"] == call_id and row["status"] == "returned"]
    assert len(admissions) == len(returns) == 1
    output = returns[0]["synthetic_visible_output"]
    assert hashlib.sha256(output.encode()).hexdigest() == OUTPUT_HASHES[call_id]
    return admissions[0], output


def frozen_case(case_id):
    return next(case for case in load_cases("holdout") if case["case_id"] == case_id)


def test_recorded_call7_normal_with_risks_is_invalid_safety_contract():
    admission, output = recorded_call(7)
    assert (admission["case_id"], admission["arm"], admission["stage"]) == (
        "ica-v1-em-ho-exam",
        "event",
        "safety",
    )
    visible = json.loads(output)
    assert visible["decision"] == "normal" and visible["risks"]
    assert visible["risks"][0]["user_role"] == "unclear"
    with pytest.raises(ValidationError, match="risk decision mismatch"):
        ChunkSafety.model_validate_json(output)


def test_recorded_call9_exact_quote_with_out_of_bounds_end_is_rejected():
    admission, output = recorded_call(9)
    assert (admission["case_id"], admission["arm"], admission["stage"]) == (
        "ica-v1-em-ho-exam",
        "baseline",
        "interaction",
    )
    parsed = ChunkInteractions.model_validate_json(output)
    ref = parsed.candidates[0].facts[0].evidence[0]
    assert ref.evidence_id == "w0-m00001"
    context = case_to_contexts(frozen_case(admission["case_id"]))[0]
    message = context.messages[0]
    assert message.id == UUID(frozen_case(admission["case_id"])["messages"][0]["message_id"])
    assert ref.quote == message.content
    assert ref.speaker == message.speaker
    assert ref.start == 0 and ref.end == 21 and len(message.content) == 17
    # Python slicing alone silently truncates an excessive end; source validation must not.
    assert message.content[ref.start : ref.end] == ref.quote
    with pytest.raises(ValueError):
        validate_evidence(context, message.id, ref.start, ref.end, ref.quote)


def test_recorded_call42_true_with_uncertain_is_rejected_by_actual_graph():
    admission, output = recorded_call(42)
    assert (admission["case_id"], admission["arm"], admission["stage"]) == (
        "ica-v1-rc-ho-different-topics",
        "event",
        "content_review",
    )
    parsed = ContentReview.model_validate_json(output)
    assert parsed.approved and parsed.grounded
    assert parsed.respects_boundaries and parsed.preserves_counterevidence
    assert parsed.reason_codes == ["uncertain"]

    rows = [json.loads(line) for line in CALLS.read_text(encoding="utf-8").splitlines()]
    sequence = [
        row["call_id"]
        for row in rows
        if row["status"] == "admitted"
        and row.get("case_id") == admission["case_id"]
        and row.get("arm") == admission["arm"]
    ]
    returned = {
        row["call_id"]: row["synthetic_visible_output"]
        for row in rows
        if row["status"] == "returned"
    }
    assert sequence[-1] == 42
    provider = MockLLMProvider()
    for call_id in sequence:
        provider.queue_structured(returned[call_id])
    result = asyncio.run(evaluate_case(frozen_case(admission["case_id"]), provider, "mock"))
    assert result["status"] == "failed" and result["result"] is None
    assert result["error_code"] == "content_review_rejected"
    assert len(result["calls"]) == len(sequence)
    assert all(call["status"] == "succeeded" for call in result["calls"][:-1])
    assert result["calls"][-1]["error_code"] == "content_review_rejected"
