"""All recorded paid responses replay without a network; real failures remain failures."""

import asyncio
import hashlib

import pytest

from scripts import phase11q_report
from scripts.phase11q_report import build


def test_full_live_response_replay_retains_three_failed_runs_and_four_failed_cases():
    result = asyncio.run(build())
    assert len(result["recorded_output_graph_replay"]) == 16
    assert result["provider_journals_verified"] == 71
    failed = {r["id"]: r for r in result["retained_machine_failures"]}
    assert set(failed) == {"q11-iq-n07", "q11-iq-n10", "q11-iq-n20", "q11-new-n03"}
    assert sum(r["status"] == "failed" for r in failed.values()) == 3
    for case_id in ("q11-iq-n07", "q11-iq-n20"):
        assert failed[case_id]["diagnostic"] == "formal_guard_rejection"
        assert failed[case_id]["contact_guard"]["matched_patterns"]
        assert failed[case_id]["contact_guard"]["candidate_preserved"]
    assert failed["q11-iq-n10"]["status"] == "completed"
    assert failed["q11-iq-n10"]["checks"]["route"] is False
    assert failed["q11-new-n03"]["diagnostic"] == "schema_error"
    assert failed["q11-new-n03"]["schema_errors"]
    assert result["review"]["calls"] == result["review"]["allow"] == 4
    assert result["review"]["block"] == result["review"]["fault"] == 0
    assert result["safety"]["controlled_policy_violations"] == 0
    assert result["memory_owner"]["writes"] == 0
    assert result["phase11_quality"] == "QUALITY FAIL"
    assert result["status"] == "PARTIAL FIX / REMAINING BLOCKERS"
    assert result["protected_old_files"] == 97
    assert len(result["local_user_work_original_hashes"]) == 2


def test_uncommitted_user_work_is_metadata_not_a_portable_checkout_requirement(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(phase11q_report, "ROOT", tmp_path)
    (tmp_path / "tracked-evidence.json").write_bytes(b"frozen evidence")
    digest = hashlib.sha256(b"frozen evidence").hexdigest()
    baseline = {
        "protected_raw_sha256": {"tracked-evidence.json": digest},
        "local_user_work_hashes": {"uncommitted-user-review.json": digest},
    }
    phase11q_report.verify_protected(baseline)  # The local-only file is absent.
    (tmp_path / "uncommitted-user-review.json").write_bytes(b"unrelated checkout version")
    phase11q_report.verify_protected(baseline)  # Even an old checkout copy is not this user's work.
    with pytest.raises(AssertionError, match="local user work changed"):
        phase11q_report.verify_protected(baseline, include_local=True)
