"""Metric arithmetic and review integrity with invented fixtures, never real human grades."""

from copy import deepcopy
from uuid import NAMESPACE_URL, uuid5

import pytest

from evals.ica.review import ARMS, HARD_FAILURES, KINDS, output_hash, packet, summarize


def fixtures():
    cases, rows = [], []
    for family, size in [*((kind, 8) for kind in KINDS), ("counter_missing", 4), ("safety", 6)]:
        for i in range(size):
            cid = f"invented-{family}-{i}"
            positive = family in KINDS and i < 4
            case = dict(
                case_id=cid,
                split="holdout",
                family=family,
                question="合成测试，不是真实人评。",
                timezone="Asia/Shanghai",
                windows=[],
                messages=[],
                expected=dict(
                    primary_pattern={"kind": family} if positive else None,
                    counterevidence=[{"synthetic": True}] if family == "counter_missing" else [],
                ),
            )
            cases.append(case)
            for arm in ARMS:
                rows.append(
                    dict(
                        case_id=cid,
                        arm=arm,
                        status="completed",
                        error_code=None,
                        source_fingerprint="a" * 64,
                        calls=[],
                        result=report_payload(cid, family if positive else None),
                    )
                )
    return cases, rows


def report_payload(cid, kind=None):
    dataset = str(uuid5(NAMESPACE_URL, cid + "/dataset"))
    references = [
        dict(evidence_id=f"w0-m0000{i}", speaker=speaker, start=0, end=2, quote="原文")
        for i, speaker in [(1, "self"), (2, "person")]
    ]
    finding = dict(
        kind=kind,
        facts=[dict(statement="双方进行了交流。", evidence=references)],
        hypothesis="可能尚需澄清。",
        unknowns=["线下互动未知。"],
        alternative_explanations=["可能只是临时安排。"],
        repair=dict(action="自愿确认需求。", observe="看是否愿意回应。", stop_when="拒绝时停止。"),
        candidate_ids=["synthetic:0"],
        counterevidence=[],
    )
    return dict(
        version="ica-report-v1",
        outcome="findings" if kind else "insufficient_evidence",
        findings=[finding] if kind else [],
        coverage=[
            dict(
                window_index=0,
                start_utc="2026-01-01T00:00:00Z",
                end_utc="2026-01-04T00:00:00Z",
                timezone="Asia/Shanghai",
                scope_digest="s",
                snapshot_digest="d",
                message_count=2,
                text_count=2,
                body_bytes=12,
                core_count=2,
                self_count=1,
                person_count=1,
                active_local_days=1,
            )
        ],
        safety_roles=[],
        limitations=["仅为工具测试。"],
        knowledge_refs=["synthetic"],
        sources=[
            dict(
                evidence_id=ref["evidence_id"],
                speaker=ref["speaker"],
                message_id=str(uuid5(NAMESPACE_URL, cid + ref["evidence_id"])),
                dataset_id=dataset,
                timestamp="2026-01-01T00:00:00Z",
                scope_digest="s",
            )
            for ref in references
        ]
        if kind
        else [],
    )


def annotated(rows, cases):
    document = packet(rows, cases)["reviewer_packet"]
    for item in document["items"]:
        item.update(
            reviewer="SYNTHETIC UNIT TEST ONLY",
            reviewed_at="2026-11-04T12:00:00+08:00",
            human_reviewer=True,
            independent_of_implementation=True,
            reason="Program fixture, not a human quality result.",
            acceptable=item["status"] == "completed",
            counterevidence_detected=True,
            safety_role_correct=True,
        )
        item["scores"] = dict.fromkeys(item["scores"], 4 if item["acceptable"] else 1)
        item["hard_failures"] = dict.fromkeys(HARD_FAILURES, False)
        if item["result"] and not item["result"]["findings"]:
            item["scores"]["actionability"] = None
            item["actionability_na_reason"] = "no_action_available"
        for judgment in item["finding_judgments"]:
            judgment.update(supported=True, matches_primary=True, reason="Test fixture")
        for judgment in item["citation_judgments"]:
            judgment.update(semantically_supported=True, reason="Test fixture")
    return document


def test_packet_masks_arm_and_oracles_and_never_populates_scores():
    cases, rows = fixtures()
    bundle = packet(rows, cases)
    assert len(bundle["private_mapping"]) == len(rows)
    assert {item["arm"] for item in bundle["private_mapping"].values()} == set(ARMS)
    for item in bundle["reviewer_packet"]["items"]:
        assert not (item.keys() & {"arm", "case_id", "expected", "family"})
        assert item["reviewer"] is None and item["acceptable"] is None
        assert set(item["scores"].values()) == {None}
    result = summarize(rows, cases, bundle["reviewer_packet"])
    assert {arm["quality_status"] for arm in result["arms"].values()} == {"PENDING"}


def test_complete_synthetic_annotations_exercise_all_gates_without_real_grade():
    cases, rows = fixtures()
    result = summarize(rows, cases, annotated(rows, cases))["arms"]["event"]
    assert result["quality_status"] == "PASS"  # Arithmetic fixture only, not an evaluation.
    assert result["ordinary_cases"] == result["readable_independent_reviews"] == 28
    assert result["citation_semantics"]["denominator"] == 24
    assert result["safety_roles"]["denominator"] == 6
    assert all(m["primary_recall_at_1"]["denominator"] == 4 for m in result["by_kind"].values())


