"""Frozen expectation/evidence and current-guard replay integrity for Phase11R."""

import asyncio
import json

from evals.agent import remediation_r, semantic_replay_r


def test_r11_selection_is_contract_first_and_historical_inputs_are_exact():
    cases = remediation_r.cases()
    old = {
        row["baseline_id"]: row
        for row in (
            json.loads(line)
            for line in remediation_r.DATASET.with_name("q11-remediation.v1.jsonl")
            .read_text("utf-8")
            .splitlines()
        )
        if row.get("baseline_id")
    }
    historical = [c for c in cases if c["stratum"] == "historical_failure"]
    assert len(historical) == 3
    for row in historical:
        assert row["input"] == old[row["baseline_id"]]["input"]
        assert row["expected_route"] == old[row["baseline_id"]]["expected_route"]
    selection = json.loads(
        remediation_r.DATASET.with_name("r11-case-selection-v1.json").read_text("utf-8")
    )
    assert len(selection["sa_cases"]) == 18
    assert selection["hard_limits"]["requests"] == 80


def test_r11_guard_replay_never_relabels_original_n10_route_failure():
    result = asyncio.run(semantic_replay_r.replay())
    assert result["paid_calls"] == 0
    assert all(row["current_action_response_guards_pass"] for row in result["cases"])
    n10 = next(row for row in result["cases"] if row["id"] == "r11-offline-n10")
    assert n10["original_diagnostic"] == "business_validation_failure"
    assert n10["original_route"] == "ordinary"
    assert n10["original_route_oracle_pass"] is False
    new = result["cases"][-1]
    assert new["route"] == "boundary"
    assert "explicit_refusal" in new["safety"]["risk_categories"]
    assert "necessary_classroom" in new["safety"]["risk_categories"]
    assert new["action_plan"]["message_suggestion"] is None


def test_r11_preserves_all_preexisting_evaluation_files_and_marker():
    result = remediation_r.protected_check()
    assert result["all_unchanged"] is True
    assert result["protected_files"] == 222
