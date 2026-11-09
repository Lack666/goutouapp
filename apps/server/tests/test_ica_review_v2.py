"""Readable review handoff and integrity tests; invented ratings are arithmetic fixtures only."""

import hashlib
import json
import sys
from copy import deepcopy
from uuid import NAMESPACE_URL, uuid5

import pytest
from test_ica_review import annotated, fixtures, report_payload

from evals.ica.review import export_review, main, output_hash, packet, readable, summarize


def small_inventory():
    cid = "WITHHELD_CASE_IDENTIFIER"
    messages = [
        {
            "message_id": str(uuid5(NAMESPACE_URL, cid + f"w0-m0000{index}")),
            "window_id": "w0",
            "timestamp_utc": f"2026-01-01T00:00:0{index - 1}+00:00",
            "sender_role": speaker,
            "content": "原文\n```\n<script>untrusted</script>",
            "content_type": "text",
        }
        for index, speaker in ((1, "self"), (2, "person"))
    ]
    case = {
        "schema_version": "ica-case-v1",
        "case_id": cid,
        "split": "holdout",
        "family": "emotional_mismatch",
        "question": "匿名合成复盘。",
        "timezone": "Asia/Shanghai",
        "source": {
            name: str(uuid5(NAMESPACE_URL, cid + "/" + name.removesuffix("_id")))
            for name in ("owner_id", "person_id", "dataset_id")
        },
        "windows": [
            {
                "window_id": "w0",
                "start_utc": "2026-01-01T00:00:00+00:00",
                "end_utc": "2026-01-04T00:00:00+00:00",
            }
        ],
        "messages": messages,
        "expected": {
            "primary_pattern": {"kind": "emotional_mismatch"},
            "secret_oracle": "PRIVATE_ORACLE_DO_NOT_DISCLOSE",
        },
    }
    rows = [
        {
            "case_id": cid,
            "arm": arm,
            "status": "completed",
            "error_code": None,
            "source_fingerprint": "a" * 64,
            "batch_plan_sha256": "b" * 64,
            "result": report_payload(cid, "emotional_mismatch"),
        }
        for arm in ("event", "baseline")
    ]
    return [case], rows


