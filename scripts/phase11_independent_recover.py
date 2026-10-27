"""Recover saved batch-0 case checkpoints without making any Provider calls.

The paid process failed in git rev-parse after all cases were saved. Original
per-call timings and node traces were not checkpointed and cannot be recovered.
Never present these reconstructed call records as original live trace events.
"""

import json
import subprocess

from evals.agent.independent import (
    DATASET,
    PLAN,
    RESULTS,
    check_frozen,
    fingerprint,
    sha,
    write_new,
)


def main():
    plan = check_frozen()
    rows = [
        json.loads((RESULTS / f"independent-{i}-v1.json").read_text(encoding="utf-8"))
        for i in plan["batches"][0]
    ]
    calls = []
    for row in rows:
        assert row["contextual_review"]["calls"] == 0
        assert (
            len(row["pydantic"]) == len(row["raw_visible_outputs"]) == row["provider"]["requests"]
        )
        for schema, raw in zip(row["pydantic"], row["raw_visible_outputs"], strict=True):
            calls.append(
                {
                    "kind": "provider",
                    "operation": "structured_output",
                    "schema": schema["schema"],
                    "status": schema["status"],
                    "error": schema["error"],
                    "usage": raw["usage"],
                    "model": raw["model"],
                    "duration_ms": None,
                    "run_id": row["result"]["run_id"],
                    "provenance": "reconstructed_from_original_case_checkpoint_not_live_trace",
                }
            )
    write_new(
        RESULTS / "independent-live-batch-0-v1.json",
        {
            "version": "independent-quality-v1",
            "mode": "live",
            "batch": 0,
            "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "source_fingerprint": fingerprint(),
            "source_fingerprint_start": None,
            "source_stable": True,
            "source_binding_basis": (
                "Immutable plan verified by runner before calls and again at recovery"
            ),
            "dataset_sha256": sha(DATASET),
            "plan_sha256": sha(PLAN),
            "prompt_version": "phase11-contextual-content-review-v1",
            "budget": {
                "requests": len(calls),
                "reserved_cny": None,
                "max_requests": 24,
                "max_cost_cny": 1.25,
                "max_tokens": 500000,
            },
            "cases": rows,
            "traces": calls,
            "evidence_recovery": {
                "reason": (
                    "git ownership check failed during batch artifact assembly "
                    "after all 3 checkpoints"
                ),
                "paid_retries": 0,
                "lost_fields": ["node_traces", "provider_duration_ms", "reserved_cny"],
                "case_latency_and_visible_outputs": "original checkpoint values, unchanged",
                "provider_records": (
                    "reconstructed statuses/schema from checkpoint; usage from original responses"
                ),
            },
        },
    )
    print(f"Recovered {len(rows)} original cases / {len(calls)} calls; no paid calls")


if __name__ == "__main__":
    main()
