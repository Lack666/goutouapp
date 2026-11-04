"""Structural freeze only. Reserved cases are never sent to a model here."""

import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[3] / "evals/ica/v1"


def test_frozen_case_inventory_and_source_spans():
    raw = (ROOT / "cases.jsonl").read_bytes()
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    assert hashlib.sha256(raw).hexdigest() == manifest["cases_sha256"]
    cases = [json.loads(line) for line in raw.decode().splitlines()]
    assert len(cases) == 48
    assert Counter(c["split"] for c in cases) == {"development": 16, "holdout": 32}
    assert len({c["case_id"] for c in cases}) == len({c["story_id"] for c in cases}) == 48
    expected = {
        "emotional_mismatch": (4, 6),
        "recurring_conflict": (4, 6),
        "temporal_change": (4, 6),
        "counter_missing": (2, 4),
        "safety": (0, 6),
        "privacy": (2, 4),
    }
    hashes = {c["case_id"]: c["sha256"] for c in manifest["cases"]}
    for family, counts in expected.items():
        assert (
            tuple(
                sum(c["family"] == family and c["split"] == split for c in cases)
                for split in ("development", "holdout")
            )
            == counts
        )
    for case in cases:
        canonical = json.dumps(case, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        assert hashlib.sha256(canonical.encode()).hexdigest() == hashes[case["case_id"]]
        assert case["case_id"] in manifest[case["split"]]
        assert case["expected"]["unknowns"] and case["expected"]["forbidden_assertions"]
        messages = {m["message_id"]: m for m in case["messages"]}
        assert len(messages) == len(case["messages"])
        for identity in case["source"].keys() & {
            "owner_id",
            "person_id",
            "relationship_id",
            "dataset_id",
        }:
            UUID(case["source"][identity])
        for message in messages.values():
            UUID(message["message_id"])
            stamp = datetime.fromisoformat(message["timestamp_utc"])
            assert stamp.utcoffset().total_seconds() == 0
            assert message["sender_role"] in {"self", "person", "system"}
            window = next(w for w in case["windows"] if w["window_id"] == message["window_id"])
            assert (
                datetime.fromisoformat(window["start_utc"])
                <= stamp
                < datetime.fromisoformat(window["end_utc"])
            )
        for ref in case["expected"]["support"] + case["expected"]["counterevidence"]:
            assert messages[ref["message_id"]]["content"][ref["start"] : ref["end"]] == ref["quote"]
        if case["family"] in {"emotional_mismatch", "recurring_conflict", "temporal_change"}:
            assert case["expected"]["alternative_explanations"]
    for family in ("emotional_mismatch", "recurring_conflict", "temporal_change"):
        for split, positives in (("development", 2), ("holdout", 3)):
            assert (
                sum(
                    c["family"] == family
                    and c["split"] == split
                    and c["expected"]["primary_pattern"] is not None
                    for c in cases
                )
                == positives
            )


def test_positive_temporal_cases_have_comparable_observed_windows():
    cases = [
        json.loads(line) for line in (ROOT / "cases.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    for case in cases:
        if case["family"] != "temporal_change":
            continue
        assert len(case["windows"]) == 2
        for window in case["windows"]:
            messages = [m for m in case["messages"] if m["window_id"] == window["window_id"]]
            assert len(messages) >= 10
            assert {m["sender_role"] for m in messages} == {"self", "person"}
            assert len({m["timestamp_utc"][:10] for m in messages}) >= 2
