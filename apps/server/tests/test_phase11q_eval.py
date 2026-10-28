"""Phase11Q denominators, old evidence preservation and no paid retry claims."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from evals.agent import remediation_q as q


def test_fixed_cases_keep_every_old_failure_and_unseen_controls_separate():
    rows = q.cases()
    assert len(rows) == 16
    assert sum(r["group"] == "normal" for r in rows) == 11
    assert sum(r["group"] == "safety" for r in rows) == 5
    assert sum(r["stratum"] == "new_control" for r in rows) == 7
    assert q.LIMITS["requests"] == 100 and q.LIMITS["cost_cny"] == 10


def test_historical_archive_is_checked_without_requiring_old_source_as_current():
    result = q.historical_archive_audit()
    assert result["original_source_files"] > 50
    assert len(result["archive_sha256"]) == 64


def test_historical_audit_does_not_silently_disable_current_source_guard(monkeypatch):
    from scripts import phase11_independent_acceptance as acceptance

    def source_mismatch():
        raise AssertionError("authorized remediation changed source")

    monkeypatch.setattr(acceptance, "check_frozen", source_mismatch)
    with pytest.raises(AssertionError, match="changed source"):
        acceptance.audit()
    rows, failures, _, _, _ = acceptance.audit(require_current_source=False)
    assert len(rows) == 28 and len(failures) == 6


def test_claim_prevents_retry_even_when_no_completed_summary_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(q, "RESULTS", tmp_path)
    monkeypatch.setattr(q, "CLAIM", tmp_path / "q11-live-v1.claim.json")
    monkeypatch.setattr(q, "OUTPUT", tmp_path / "q11-live-v1.json")
    q.guard_new_execution()
    q.CLAIM.write_text(json.dumps({"interrupted": True}), encoding="utf-8")
    with pytest.raises(ValueError, match="no paid retry"):
        q.guard_new_execution()


def test_checkpoint_prevents_duplicate_paid_case_under_different_summary_name(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(q, "RESULTS", tmp_path)
    monkeypatch.setattr(q, "CLAIM", tmp_path / "absent-claim.json")
    monkeypatch.setattr(q, "OUTPUT", tmp_path / "new-output.json")
    (tmp_path / "q11-case-old-id-v1.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="no paid retry"):
        q.guard_new_execution()


def test_call_journal_keeps_response_usage_before_formal_validation(tmp_path, monkeypatch):
    monkeypatch.setattr(q, "RESULTS", tmp_path)
    budget = SimpleNamespace(requests=0)

    class Provider:
        async def _chat_request(self):
            budget.requests += 1
            return SimpleNamespace(
                model_dump=lambda **_: {
                    "content": '{"extra_business_field": "must still fail schema"}',
                    "usage": {"input_tokens": 20, "output_tokens": 10},
                }
            )

    provider = Provider()
    q.attach_call_journal(provider, budget)
    provider.q11_case = "synthetic-only"
    asyncio.run(provider._chat_request())
    saved = json.loads((tmp_path / "q11-call-001-v1.json").read_text("utf-8"))
    assert saved["request_reserved"] and saved["status"] == "response"
    assert saved["visible_response"]["usage"]["input_tokens"] == 20
    assert "extra_business_field" in saved["visible_response"]["content"]
