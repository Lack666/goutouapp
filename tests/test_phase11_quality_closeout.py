"""Closeout preserves human judgments and excludes duplicated reviews from denominators."""

import copy

import pytest

from scripts.phase11_quality_closeout import build, deduplicate


def test_repeated_reviews_are_not_new_cases_and_conflicts_fail_closed():
    item = {"case_id": "synthetic", "scores": {"agency": 3}, "output_sha256": "same"}
    unique, repeats = deduplicate([item, copy.deepcopy(item)])
    assert unique == [item] and repeats == ["synthetic"]
    changed = copy.deepcopy(item)
    changed["scores"]["agency"] = 4
    with pytest.raises(AssertionError, match="Conflicting"):
        deduplicate([item, changed])


def test_actual_completed_reviews_cannot_override_failed_operational_or_safety_gates():
    result = build()
    assert result["review_counts"]["review_records"] == 30
    assert result["review_counts"]["unique_cases"] == 28
    assert result["review_counts"]["completed_answers_reviewed"] == 22
    assert result["human_summary"]["unique_all"]["acceptable"] == 8
    assert result["quality_conclusion"] == "QUALITY FAIL"
    assert result["phase_acceptance"] == "BLOCKED"
    assert result["official_marker"] == {"completed_phase": 9, "completed_subphase": "9H"}
