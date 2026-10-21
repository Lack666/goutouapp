"""Current-source Mobile erasure evidence; historical acceptance stays immutable."""

import hashlib
import json
from pathlib import Path

from check_security_9b import mobile_fingerprint, native_check
from check_security_9c import source_fingerprint as admission_fingerprint
from check_security_9d import source_fingerprint as lifecycle_fingerprint
from check_security_9e import revalidation
from check_security_9e import source_fingerprint as erasure_fingerprint

ROOT = Path(__file__).resolve().parents[1]
NATIVE_SCENES = {"dataset", "conversation", "faults", "restart_session"}
REQUIRED = (
    "docs/PHASE_9F_ACCEPTANCE.md",
    "docs/MOBILE_DATA_ERASURE.md",
    "docs/PHASE_9F_MATRIX.json",
    "apps/mobile/src/data/erasureController.ts",
    "apps/mobile/src/api/erasureAdapter.ts",
    "apps/mobile/src/features/ConnectedErasurePanel.tsx",
    "apps/server/tests/test_dataset_discovery.py",
    "apps/mobile/tests/erasureController.test.ts",
    "apps/mobile/erasure-connected/web.spec.ts",
    "tests/test_security_9f_tooling.py",
)


def source_fingerprint(root=ROOT):
    names = [
        "scripts/check_security_9f.py",
        "scripts/verify.py",
        "tests/test_security_9f_tooling.py",
        "apps/server/resource_demo_support.py",
        "apps/mobile/connected/web.spec.ts",
    ]
    for folder in ("apps/mobile/tests", "apps/mobile/erasure-connected", "scripts/native"):
        names.extend(
            p.relative_to(root).as_posix() for p in (root / folder).rglob("*") if p.is_file()
        )
    hashes = {
        name: hashlib.sha256((root / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        for name in sorted(names)
    }
    hashes.update(erasure=erasure_fingerprint(root), mobile=mobile_fingerprint(root))
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()


def artifact(descriptor, root=ROOT):
    path = (root / descriptor["path"]).resolve()
    if not path.is_relative_to((root / "docs/evidence/phase9f").resolve()) or not path.is_file():
        raise RuntimeError("9F evidence missing or outside phase9f")
    if hashlib.sha256(path.read_bytes()).hexdigest() != descriptor["sha256"]:
        raise RuntimeError("9F evidence hash mismatch")
    return path


def gate(record, root=ROOT):
    if (
        record.get("exit_code") != 0
        or artifact(record["exit"], root).read_text("utf-8").strip() != "0"
    ):
        raise RuntimeError("9F independent zero exit required")
    return artifact(record["log"], root).read_text("utf-8")


def native_erasure(matrix, root=ROOT, *, expected_source=None, expected_erasure=None):
    native = matrix["erasure_native"]
    if (
        native.get("status") != "PASS"
        or native.get("source_fingerprint") != (expected_source or source_fingerprint(root))
        or native.get("synthetic_only") is not True
        or not native.get("device")
    ):
        raise RuntimeError("9F fresh actual Android erasure evidence required")
    rows = native["scenes"]
    if len(rows) != len(NATIVE_SCENES) or {r["scene"] for r in rows} != NATIVE_SCENES:
        raise RuntimeError("9F native deletion/fault/restart coverage incomplete")
    for row in rows:
        if row.get("status") != "PASS" or row.get("exit_code") != 0:
            raise RuntimeError("9F native scene failed")
        paths = {
            name: artifact(row["artifacts"][name], root)
            for name in ("steps", "report", "log", "exit")
        }
        if paths["exit"].read_text("utf-8").strip() != "0":
            raise RuntimeError("9F native independent exit required")
        report = json.loads(paths["report"].read_text("utf-8"))
        steps = json.loads(paths["steps"].read_text("utf-8"))
        canonical = root / "scripts/native" / f"phase9f_{row['scene']}.json"
        if not canonical.is_file() or json.loads(canonical.read_text("utf-8")) != steps:
            raise RuntimeError("9F native scenario differs from required current script")
        expected = [s.partition(" ")[0] for s in steps if s != "stop"]
        actual = [
            r["command"] if r.get("status") == "done" else "state"
            for r in report
            if r.get("status") == "done" or "ui_state" in r
        ]
        if not report or report[0]["execution"]["steps"] != steps or expected != actual:
            raise RuntimeError("9F partial/spliced native execution rejected")
        if report[0]["execution"].get("mobile_fingerprint") != mobile_fingerprint(root) or report[
            0
        ]["execution"].get("erasure_fingerprint") != (
            expected_erasure or erasure_fingerprint(root)
        ):
            raise RuntimeError("9F native execution recorded stale application source")
        if any(r.get("status") in {"FAIL", "failed"} for r in report):
            raise RuntimeError("9F failed native step")
        proofs = [r["database"] for r in report if "database" in r]
        if not proofs or not all("erasure" in p and "wire" in p for p in proofs):
            raise RuntimeError("9F native PostgreSQL/signed wire witness required")
        requests = [r for p in proofs for r in p["wire"]["requests"] if not r["host_setup"]]
        if row["scene"] in {"dataset", "conversation", "faults"}:
            for suffix in ("/erasures/prepare", "/erasures/execute", "/erasures/receipts/"):
                if not any(
                    suffix in r["path"] and r["bearer"] and r.get("status") == 200 for r in requests
                ):
                    raise RuntimeError("9F actual native prepare/execute/receipt missing")
        assertions = [r for r in report if r.get("assert_erased") == row["scene"]]
        if row["scene"] in {"dataset", "conversation"} and not any(
            r.get("deleted") is True and r.get("message_count") == 0 for r in assertions
        ):
            raise RuntimeError("9F native physical deletion assertion missing")


def root_gate(record, root, subphase):
    log = gate(record, root)
    for text in (
        "PASS: all active Phase 0..8 gates",
        "PASS: Phase9E guarded dataset/conversation erasure gates",
        "PASS: Phase9F Mobile self-service erasure gates",
        f"Completed subphase: {subphase}",
        "2 passed",
    ):
        if text not in log:
            raise RuntimeError("9F complete root regression evidence required")


def check(root=ROOT, *, completed=False):
    # Authorized 9H changes executable inputs. Preserve Git-pinned historical
    # evidence and require complete fresh suites and thirteen native executions.
    from check_security_9h import revalidate_prior

    if revalidate_prior("9F", root):
        return
    for name in REQUIRED:
        if not (root / name).is_file():
            raise RuntimeError("Missing Phase9F gate: " + name)
    matrix = json.loads((root / "docs/PHASE_9F_MATRIX.json").read_text("utf-8"))
    if matrix.get("phase") != "9F":
        raise RuntimeError("9F tested source fingerprint drift")
    expected_source = None
    expected_erasure = erasure_fingerprint(root)
    if matrix.get("source_fingerprint") != source_fingerprint(root):
        from check_security_9g import prior_9f

        historical = prior_9f(root)
        expected_source = historical["source_fingerprint"]
        expected_erasure = historical["erasure_revalidation"]["source_fingerprint"]
    if (
        matrix.get("production_acceptable") is not False
        or not matrix.get("production_blockers")
        or matrix.get("open_p0_p1") != []
    ):
        raise RuntimeError("9F production boundaries invalid")
    baseline = matrix["baseline"]
    baseline_log = artifact(baseline["log"], root).read_text("utf-8")
    baseline_exit = artifact(baseline["exit"], root).read_text("utf-8").strip()
    if baseline.get("commit") != "a6d8c2c" or baseline_exit != str(baseline.get("exit_code")):
        raise RuntimeError("9F original-source baseline provenance required")
    if baseline_exit != "0":
        issue = matrix.get("fixed_baseline_issue", {})
        if (
            baseline_exit != "1"
            or issue.get("id") != "9F-01"
            or "test_finalize_cancel_race_and_concurrent_uploads" not in baseline_log
            or "753 passed" not in baseline_log
            or "2 passed" not in gate(issue["regression"], root)
        ):
            raise RuntimeError("9F baseline failure must remain explicit and regression-fixed")
    if "374 passed" not in gate(matrix["baseline_mobile"], root):
        raise RuntimeError("9F original Mobile baseline required")
    for name, fingerprint, original, expected in (
        (
            "admission_revalidation",
            admission_fingerprint(root),
            "docs/PHASE_9C_MATRIX.json",
            "27 passed",
        ),
        (
            "lifecycle_revalidation",
            lifecycle_fingerprint(root),
            "docs/PHASE_9D_MATRIX.json",
            "44 passed",
        ),
        (
            "erasure_revalidation",
            erasure_fingerprint(root),
            "docs/PHASE_9E_MATRIX.json",
            "39 passed",
        ),
    ):
        revalidation(matrix, root, name, fingerprint, original, expected)
    native_check(matrix, root, evidence_phase="phase9f")
    for row in matrix["native"]["scenes"]:
        report = json.loads(artifact(row["artifacts"]["report"], root).read_text("utf-8"))
        if (
            report[0]["execution"].get("mobile_fingerprint") != mobile_fingerprint(root)
            or report[0]["execution"].get("erasure_fingerprint") != expected_erasure
        ):
            raise RuntimeError("9F prior native regression recorded stale application source")
    native_erasure(matrix, root, expected_source=expected_source, expected_erasure=expected_erasure)
    if "2 passed" not in gate(matrix["web"], root) or "5 passed" not in gate(
        matrix["discovery"], root
    ):
        raise RuntimeError("9F real Web and PostgreSQL discovery suites required")
    if completed:
        if matrix.get("status") != "PASS":
            raise RuntimeError("9F marker requires PASS")
        root_gate(matrix["pre_marker"], root, "9E")
    if matrix.get("acceptance_state") == "closed":
        root_gate(matrix["post_marker"], root, "9F")
        if matrix["pre_marker"]["log"]["path"] == matrix["post_marker"]["log"]["path"]:
            raise RuntimeError("9F independent pre/post processes required")


if __name__ == "__main__":
    check()
    print("PASS: Phase9F Mobile self-service erasure gates")
