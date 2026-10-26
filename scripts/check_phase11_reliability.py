"""Verify the separate reliability evidence, without running tests or paid APIs."""

import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

from evals.agent.harness import fingerprint, summarize
from evals.agent.review import ANCHORS, output_hash, validate_reviews

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "evals/agent/results"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    report = read(RESULTS / "reliability-fix-v5-report.json")
    runs = []
    for evidence in report["runs"]:
        path = ROOT / evidence["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == evidence["sha256"]
        run = read(path)
        assert run["source_stable"]
        if run["prompt_version"].endswith("-v5"):
            assert run["source_fingerprint"] == report["source_fingerprint"]
        assert run["budget"]["requests"] <= 30
        assert (
            len([t for t in run["traces"] if t["kind"] == "provider"]) == run["budget"]["requests"]
        )
        runs.append(run)
    for version, run in zip((3, 4, 5), runs[:3], strict=True):
        digest = hashlib.sha256()
        with ZipFile(RESULTS / f"reliability-fix-v{version}-source.zip") as archive:
            for name in archive.namelist():
                digest.update(name.encode())
                digest.update(archive.read(name))
        assert digest.hexdigest() == run["source_fingerprint"]
    assert fingerprint() == report["source_fingerprint"]
    assert (
        hashlib.sha256((ROOT / report["source_archive"]["path"]).read_bytes()).hexdigest()
        == (report["source_archive"]["sha256"])
    )
    for label, selected in (
        ("all_paid_attempts_metrics", runs),
        ("current_version_metrics", [r for r in runs if r["prompt_version"].endswith("-v5")]),
    ):
        assert report[label] == summarize(
            [c for r in selected for c in r["cases"]],
            [t for r in selected for t in r["traces"] if t["kind"] == "provider"],
        )
    for evidence in read(RESULTS / "aggregate-final.json")["evidence"]:
        assert (
            hashlib.sha256((ROOT / evidence["path"]).read_bytes()).hexdigest() == evidence["sha256"]
        )
    review = read(RESULTS / "reliability-fix-v5-human-review-15.json")
    rows = {}
    for source in review["sources"]:
        path = ROOT / source["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]
        rows.update({c["id"]: c for c in read(path)["cases"]})
    assert len(review["items"]) == 15 and review["dimensions"] == ANCHORS
    for item in review["items"]:
        assert item["output_sha256"] == output_hash(rows[item["case_id"]])
        assert item["result"] == rows[item["case_id"]]["result"]
    assert {c["case_id"] for c in report["remaining_failures"]} <= {
        i["case_id"] for i in review["items"]
    }
    reviewed = validate_reviews(review, list(rows.values()))
    assert read(ROOT / "project-phase.json") == {"completed_phase": 9, "completed_subphase": "9H"}
    print(
        "Evidence verified: 4 batches, 3 source archives; "
        f"actual new human reviews {len(reviewed)}/15"
    )


if __name__ == "__main__":
    main()
