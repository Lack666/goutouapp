"""Focused Phase11 evidence checks; never replaces the formal root verifier."""

import ast
import hashlib
import json
import re
import subprocess
from zipfile import ZipFile

from evals.agent.harness import ROOT, cases, summarize


def git(*args):
    return subprocess.check_output(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", *args], cwd=ROOT
    )


def main():
    marker = json.loads((ROOT / "project-phase.json").read_text(encoding="utf-8"))
    assert marker == {"completed_phase": 9, "completed_subphase": "9H"}
    frozen = ROOT / "evals/golden_cases.jsonl"
    assert frozen.read_bytes().replace(b"\r\n", b"\n") == git(
        "show", "HEAD:evals/golden_cases.jsonl"
    ).replace(b"\r\n", b"\n")
    assert not git(
        "diff", "--name-only", "HEAD", "--", "knowledge", "docs/PHASE_9_FINAL_ACCEPTANCE.md"
    )
    assert len(cases()) == 60
    results = ROOT / "evals/agent/results"
    aggregate = json.loads((results / "aggregate-final.json").read_text(encoding="utf-8"))
    rows, calls = [], []
    for item in aggregate["evidence"]:
        path = ROOT / item["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
        record = json.loads(path.read_text(encoding="utf-8"))
        assert record["source_stable"] is True
        assert record["budget"]["requests"] <= record["budget"]["max_requests"]
        rows.extend(record["cases"])
        calls.extend(e for e in record["traces"] if e["kind"] == "provider")
    assert aggregate["metrics"] == summarize(rows, calls)
    assert len(rows) == 20
    archive = results / "evaluated-source.zip"
    digest = hashlib.sha256()
    style_only = []
    with ZipFile(archive) as zipped:
        for name in zipped.namelist():
            original = zipped.read(name)
            digest.update(name.encode())
            digest.update(original)
            current = (ROOT / name).read_bytes()
            if current != original:
                assert name.endswith(".py")
                assert ast.dump(ast.parse(current)) == ast.dump(ast.parse(original))
                style_only.append(name)
    assert digest.hexdigest() == aggregate["source_fingerprint"]
    private_keys = re.findall(
        r"sk-[A-Za-z0-9_-]+", (ROOT / "api.txt").read_text(encoding="utf-8-sig")
    )
    forbidden = {
        "content",
        "messages",
        "authorization",
        "api_key",
        "reasoning_content",
        "current_message",
        "retrieved_context",
        "loaded_memories",
    }
    for path in results.glob("*.json"):
        text = path.read_text(encoding="utf-8")
        assert not any(key in text for key in private_keys), "Credential in evidence"
        record = json.loads(text)
        for event in record.get("traces", []):
            assert not forbidden.intersection(event), "Private trace field"
    result = {
        "official_marker": marker,
        "golden83_sha256": hashlib.sha256(frozen.read_bytes()).hexdigest(),
        "evaluated_source_fingerprint": digest.hexdigest(),
        "source_archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "only_formatting_changed_after_live": style_only,
        "synthetic_cases": len(cases()),
        "live_cases": len(rows),
        "quality_gate": aggregate["quality_gate"],
        "full_regression": "NOT RUN",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
