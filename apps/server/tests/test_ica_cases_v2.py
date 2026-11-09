"""Frozen v2 fixture integrity and preparation only; no Providers or v1 data reads."""

import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from unicodedata import normalize
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from app.agent.imported_quote import exact_span
from app.chat_import.analysis_scope import validate_coverage
from evals.ica.runner import case_to_contexts, load_cases

ROOT = Path(__file__).resolve().parents[3]
DIRECTORY = ROOT / "evals/ica/v2"
CASE_IDS = [f"ica-v2-d{i:02d}" for i in range(1, 17)] + [f"ica-v2-h{i:02d}" for i in range(1, 33)]
CASES_SHA256 = "15e1d48fff423456f6144bcf64cf639c13b6303af5ff4959129f955fc3b7a379"
MANIFEST_SHA256 = "3198d33120e33383e09bef30972fbeb69f8b362477450dbba478e9f16bab2ba6"


@pytest.fixture(scope="module")
def inventory():
    rows = load_cases("development", case_set="v2") + load_cases("holdout", case_set="v2")
    return {case["case_id"]: case for case in rows}


def test_v2_loader_and_exact_frozen_inventory(inventory):
    payload = (DIRECTORY / "cases.jsonl").read_bytes()
    manifest_bytes = (DIRECTORY / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    assert hashlib.sha256(payload).hexdigest() == CASES_SHA256 == manifest["cases_sha256"]
    assert hashlib.sha256(manifest_bytes).hexdigest() == MANIFEST_SHA256
    assert set(inventory) == set(CASE_IDS)
    assert set(manifest["development"]) == {f"ica-v2-d{i:02d}" for i in range(1, 17)}
    assert set(manifest["holdout"]) == {f"ica-v2-h{i:02d}" for i in range(1, 33)}
    assert set(manifest["ordinary_holdout"]) == {f"ica-v2-h{i:02d}" for i in range(1, 23)}
    assert set(manifest["safety_holdout"]) == {f"ica-v2-h{i:02d}" for i in range(23, 29)}
    assert set(manifest["adversarial_holdout"]) == {f"ica-v2-h{i:02d}" for i in range(29, 33)}
    assert Counter(case["split"] for case in inventory.values()) == {
        "development": 16,
        "holdout": 32,
    }
    holdout = [case for case in inventory.values() if case["split"] == "holdout"]
    assert Counter(case["family"] for case in holdout) == {
        "emotional_mismatch": 6,
        "recurring_conflict": 6,
        "temporal_change": 6,
        "counter_missing": 4,
        "safety_role": 6,
        "adversarial": 4,
    }
    for kind in ("emotional_mismatch", "recurring_conflict", "temporal_change"):
        cases = [case for case in holdout if case["family"] == kind]
        assert sum(case["expected"]["primary_pattern"] == {"kind": kind} for case in cases) == 3
        assert sum(case["expected"]["primary_pattern"] is None for case in cases) == 3
    assert manifest["case_schema_version"] == "ica-case-v1"
    assert manifest["evidence_protocol"] == "quote-v2"
    assert manifest["expected_harness_only"] is True
    assert manifest["human_semantic_review"] == "pending"
    assert manifest["paid_execution_authorized"] is False
    assert manifest["provider_calls"] == 0
    assert len(manifest["cases"]) == 48
    for entry in manifest["cases"]:
        row = inventory[entry["case_id"]]
        canonical = json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        assert hashlib.sha256(canonical.encode()).hexdigest() == entry["sha256"]
    for name, field in (
        ("author_cases.py", "authoring_script_sha256"),
        ("AUTHORING_PROVENANCE.md", "authoring_provenance_sha256"),
    ):
        assert hashlib.sha256((DIRECTORY / name).read_bytes()).hexdigest() == manifest[field]


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_v2_uuid_scope_window_and_exact_core_partition(case_id, inventory):
    case = inventory[case_id]
    source = {key: UUID(value) for key, value in case["source"].items()}
    contexts = case_to_contexts(case)
    assert 1 <= len(contexts) <= 2
    assert 1 <= len(case["question"]) <= 2000
    assert case["synthetic"] is True
    assert case["expected"]["harness_only"] is True
    if case["split"] == "holdout":
        assert 2 <= len(case["messages"]) <= 40
    for index, context in enumerate(contexts):
        validate_coverage(context)
        assert context.scope.owner_id == source["owner_id"]
        assert context.scope.person_id == source["person_id"]
        assert context.scope.dataset_id == source["dataset_id"]
        assert context.scope.timezone == case["timezone"]
        ZoneInfo(context.scope.timezone)
        window = case["windows"][index]
        assert window["window_id"] == f"w{index}"
        assert context.scope.start == datetime.fromisoformat(window["start_utc"])
        assert context.scope.end == datetime.fromisoformat(window["end_utc"])
        expected_ids = {
            UUID(message["message_id"])
            for message in case["messages"]
            if message["window_id"] == window["window_id"]
        }
        core = [message_id for chunk in context.chunks for message_id in chunk.core]
        assert len(core) == len(set(core)) == len(expected_ids)
        assert set(core) == expected_ids
        for message in context.messages:
            assert (message.owner_id, message.person_id, message.dataset_id) == (
                source["owner_id"],
                source["person_id"],
                source["dataset_id"],
            )
            assert message.timestamp.tzinfo is not None
            assert context.scope.start <= message.timestamp < context.scope.end
        for chunk in context.chunks:
            assert 1 <= len(chunk.core) <= 200
            assert set(chunk.halo_before + chunk.halo_after) <= expected_ids
            assert not set(chunk.core) & set(chunk.halo_before + chunk.halo_after)
    if len(contexts) == 2:
        assert contexts[0].scope.end <= contexts[1].scope.start


def test_v2_case_story_and_message_identifiers_do_not_cross_stories(inventory):
    stories = [case["story_id"] for case in inventory.values()]
    message_ids = [m["message_id"] for case in inventory.values() for m in case["messages"]]
    assert len(stories) == len(set(stories)) == 48
    assert len(message_ids) == len(set(message_ids))
    for field in ("owner_id", "person_id", "dataset_id", "relationship_id"):
        assert len({case["source"][field] for case in inventory.values()}) == 48
    assert len(inventory["ica-v2-d14"]["question"]) == 2000


def test_v2_all_93_oracle_anchors_resolve_unique_canonical_unicode_spans(inventory):
    checked = 0
    for case in inventory.values():
        messages = {message["message_id"]: message for message in case["messages"]}
        expected = case["expected"]
        assert expected["harness_only"] is True
        assert expected["human_semantic_review"] == "pending"
        for reference in expected["support"] + expected["counterevidence"]:
            message = messages[reference["message_id"]]
            text = message["content"]
            start, end = exact_span(text, reference["quote"])
            assert (start, end) == (reference["start"], reference["end"])
            assert text[start:end] == reference["quote"]
            assert 1 <= len(reference["quote"]) <= 160
            assert reference["speaker"] == message["sender_role"]
            checked += 1
    assert checked == 93


@pytest.mark.parametrize(
    "case_id,ambiguous", [("ica-v2-d04", "先等等"), ("ica-v2-h03", "我想静静")]
)
def test_v2_unicode_is_not_normalized_and_repeated_short_quotes_require_context(
    case_id, ambiguous, inventory
):
    case = inventory[case_id]
    text = case["messages"][0]["content"]
    assert normalize("NFC", text) != text
    assert "\u0301" in text
    with pytest.raises(ValueError, match="quote_ambiguous"):
        exact_span(text, ambiguous)
    reference = case["expected"]["support"][0]
    assert exact_span(text, reference["quote"]) == (reference["start"], reference["end"])
    decomposed = "cafe\u0301" if case_id == "ica-v2-d04" else "Cafe\u0301"
    exact_span(text, decomposed)
    with pytest.raises(ValueError, match="quote_not_found"):
        exact_span(text, normalize("NFC", decomposed))
    if case_id == "ica-v2-d04":
        assert "\u200d" in text
        assert len(text[: reference["start"]].encode("utf-16-le")) // 2 > reference["start"]


def test_v2_recurring_positive_anchors_have_two_sided_episodes_separated_by_24_hours(inventory):
    positives = [
        case
        for case in inventory.values()
        if case["expected"]["primary_pattern"] == {"kind": "recurring_conflict"}
    ]
    assert len(positives) == 5
    for case in positives:
        by_id = {message["message_id"]: message for message in case["messages"]}
        support_ids = {ref["message_id"] for ref in case["expected"]["support"]}
        ordered = sorted(
            (by_id[message_id] for message_id in support_ids),
            key=lambda message: datetime.fromisoformat(message["timestamp_utc"]),
        )
        episodes = []
        for message in ordered:
            at = datetime.fromisoformat(message["timestamp_utc"])
            if not episodes or at - episodes[-1][-1][0] > timedelta(minutes=30):
                episodes.append([])
            episodes[-1].append((at, message["sender_role"]))
        both = [
            episode for episode in episodes if {row[1] for row in episode} == {"self", "person"}
        ]
        assert any(
            later[0][0] - earlier[-1][0] >= timedelta(hours=24)
            for earlier in both
            for later in both
        ), case["case_id"]


def test_v2_temporal_positive_anchors_are_within_comparable_nonoverlapping_windows(inventory):
    positives = [
        case
        for case in inventory.values()
        if case["expected"]["primary_pattern"] == {"kind": "temporal_change"}
    ]
    assert len(positives) == 4
    for case in positives:
        contexts = case_to_contexts(case)
        assert len(contexts) == 2
        assert contexts[0].scope.end <= contexts[1].scope.start
        zone = ZoneInfo(case["timezone"])
        lengths = []
        supported_windows = {
            message["window_id"]
            for message in case["messages"]
            if message["message_id"] in {r["message_id"] for r in case["expected"]["support"]}
        }
        assert supported_windows == {"w0", "w1"}
        for context in contexts:
            texts = [
                m for m in context.messages if m.content_type == "text" and m.speaker != "system"
            ]
            counts = Counter(message.speaker for message in texts)
            assert len(texts) >= 10
            assert min(counts["self"], counts["person"]) >= 2
            assert len({message.timestamp.astimezone(zone).date() for message in texts}) >= 2
            assert len(texts) / len(context.messages) >= 0.8
            lengths.append(
                (context.scope.end - timedelta(microseconds=1)).astimezone(zone).date()
                - context.scope.start.astimezone(zone).date()
            )
        assert lengths[0] == lengths[1]


def test_v2_dst_and_cross_midnight_fixture_conditions_are_real(inventory):
    contexts = case_to_contexts(inventory["ica-v2-h15"])
    assert [context.scope.end - context.scope.start for context in contexts] == [
        timedelta(hours=72),
        timedelta(hours=73),
    ]
    for case_id in ("ica-v2-d06", "ica-v2-h10"):
        case = inventory[case_id]
        context = case_to_contexts(case)[0]
        zone = ZoneInfo(case["timezone"])
        assert len({message.timestamp.astimezone(zone).date() for message in context.messages}) == 2
        assert context.messages[-1].timestamp - context.messages[0].timestamp < timedelta(hours=24)
        assert case["expected"]["primary_pattern"] is None


@pytest.mark.parametrize("case_id,count,chunks", [("ica-v2-d15", 900, 5), ("ica-v2-d16", 2100, 11)])
def test_v2_large_engineering_cases_cover_all_core_and_exercise_halos(
    case_id, count, chunks, inventory
):
    case = inventory[case_id]
    context = case_to_contexts(case)[0]
    assert case["split"] == "development"
    assert "engineering_only" in case["tags"]
    assert len(context.messages) == count
    assert len(context.chunks) == chunks
    assert sum(chunk.continuation for chunk in context.chunks) == chunks - 1
    assert all(chunk.halo_before or chunk.halo_after for chunk in context.chunks)
    if case_id == "ica-v2-d15":
        repair_id = UUID(case["expected"]["counterevidence"][0]["message_id"])
        assert repair_id in context.chunks[0].halo_after
        assert repair_id in context.chunks[1].core
        assert sum(repair_id in chunk.core for chunk in context.chunks) == 1
    else:
        refusal_id = UUID(case["expected"]["support"][0]["message_id"])
        assert refusal_id in context.chunks[-1].core


def test_v2_case_to_contexts_does_not_consume_harness_oracles(inventory):
    fields = {"schema_version", "source", "timezone", "windows", "messages"}
    for case in inventory.values():
        selected_input = {key: value for key, value in case.items() if key in fields}
        assert case_to_contexts(selected_input) == case_to_contexts(case)
