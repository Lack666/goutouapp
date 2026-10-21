"""Current 9H source gates with immutable Git-backed historical provenance."""

import hashlib
import json
import re
import subprocess
from functools import lru_cache
from pathlib import Path

from check_security_9g import runtime_files
from phase8_android_demo import compiled_mobile_fingerprint
from phase9h_android_smoke import SCENES
from phase9h_capture import fingerprint

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "dcc7085c6061fe43081b2b914507fa8ebd733fcb"
REQUIRED = (
    "docs/PHASE_9H_ACCEPTANCE.md",
    "docs/PHASE_9H_MATRIX.json",
    "docs/PHASE_9H_PRODUCTION_RISKS.json",
    "docs/adr/0043-full-structured-erasure-and-proved-writer-recovery.md",
    "apps/server/tests/test_full_erasure_9h.py",
    "apps/server/tests/test_agent_recovery_9h.py",
    "apps/server/tests/test_full_restore_9h.py",
    "apps/server/tests/test_owner_operator_9h.py",
    "apps/mobile/tests/lifecycleController.test.ts",
    "apps/mobile/erasure-connected/lifecycle.spec.ts",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact(item, root=ROOT):
    path = (root / item["path"]).resolve()
    if not path.is_relative_to((root / "docs/evidence/phase9h").resolve()) or not path.is_file():
        raise RuntimeError("9H evidence missing or outside phase9h")
    if digest(path) != item["sha256"]:
        raise RuntimeError("9H evidence hash mismatch")
    return path


def gate(record, root=ROOT, *, current=True):
    if (
        record.get("exit_code") != 0
        or artifact(record["exit"], root).read_text("utf-8").strip() != "0"
    ):
        raise RuntimeError("9H independent zero exit required")
    source = json.loads(artifact(record["source"], root).read_text("utf-8"))
    log = artifact(record["log"], root)
    if source.get("exit_code") != 0 or source.get("log_sha256") != digest(log):
        raise RuntimeError("9H capture/log/exit binding mismatch")
    if current and (
        source.get("source_fingerprint") != fingerprint(root)
        or source.get("end_source_fingerprint") != fingerprint(root)
    ):
        raise RuntimeError("9H execution-time source fingerprint drift")
    return log.read_text("utf-8"), source


@lru_cache(maxsize=20)
def pinned_matrix(root, phase):
    name = f"docs/PHASE_{phase}_MATRIX.json"
    try:
        result = subprocess.run(
            ["git", "-c", f"safe.directory={root.as_posix()}", "show", f"{BASELINE}:{name}"],
            cwd=root,
            capture_output=True,
            check=True,
            timeout=10,
        )
        return result.stdout.replace(b"\r\n", b"\n")
    except (OSError, subprocess.SubprocessError):
        raise RuntimeError("9H immutable Git historical provenance unavailable") from None


def historical(root, phase):
    path = root / f"docs/PHASE_{phase}_MATRIX.json"
    if path.read_bytes().replace(b"\r\n", b"\n") != pinned_matrix(root, phase):
        raise RuntimeError("9H historical matrix differs from Git")

    def inspect(value):
        if isinstance(value, dict):
            if str(value.get("path", "")).startswith("docs/evidence/") and "sha256" in value:
                target = (root / value["path"]).resolve()
                if (
                    not target.is_relative_to((root / "docs/evidence").resolve())
                    or not target.is_file()
                    or digest(target) != value["sha256"]
                ):
                    raise RuntimeError("9H historical artifact hash drift")
            for child in value.values():
                inspect(child)
        elif isinstance(value, list):
            for child in value:
                inspect(child)

    inspect(json.loads(path.read_text("utf-8")))


def native_report(row, root, steps, runtime, *, current=False):
    _, source = gate(row, root, current=current)
    if source.get("synthetic_only") is not True:
        raise RuntimeError("9H native synthetic boundary missing")
    report = json.loads(artifact(row["report"], root).read_text("utf-8"))
    if (
        not report
        or report[0]["execution"].get("steps") != steps
        or report[0]["execution"].get("runtime_fingerprint_9h") != runtime
    ):
        raise RuntimeError("9H native execution recorded stale runtime/scenario")
    expected = [s.partition(" ")[0] for s in steps if s != "stop"]
    actual = [
        r["command"] if r.get("status") == "done" else "state"
        for r in report
        if r.get("status") == "done" or "ui_state" in r
    ]
    if actual != expected or any(r.get("status") in {"failed", "FAIL"} for r in report):
        raise RuntimeError("9H partial/spliced/failed Android execution rejected")
    builds = [r["native_build"] for r in report if "native_build" in r]
    mobile = compiled_mobile_fingerprint(root)
    if not builds or any(
        b.get("compiled_mobile_fingerprint") != mobile
        or b.get("expected_mobile_fingerprint") != mobile
        or b.get("verified") is not True
        or b.get("transport") != "actual Android accessibility"
        for b in builds
    ):
        raise RuntimeError("9H actual compiled Android source proof missing or stale")
    proofs = [r["database"] for r in report if "database" in r]
    if not proofs or any("wire" not in p for p in proofs):
        raise RuntimeError("9H actual PostgreSQL and signed native wire required")
    requests = [r for p in proofs for r in p["wire"]["requests"] if not r["host_setup"]]
    return report, requests


def native(matrix, root=ROOT):
    runtime = hashlib.sha256(json.dumps(runtime_files(root), sort_keys=True).encode()).hexdigest()
    rows = matrix.get("native", [])
    if len(rows) != len(SCENES) or {r["scene"] for r in rows} != set(SCENES):
        raise RuntimeError("9H thirteen fresh Android scenes required")
    for row in rows:
        steps = json.loads((root / "scripts/native" / SCENES[row["scene"]]).read_text("utf-8"))
        report, requests = native_report(row, root, steps, runtime)
        if "wire_supplement" in row:
            if row["scene"] != "lifecycle_faults" or steps[-1] != "stop":
                raise RuntimeError("9H unexpected native wire supplement")
            # A separate complete execution adds only a final SQL/wire snapshot.
            # Never alter/splice the original canonical report or waive a command.
            _, supplemental_requests = native_report(
                row["wire_supplement"],
                root,
                [*steps[:-1], "evidence", "stop"],
                runtime,
                current=True,
            )
            requests = supplemental_requests
        if row["scene"] in {"person", "relationship", "lifecycle_faults"}:
            for suffix in (
                "/lifecycle-erasures/prepare",
                "/lifecycle-erasures/execute",
                "/lifecycle-erasures/receipts/",
            ):
                if not any(
                    suffix in r["path"] and r["bearer"] and r.get("status") == 200 for r in requests
                ):
                    raise RuntimeError("9H native formal lifecycle prepare/execute/receipt missing")
        if row["scene"] in {"person", "relationship"} and not any(
            r.get("assert_lifecycle") == row["scene"] and r.get("deleted") is True for r in report
        ):
            raise RuntimeError("9H native structured target SQL deletion missing")


def root_gate(record, root, marker):
    log, source = gate(record, root)
    if source.get("phase_marker") != marker:
        raise RuntimeError("9H root marker provenance mismatch")
    for required in (
        "PASS: all active Phase 0..",
        "21/21 checks passed",
        "Golden annotation validation passed: {'cases': 83",
        "43 operations",
        "22 passed",
        "4 passed",
        "PASS: Phase9H full erasure/proved recovery gates",
    ):
        if required not in log:
            raise RuntimeError("9H complete root regression evidence required")
    if source.get("command") != ["make.cmd", "verify"]:
        raise RuntimeError("9H original full make.cmd verify invocation required")


def check(root=ROOT, *, completed=False):
    for name in REQUIRED:
        if not (root / name).is_file():
            raise RuntimeError("Missing Phase9H gate: " + name)
    matrix = json.loads((root / "docs/PHASE_9H_MATRIX.json").read_text("utf-8"))
    if (
        matrix.get("phase") != "9H"
        or matrix.get("source_fingerprint") != fingerprint(root)
        or matrix.get("baseline_commit") != BASELINE
    ):
        raise RuntimeError("9H current-source/baseline scope drift")
    if matrix.get("open_p0_p1") != [] or matrix.get("production_acceptable") is not False:
        raise RuntimeError("9H blockers/production boundary invalid")
    criteria = json.loads((root / "docs/PHASE_9_EXIT_CRITERIA_MATRIX.json").read_text("utf-8"))
    original_ids = {
        "P9-UPLOAD",
        "P9-TYPE",
        "P9-PATH",
        "P9-OWNER",
        "P9-DELETE",
        "P9-LOG",
        "P9-SAFETY",
        "P9-RELIABILITY",
        "P9-CLOSEOUT",
    }
    if {r["id"] for r in criteria["requirements"]} != original_ids or len(
        criteria["requirements"]
    ) != len(original_ids):
        raise RuntimeError("9H original engineering criteria traceability incomplete")
    if criteria.get("public_production_readiness") != "NOT APPROVED":
        raise RuntimeError("9H cannot certify public production")
    for row in criteria["requirements"]:
        if type(row.get("blocks_phase9")) is not bool or not all(
            row.get(field)
            for field in (
                "requirement",
                "implementation",
                "tests",
                "evidence",
                "status",
                "remaining",
            )
        ):
            raise RuntimeError("9H original engineering criterion incomplete")
        for reference in row["implementation"] + row["tests"]:
            name, _, function = reference.partition("::")
            path = (root / name).resolve()
            if (
                not path.is_relative_to(root.resolve())
                or not path.is_file()
                or (function and f"def {function}(" not in path.read_text("utf-8"))
            ):
                raise RuntimeError("9H engineering implementation/test link missing")
    risks = json.loads((root / "docs/PHASE_9H_PRODUCTION_RISKS.json").read_text("utf-8"))
    if risks.get("production_acceptable") is not False or {r["id"] for r in risks["risks"]} != {
        "R-06",
        "R-07",
        "R-08",
        "R-09",
        "R-10",
        "L-OUTBOX",
        "L-ACCOUNT",
        "L-PRIMARY-LOSS",
        "L-PUBLIC",
        "L-OBSERVABILITY",
        "L-EXPORT-COPIES",
        "L-WINDOWS-TEST",
    }:
        raise RuntimeError("9H risk/production audit incomplete")
    for phase in ("9B", "9C", "9D", "9E", "9F", "9G"):
        historical(root, phase)
    baseline, _ = gate(matrix["baseline"], root, current=False)
    if not all(
        v in baseline
        for v in (
            "810 passed",
            "396 passed",
            "Ran 99 tests",
            "21/21 checks passed",
            "PASS: all active Phase 0..8 gates",
        )
    ):
        raise RuntimeError("9H pristine full 9G baseline required")
    for name, count in (
        ("admission_revalidation", "27 passed"),
        ("lifecycle_revalidation", "44 passed"),
        ("erasure_revalidation", "39 passed"),
        ("integration_revalidation", "7 passed"),
        ("focused", "49 passed"),
    ):
        log, _ = gate(matrix[name], root)
        if count not in log:
            raise RuntimeError("9H complete prior regression required: " + name)
    for name, minimum in (("backend", 810), ("mobile", 396)):
        log, _ = gate(matrix[name], root)
        if not any(int(n) > minimum for n in re.findall(r"(\d+) passed", log)) or re.search(
            r"\d+ (?:skipped|deselected|failed)", log
        ):
            raise RuntimeError("9H full current suite including all prior tests required")
        expected = (
            ["uv", "--cache-dir", ".cache/uv", "run", "pytest", "apps/server/tests", "-q"]
            if name == "backend"
            else ["pnpm", "--filter", "@goutou/mobile", "test"]
        )
        if (
            json.loads(artifact(matrix[name]["source"], root).read_text("utf-8")).get("command")
            != expected
        ):
            raise RuntimeError("9H complete unfiltered suite invocation required")
    boundary_log, boundary_source = gate(matrix["full_boundaries"], root)
    if "42 passed" not in boundary_log or boundary_source.get("command") != [
        "uv",
        "--cache-dir",
        ".cache/uv",
        "run",
        "pytest",
        "apps/server/tests/test_full_erasure_9h.py",
        "apps/server/tests/test_agent_recovery_9h.py",
        "apps/server/tests/test_full_restore_9h.py",
        "apps/server/tests/test_owner_operator_9h.py",
        "-q",
    ]:
        raise RuntimeError(
            "9H complete real writer/erasure/operator/archive boundary suite required"
        )
    for row in criteria["requirements"]:
        for name in row["evidence"]:
            if name in {"pre_marker", "post_marker"} and matrix.get("acceptance_state") != "closed":
                continue
            if name not in matrix:
                raise RuntimeError("9H original criterion evidence link missing")
            gate(matrix[name], root)
    if matrix.get("acceptance_state") == "closed" and (
        matrix.get("status") != "PASS"
        or criteria.get("phase9_overall") != "PASS"
        or any(r["status"] != "PASS" or r["blocks_phase9"] for r in criteria["requirements"])
    ):
        raise RuntimeError("9H closed whole-phase engineering criteria incomplete")
    repository, _ = gate(matrix["repository"], root)
    if not any(int(n) > 99 for n in re.findall(r"Ran (\d+) tests", repository)):
        raise RuntimeError("9H complete repository regression required")
    web, _ = gate(matrix["web"], root)
    if "4 passed" not in web:
        raise RuntimeError("9H original and new actual Web regression required")
    native(matrix, root)
    if completed:
        root_gate(matrix["pre_marker"], root, {"completed_phase": 8, "completed_subphase": "9G"})
    if matrix.get("acceptance_state") == "closed":
        root_gate(matrix["post_marker"], root, matrix["final_marker"])


def revalidate_prior(phase, root=ROOT):
    if not (root / "docs/PHASE_9H_MATRIX.json").is_file():
        return False
    check(root)
    historical(root, phase)
    return True


if __name__ == "__main__":
    check()
    print("PASS: Phase9H full erasure/proved recovery gates")
