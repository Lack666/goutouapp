"""Independent evaluation accounting must not confuse schema, provider or Agent success."""

from evals.agent.independent import call_metrics, diagnostic, load_cases


def call(status="completed", error=None, operation="structured_output"):
    return {
        "kind": "provider",
        "status": status,
        "error": error,
        "operation": operation,
        "usage": None,
    }


def test_independent_dataset_and_fixed_denominators():
    rows = load_cases()
    assert sum(r["group"] == "normal" for r in rows) == 20
    assert sum(r["group"] == "safety" for r in rows) == 8
    assert len({r["input"] for r in rows}) == 28
    assert sum(r.get("memory_probe", False) for r in rows) == 2


def test_provider_response_success_includes_pydantic_failure_not_network_failure():
    metrics = call_metrics(
        [
            call(),
            call("failed", "llm_invalid_structured_output"),
            call("failed", "llm_timeout"),
            call(operation="chat"),
        ]
    )
    assert metrics["provider_success_rate"] == 3 / 4
    assert metrics["pydantic_rate"] == 1 / 2
    assert metrics["pydantic_denominator"] == 2
    assert metrics["unknown_cost_calls"] == 4
    assert call_metrics([])["provider_success_rate"] is None


def test_rejection_fault_and_formal_failure_remain_distinct():
    row = {"status": "failed", "passed": False}
    assert diagnostic(row, [call("failed", "llm_timeout")]) == "provider_error"
    assert diagnostic(row, [call("failed", "llm_invalid_structured_output")]) == "schema_error"
    assert diagnostic(row, [call()]) == "formal_guard_rejection"
    review = call(operation="chat")
    assert diagnostic(row, [review]) == "review_fault"
    block = {"kind": "content_safety_review", "decision": "block"}
    assert diagnostic(row, [review, block]) == "safety_rejection"
    assert diagnostic({"status": "completed", "passed": False}, []) == "business_validation_failure"
    assert diagnostic({"status": "completed", "passed": True}, []) == "completed"


def test_frozen_live_evidence_replays_schemas_and_matches_exact_denominators():
    from scripts.phase11_independent_acceptance import audit

    rows, failures, metrics, e2e, _ = audit()
    assert len(rows) == 28 and len(failures) == 6
    assert metrics["quality_gate"] == "FAIL"
    assert e2e["budget"]["requests"] == 11


def test_new_packets_load_actual_inputs_without_prefilling_scores_or_old_progress():
    from evals.agent.independent import RESULTS
    from scripts.human_review_ui import ReviewStore

    primary = ReviewStore(packet_path=RESULTS / "independent-human-review-15-v1.json")
    safety = ReviewStore(packet_path=RESULTS / "independent-safety-review-15-v1.json")
    assert primary.progress != safety.progress
    assert primary.public()["items"][0]["case_id"] == "iq-n01"
    assert primary.public()["items"][0]["question"] == load_cases()[0]["input"]
    assert {item["case_id"] for item in safety.public()["items"]} >= {
        f"iq-s{i:02}" for i in range(1, 9)
    }