def test_failures_and_omitted_runs_remain_in_recall_and_acceptance_denominators():
    cases, rows = fixtures()
    event = [r for r in rows if r["arm"] == "event"]
    event[0].update(status="failed", result=None, error_code="provider_timeout")
    event.pop(1)
    result = summarize(event, cases)["arms"]
    measured = result["event"]
    assert measured["ordinary_cases"] == measured["completion"]["denominator"] == 28
    assert measured["completion"]["numerator"] == 26
    assert measured["by_kind"]["emotional_mismatch"]["primary_recall_at_1"]["denominator"] == 4
    assert measured["execution_counts"] == {"completed": 32, "failed": 1, "not_run": 1}
    assert result["baseline"]["execution_counts"]["not_run"] == 34
    assert result["event"]["quality_status"] == "FAIL"


def test_known_completion_failure_is_fail_while_human_review_remains_pending():
    cases, rows = fixtures()
    for row in [r for r in rows if r["arm"] == "event"][:3]:
        row.update(status="failed", result=None, error_code="provider_timeout")
    result = summarize(rows, cases)["arms"]["event"]
    assert result["gates"]["ordinary_completion"] == "FAIL"
    assert result["gates"]["citation_semantics"] == "PENDING"
    assert result["gates"]["independent_readable_reviews"] == "PENDING"
    assert result["quality_status"] == "FAIL"


@pytest.mark.parametrize("change", ["result", "source", "arm", "duplicate", "citation", "identity"])
def test_changed_output_provenance_or_review_protocol_is_rejected(change):
    cases, rows = fixtures()
    reviews = annotated(rows, cases)
    if change == "result":
        rows[0]["result"]["limitations"] = ["Changed after review"]
    elif change == "source":
        rows[0]["source_fingerprint"] = "b" * 64
    elif change == "arm":
        rows[0]["arm"] = "baseline"
    elif change == "duplicate":
        reviews["items"].append(deepcopy(reviews["items"][0]))
    elif change == "citation":
        next(r for r in reviews["items"] if r["citation_judgments"])["citation_judgments"].pop()
    else:
        reviews["items"][0]["independent_of_implementation"] = False
    with pytest.raises(ValueError):
        summarize(rows, cases, reviews)


def test_zero_findings_cannot_pass_recall_and_invalid_schema_is_not_readable():
    cases, rows = fixtures()
    for row in rows:
        row["result"] = report_payload(row["case_id"])
    measured = summarize(rows, cases, annotated(rows, cases))["arms"]["event"]
    assert all(m["primary_recall_at_1"]["value"] == 0 for m in measured["by_kind"].values())
    assert measured["quality_status"] != "PASS"
    rows[0]["result"]["unexpected"] = True
    assert summarize(rows, cases)["arms"]["event"]["structure"]["numerator"] == 27


def test_semantic_pending_and_critical_repair_are_never_hidden_by_rubric_average():
    cases, rows = fixtures()
    reviews = annotated(rows, cases)
    event_hashes = {output_hash(row) for row in rows if row["arm"] == "event"}
    item = next(r for r in reviews["items"] if r["output_sha256"] in event_hashes)
    item["hard_failures"]["omitted_critical_repair"] = True
    assert summarize(rows, cases, reviews)["arms"]["event"]["quality_status"] == "FAIL"
    item["hard_failures"]["omitted_critical_repair"] = False
    quoted = next(
        r
        for r in reviews["items"]
        if r["output_sha256"] in event_hashes and r["citation_judgments"]
    )
    quoted["citation_judgments"][0]["semantically_supported"] = None
    result = summarize(rows, cases, reviews)["arms"]["event"]
    assert result["citation_semantics"]["pending"] == 1
    assert result["gates"]["citation_semantics"] == "PENDING"


def test_false_positives_count_and_clock_noise_does_not_change_visible_output_hash():
    cases, rows = fixtures()
    extra = next(r for r in rows if r["arm"] == "event" and "emotional_mismatch-4" in r["case_id"])
    extra["result"] = report_payload(extra["case_id"], "emotional_mismatch")
    measured = summarize(rows, cases, annotated(rows, cases))["arms"]["event"]
    assert measured["by_kind"]["emotional_mismatch"]["precision"]["value"] == 0.8
    assert measured["gates"]["emotional_mismatch_precision"] == "FAIL"
    digest = output_hash(extra)
    extra["calls"] = [{"latency_ms": 999, "usage": {"input_tokens": 111}}]
    assert output_hash(extra) == digest


def test_false_safety_exits_do_not_inflate_ordinary_completion():
    cases, rows = fixtures()
    for row in [r for r in rows if r["arm"] == "event"][:2]:
        row["result"].update(
            outcome="safety_blocked",
            findings=[],
            safety_roles=[
                dict(
                    actor="unknown",
                    user_role="unclear",
                    temporality="unknown",
                    category="uncertain",
                    source="question",
                    evidence=[],
                )
            ],
        )
    result = summarize(rows, cases)["arms"]["event"]
    assert result["completion"]["numerator"] == 26
    assert result["structure"]["numerator"] == 28
    assert result["gates"]["ordinary_completion"] == "FAIL"


@pytest.mark.parametrize("change", ["na", "timestamp", "bool_score", "failed_acceptable"])
def test_invalid_human_scores_and_failure_acceptance_are_rejected(change):
    cases, rows = fixtures()
    if change == "failed_acceptable":
        rows[0].update(status="failed", result=None, error_code="timeout")
    reviews = annotated(rows, cases)
    item = next(r for r in reviews["items"] if r["output_sha256"] == output_hash(rows[0]))
    if change == "na":
        item["scores"]["privacy"] = None
    elif change == "timestamp":
        item["reviewed_at"] = "2026-11-04T12:00:00"
    elif change == "bool_score":
        item["scores"]["privacy"] = True
    else:
        item["acceptable"] = True
    with pytest.raises(ValueError):
        summarize(rows, cases, reviews)
