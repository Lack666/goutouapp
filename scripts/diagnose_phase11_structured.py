"""Replay frozen synthetic analysis failures without invoking a provider."""

import hashlib
import json
import sys
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/server"))

from app.agent.analysis_validation import (  # noqa: E402
    ACTION_CUES,
    UNSUPPORTED_CERTAINTY_CUES,
)
from app.agent.contracts import AnalysisResult  # noqa: E402

RESULTS = ROOT / "evals/agent/results"


def diagnose():
    failures = []
    for group in ("communication", "grounding"):
        path = RESULTS / f"final-live-{group}.json"
        run = json.loads(path.read_text(encoding="utf-8"))
        cases = {c["run_id"]: c for c in run["cases"]}
        calls = [t for t in run["traces"] if t["kind"] == "provider"]
        for trace, output in zip(calls, run["synthetic_visible_outputs"], strict=True):
            case = cases[trace["run_id"]]
            if case["status"] == "completed" or trace.get("schema") != "AnalysisResult":
                continue
            errors = []
            matches = []
            try:
                analysis = AnalysisResult.model_validate_json(output["content"], strict=True)
            except ValidationError as exc:
                errors = exc.errors(include_url=False, include_context=False)
            else:
                for statement in (
                    analysis.core_issue,
                    *(
                        point.statement
                        for field in (
                            "observations",
                            "relationship_dynamics",
                            "risks",
                            "constraints",
                            "uncertainties",
                        )
                        for point in getattr(analysis, field)
                    ),
                ):
                    for pattern in (*ACTION_CUES, *UNSUPPORTED_CERTAINTY_CUES):
                        if match := pattern.search(statement):
                            matches.append({"statement": statement, "match": match.group()})
            failures.append(
                {
                    "case_id": case["id"],
                    "run_id": case["run_id"],
                    "source": path.relative_to(ROOT).as_posix(),
                    "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "node": trace["node"],
                    "provider_trace": trace,
                    "finish_reason": output["finish_reason"],
                    "usage": output["usage"],
                    "max_output_tokens": run["model_parameters"]["max_tokens"],
                    "visible_output_sha256": hashlib.sha256(output["content"].encode()).hexdigest(),
                    "pydantic_errors": errors,
                    "guard_matches": matches,
                }
            )
    return failures


if __name__ == "__main__":
    destination = Path(sys.argv[1])
    if destination.exists():
        raise SystemExit("Refusing to overwrite diagnosis evidence")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(diagnose(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