def test_legacy_hash_is_unchanged_and_new_plan_is_bound():
    cases, rows = small_inventory()
    row = rows[0]
    row.pop("batch_plan_sha256")
    original = {
        k: row.get(k)
        for k in ("case_id", "arm", "status", "result", "error_code", "source_fingerprint")
    }
    expected = hashlib.sha256(
        json.dumps(original, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert output_hash(row) == expected
    row["batch_plan_sha256"] = "b" * 64
    changed = output_hash(row)
    assert changed != expected
    row["batch_plan_sha256"] = "c" * 64
    assert output_hash(row) != changed
    reviews = packet(rows, cases)["reviewer_packet"]
    row["batch_plan_sha256"] = "d" * 64
    with pytest.raises(ValueError):
        summarize(rows, cases, reviews)


@pytest.mark.parametrize("field", ["input", "result", "status", "error_code"])
def test_displayed_source_or_output_tampering_is_rejected_before_any_review(field):
    cases, rows = small_inventory()
    document = packet(rows, cases)["reviewer_packet"]
    item = document["items"][0]
    if field == "input":
        item[field]["question"] = "Changed displayed source, unchanged output hash"
    elif field == "result":
        item[field]["limitations"] = ["Changed visible report"]
    else:
        item[field] = "changed"
    assert item["reviewer"] is None
    with pytest.raises(ValueError, match="Displayed input/output"):
        summarize(rows, cases, document)


@pytest.mark.parametrize(
    "change", ["missing", "extra_item", "extra_field", "extra_dimension", "nonce"]
)
def test_missing_or_extra_packet_items_and_protocol_fields_reject(change):
    cases, rows = small_inventory()
    document = packet(rows, cases)["reviewer_packet"]
    if change == "missing":
        document["items"].pop()
    elif change == "extra_item":
        document["items"].append(deepcopy(document["items"][0]))
    elif change == "extra_field":
        document["items"][0]["oracle"] = "untrusted"
    elif change == "extra_dimension":
        document["dimensions"]["new"] = ["unapproved"]
    else:
        document["packet_nonce"] = "invalid"
    with pytest.raises(ValueError):
        summarize(rows, cases, document)


def test_item_permutation_is_valid_and_masked_mapping_is_bijective():
    cases, rows = small_inventory()
    bundle = packet(rows, cases)
    document = bundle["reviewer_packet"]
    document["items"].reverse()
    assert len(bundle["private_mapping"]) == len(rows)
    assert {value["arm"] for value in bundle["private_mapping"].values()} == {"event", "baseline"}
    result = summarize(rows, cases, document)
    assert all(arm["readable_independent_reviews"] == 0 for arm in result["arms"].values())
    view = readable(document, cases, rows)
    assert "WITHHELD_CASE_IDENTIFIER" not in view
    assert "PRIVATE_ORACLE_DO_NOT_DISCLOSE" not in view
    assert "baseline" not in view


def test_known_low_dimension_fails_even_if_other_reviews_pending():
    cases, rows = fixtures()
    document = annotated(rows, cases)
    event_hashes = {output_hash(row) for row in rows if row["arm"] == "event"}
    ordinary = [
        item
        for item in document["items"]
        if item["output_sha256"] in event_hashes and item["result"]["findings"]
    ]
    ordinary[0]["scores"]["agency"] = 2
    ordinary[1]["reviewer"] = None
    result = summarize(rows, cases, document)["arms"]["event"]
    assert result["gates"]["rubric_dimensions"] == result["quality_status"] == "FAIL"


@pytest.mark.parametrize("field", ["human_reviewer", "independent_of_implementation"])
def test_human_identity_and_independence_cannot_be_omitted(field):
    cases, rows = fixtures()
    document = annotated(rows, cases)
    document["items"][0][field] = None
    with pytest.raises(ValueError, match="attestation"):
        summarize(rows, cases, document)


def test_readable_mock_bundle_is_safe_masked_and_never_fills_scores(tmp_path):
    cases, rows = small_inventory()
    destination = export_review(rows, cases, tmp_path / "demo", demonstration=True)
    view = (destination / "reviewer/reports.md").read_text(encoding="utf-8")
    assert "Mock 演示" in view and "不进行质量评分" in view
    for label in ("可观察事实与引用", "推测", "未知", "替代解释", "反证与修复迹象", "可退出的行动"):
        assert label in view
    assert "w0-m00001" in view and "<script>untrusted</script>" in view
    assert "````text\n原文\n```\n<script>untrusted</script>\n````" in view
    public = json.loads((destination / "reviewer/packet.json").read_text(encoding="utf-8"))
    private = json.loads(
        (destination / "private/adjudication-oracles.json").read_text(encoding="utf-8")
    )
    assert len(public["items"]) == len(private) == 2
    assert all(set(item["scores"].values()) == {None} for item in public["items"])
    assert all(item["reviewer"] is None and item["acceptable"] is None for item in public["items"])
    assert "PRIVATE_ORACLE_DO_NOT_DISCLOSE" in json.dumps(private)
    for path in (destination / "reviewer").iterdir():
        data = path.read_text(encoding="utf-8")
        assert (
            "WITHHELD_CASE_IDENTIFIER" not in data and "PRIVATE_ORACLE_DO_NOT_DISCLOSE" not in data
        )
    before = (destination / "reviewer/packet.json").read_bytes()
    with pytest.raises(FileExistsError):
        export_review(rows, cases, destination, demonstration=True)
    assert (destination / "reviewer/packet.json").read_bytes() == before


def write_inventory(tmp_path):
    cases, rows = small_inventory()
    development = {**cases[0], "case_id": "DEVELOPMENT_SHOULD_NOT_APPEAR", "split": "development"}
    path = tmp_path / "cases.jsonl"
    path.write_text(
        "\n".join(json.dumps(case) for case in [*cases, development]) + "\n", encoding="utf-8"
    )
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "cases_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    rows_path = tmp_path / "results.jsonl"
    rows_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    return path, rows_path


def test_cli_render_and_pending_summary_with_frozen_cases(tmp_path, monkeypatch, capsys):
    cases, rows = write_inventory(tmp_path)
    destination = tmp_path / "handoff"
    monkeypatch.setattr(
        sys,
        "argv",
        ["review", "render", str(rows), str(cases), str(destination), "--demonstration"],
    )
    main()
    assert "no human grading requested" in capsys.readouterr().out
    reviews = destination / "reviewer/packet.json"
    document = json.loads(reviews.read_text(encoding="utf-8"))
    assert len(document["items"]) == 2
    result = tmp_path / "summary.json"
    monkeypatch.setattr(
        sys, "argv", ["review", "summarize", str(rows), str(cases), str(reviews), str(result)]
    )
    main()
    measured = json.loads(result.read_text())
    assert all(arm["quality_status"] != "PASS" for arm in measured["arms"].values())
    with pytest.raises(FileExistsError):
        main()


def test_cli_rejects_changed_case_source_or_oracle(tmp_path, monkeypatch):
    cases, rows = write_inventory(tmp_path)
    cases.write_text(
        cases.read_text(encoding="utf-8").replace("PRIVATE_ORACLE", "CHANGED_ORACLE"),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys, "argv", ["review", "render", str(rows), str(cases), str(tmp_path / "new")]
    )
    with pytest.raises(ValueError, match="Frozen case inventory changed"):
        main()


def test_private_dual_window_aliases_use_runtime_global_numbering_without_editing_oracle(tmp_path):
    cases, rows = small_inventory()
    case = cases[0]
    case["windows"].append(
        {
            "window_id": "w1",
            "start_utc": "2026-01-04T00:00:00+00:00",
            "end_utc": "2026-01-07T00:00:00+00:00",
        }
    )
    second = [
        {
            **message,
            "message_id": str(uuid5(NAMESPACE_URL, f"second-window/{index}")),
            "window_id": "w1",
            "timestamp_utc": f"2026-01-05T00:00:0{index}+00:00",
        }
        for index, message in enumerate(case["messages"])
    ]
    case["messages"].extend(second)
    case["expected"]["supporting_evidence"] = [
        {
            "message_id": second[0]["message_id"],
            "evidence_id": "w1-m00001",
            "speaker": "self",
            "start": 0,
            "end": 2,
            "quote": "原文",
        }
    ]
    original_expected = deepcopy(case["expected"])
    destination = export_review(rows, cases, tmp_path / "dual-window", demonstration=True)
    private = json.loads(
        (destination / "private/adjudication-oracles.json").read_text(encoding="utf-8")
    )
    for item in private.values():
        assert item["expected"] == original_expected
        assert item["expected"]["supporting_evidence"][0]["evidence_id"] == "w1-m00001"
        assert item["current_source_aliases"][second[0]["message_id"]] == "w1-m00003"
        assert item["current_source_aliases"][second[1]["message_id"]] == "w1-m00004"
        assert "authored_evidence_id advisory" in item["source_alias_policy"]
        assert "message UUID and exact quote" in item["source_alias_policy"]
    assert case["expected"] == original_expected
