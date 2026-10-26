"""Only temporary copies receive fixture scores; real human review evidence stays untouched."""

import copy
import hashlib
import importlib.util
import json
import re
import shutil
import threading
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "human_review_ui", ROOT / "scripts/human_review_ui.py"
)
ui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui)


@pytest.fixture
def store(tmp_path):
    for name in [
        "human-review-15.json",
        "final-live-safety.json",
        "final-live-communication.json",
        "final-live-grounding.json",
    ]:
        target = tmp_path / "evals/agent/results" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "evals/agent/results" / name, target)
    packet = tmp_path / "evals/agent/results/human-review-15.json"
    document = ui.read_json(packet)
    for item in document["items"]:
        item.update(
            scores=dict.fromkeys(ui.DIMENSIONS), reviewer=None, reviewed_at=None, reason=None
        )
    ui.atomic_write(packet, ui.encoded(document))
    shutil.copyfile(ROOT / "evals/agent/cases.v1.jsonl", tmp_path / "evals/agent/cases.v1.jsonl")
    return ui.ReviewStore(tmp_path)


def payload(store, index=0, submit=False):
    item = store.public()["items"][index]
    return {
        "revision": store.state["revision"],
        "case_id": item["case_id"],
        "reviewer": "SYNTHETIC TEST ONLY",
        "scores": dict.fromkeys(ui.DIMENSIONS, None),
        "reason": "",
        "submit": submit,
        "position": index,
    }


def test_actual_questions_visible_outputs_and_no_proxy_autofill(store):
    view = store.public()
    assert len(view["items"]) == 15
    assert view["completed"] == 0 and view["reviewer"] == ""
    for item in view["items"]:
        assert item["question"] == store.questions[item["case_id"]]
        assert all(v is None for v in item["draft"]["scores"].values())
        assert "automated_proxy" not in item
        row = store.rows[item["case_id"]]
        assert item["status"] == row["result"]["status"]
        if item["status"] == "failed":
            assert item["answer"] is None and item["error_code"] == "structured_output_failure"
        else:
            assert item["answer"] == row["result"]["final_answer"]


def test_partial_progress_restart_edit_and_server_timestamp(store):
    original = store.packet_path.read_bytes()
    request = payload(store)
    request["scores"]["relevance"] = 2
    store.save(request)
    restored = ui.ReviewStore(store.root)
    assert restored.public()["items"][0]["draft"]["scores"]["relevance"] == 2
    assert restored.packet_path.read_bytes() == original
    with pytest.raises(ValueError, match="全部 15"):
        restored.finish(restored.state["revision"])
    request = payload(restored, submit=True)
    request.update(
        scores=dict.fromkeys(ui.DIMENSIONS, 3), reason="Synthetic fixture, not real review"
    )
    restored.save(request)
    draft = restored.public()["items"][0]["draft"]
    assert draft["reviewer"] == "SYNTHETIC TEST ONLY"
    assert datetime.fromisoformat(draft["reviewed_at"]).tzinfo is not None
    request = payload(restored)
    request.update(scores=dict.fromkeys(ui.DIMENSIONS, 4), reason="Synthetic edited fixture")
    restored.save(request)
    assert restored.public()["items"][0]["draft"]["submitted"] is False


def test_validation_conflicts_and_no_unsubmitted_export(store):
    request = payload(store, submit=True)
    with pytest.raises(ValueError):
        store.save(request)
    request["scores"] = dict.fromkeys(ui.DIMENSIONS, True)
    with pytest.raises(ValueError):
        store.save(request)
    request = payload(store)
    store.save(request)
    with pytest.raises(ValueError, match="另一个窗口"):
        store.save(request)
    with pytest.raises(ValueError):
        store.finish(store.state["revision"])


def test_all_fifteen_exports_preserve_evidence_and_allow_revisions(store):
    before = copy.deepcopy(store.state["baseline"])
    for i in range(15):
        request = payload(store, i, submit=True)
        request.update(scores=dict.fromkeys(ui.DIMENSIONS, 4), reason="Synthetic test fixture only")
        store.save(request)
    result = store.finish(store.state["revision"])
    assert result["completed"] == 15
    document = ui.read_json(store.packet_path)
    expected = copy.deepcopy(before)
    for old, new in zip(expected["items"], document["items"], strict=True):
        for key in ("scores", "reviewer", "reviewed_at", "reason"):
            old[key] = new[key]
    assert expected == document
    assert ui.read_json(store.progress.with_name("original-human-review-15.json")) == before
    assert "15/15" in store.report_path.read_text(encoding="utf-8")
    resumed = ui.ReviewStore(store.root)
    assert resumed.public()["completed"] == 15
    request = payload(resumed, 0, submit=True)
    request.update(scores=dict.fromkeys(ui.DIMENSIONS, 2), reason="Synthetic correction")
    resumed.save(request)
    resumed.finish(resumed.state["revision"])
    assert ui.read_json(resumed.packet_path)["items"][0]["scores"]["relevance"] == 2


def test_external_packet_change_is_not_overwritten(store):
    document = ui.read_json(store.packet_path)
    document["items"][0]["result"]["final_answer"] = "tampered"
    ui.atomic_write(store.packet_path, ui.encoded(document))
    with pytest.raises(ValueError, match="frozen"):
        ui.ReviewStore(store.root)


def test_loopback_http_and_csrf(store):
    server = ui.make_server(store, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url) as response:
            html = response.read().decode()
            assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
        token = re.search(r'const token="([^"]+)"', html)[1]
        request = urllib.request.Request(
            url + "/api/save",
            data=ui.encoded(payload(store)),
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(urllib.error.HTTPError) as caught:
            opener.open(request)
        assert caught.value.code == 403
        request.add_header("X-Review-Token", token)
        with opener.open(request) as response:
            assert json.load(response)["completed"] == 0
        request.add_header("Origin", "http://external.invalid")
        with pytest.raises(urllib.error.HTTPError) as caught:
            opener.open(request)
        assert caught.value.code == 403
    finally:
        server.shutdown()
        server.server_close()


def test_real_packet_is_not_modified_by_fixture_scoring(store):
    path = ROOT / "evals/agent/results/human-review-15.json"
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    store.save(payload(store))
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
