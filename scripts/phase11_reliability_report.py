"""Build separate, hash-bound reliability evidence and a blank human review packet."""

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "apps/server")]

from evals.agent.harness import DATASET, fingerprint, summarize  # noqa: E402
from evals.agent.review import packet  # noqa: E402

RESULTS = ROOT / "evals/agent/results"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def evidence(path):
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def write(path, document):
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(document, ensure_ascii=False, indent=2) + "\n")


def metrics(runs):
    return summarize(
        [c for r in runs for c in r["cases"]],
        [t for r in runs for t in r["traces"] if t["kind"] == "provider"],
    )


def main():
    prefix = "reliability-fix-v5"
    paths = [RESULTS / f"reliability-fix-v{v}-original-five.json" for v in (3, 4, 5)]
    regression = RESULTS / f"{prefix}-regression.json"
    if regression.exists():
        paths.append(regression)
    runs = [read(p) for p in paths]
    current = [r for r in runs if r["prompt_version"] == "phase11-source-first-v5"]
    assert current and all(r["source_stable"] for r in runs)
    assert all(r["source_fingerprint"] == fingerprint() for r in current)
    assert all(r["budget"]["requests"] <= 30 for r in runs)
    original = {
        c["id"]: c
        for g in ("communication", "grounding")
        for c in read(RESULTS / f"final-live-{g}.json")["cases"]
    }
    comparison = [
        {
            "case_id": c["id"],
            "before": original[c["id"]]["status"],
            "after": c["status"],
            "after_run_id": c["run_id"],
        }
        for c in runs[2]["cases"]
    ]
    assert len(comparison) == 5
    destinations = [
        RESULTS / f"{prefix}-report.json",
        RESULTS / f"{prefix}-source.zip",
        RESULTS / f"{prefix}-human-review-15.json",
    ]
    if any(p.exists() for p in destinations):
        raise SystemExit("Refusing to overwrite reliability evidence")
    with ZipFile(destinations[1], "x", ZIP_DEFLATED) as zipped:
        for p in [
            *sorted((ROOT / "apps/server/app").rglob("*.py")),
            *sorted((ROOT / "evals/agent").glob("*.py")),
            DATASET,
            ROOT / "uv.lock",
        ]:
            zipped.writestr(p.relative_to(ROOT).as_posix(), p.read_bytes())
    sources = [RESULTS / "final-live-safety.json"]
    # If expansion was not allowed, original successes remain explicitly older evidence.
    if not regression.exists():
        sources += [RESULTS / f"final-live-{g}.json" for g in ("communication", "grounding")]
    sources += [p for p, r in zip(paths, runs, strict=True) if r in current]
    rows = {c["id"]: c for p in sources for c in read(p)["cases"]}
    old_review = read(RESULTS / "human-review-15.json")
    if regression.exists():
        review_rows = [c for r in current for c in r["cases"]]
        review_rows += read(RESULTS / "final-live-safety.json")["cases"][:5]
    else:
        review_rows = [rows[i["case_id"]] for i in old_review["items"]]
    review = packet(review_rows)
    assert len(review["items"]) == 15
    assert all(
        i["reviewer"] is None and all(v is None for v in i["scores"].values())
        for i in review["items"]
    )
    review["sources"] = [evidence(p) for p in sources]
    review["note"] = (
        "New blank scoring packet. No old human scores copied. Safety outputs are frozen v2 "
        "evidence, not fresh v5 safety runs. Each source/version is shown in the UI."
    )
    write(destinations[2], review)
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "PARTIAL RELIABILITY FIX / QUALITY GATE FAIL; new human review pending",
        "official_marker": read(ROOT / "project-phase.json"),
        "source_fingerprint": fingerprint(),
        "source_archive": evidence(destinations[1]),
        "runs": [evidence(p) for p in paths],
        "baseline_diagnosis": evidence(RESULTS / "reliability-fix-v3-diagnosis.json"),
        "original_five_comparison": comparison,
        "attempts": [
            {
                "path": p.name,
                "metrics": r["metrics"],
                "failed_cases": [c["id"] for c in r["cases"] if c["status"] != "completed"],
            }
            for p, r in zip(paths, runs, strict=True)
        ],
        "current_version_metrics": metrics(current),
        "remaining_failures": [
            {
                "case_id": c["id"],
                "status": c["status"],
                "failed_checks": [k for k, v in c["checks"].items() if not v],
                "failed_nodes": [
                    t["node"]
                    for t in r["traces"]
                    if t["kind"] == "node_end"
                    and t["run_id"] == c["run_id"]
                    and t["status"] == "failed"
                ],
            }
            for r in current
            for c in r["cases"]
            if not c["passed"]
        ],
        "all_paid_attempts_metrics": metrics(runs),
        "paid_budgets": [r["budget"] for r in runs],
        "human_review": evidence(destinations[2]),
        "prior_human_review": evidence(RESULTS / "human-review-15.json"),
        "limits": [
            "Small selected samples; P95 is not a production SLA",
            "JSON mode does not guarantee schema validity; no retry or repair",
            "No new FastAPI/PostgreSQL E2E; real LangGraph retests only",
            "Old metrics and all failed attempts retained; no full regression",
            "Cost is the official peak CNY upper bound, not a billing receipt",
        ],
    }
    write(destinations[0], report)
    print(
        json.dumps(
            {
                key: {k: v for k, v in value.items() if k != "token_distribution"}
                for key, value in (
                    ("current", report["current_version_metrics"]),
                    ("all_attempts", report["all_paid_attempts_metrics"]),
                )
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
