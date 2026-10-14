"""Fail closed on missing 9C evidence, topology, risks or source drift."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "docs/PHASE_9C_ACCEPTANCE.md",
    "docs/RESOURCE_ADMISSION_POLICY.md",
    "docs/UPLOAD_RELIABILITY.md",
    "docs/adr/0038-shared-resource-admission-and-worker-fences.md",
    "apps/server/tests/test_resource_admission.py",
    "apps/mobile/tests/resourceAdmission.test.ts",
)


def source_fingerprint(root=ROOT):
    paths = list((root / "apps/server/app").rglob("*.py"))
    paths += list((root / "apps/server/alembic").rglob("*.py"))
    paths += list((root / "apps/server/tests").rglob("*.py"))
    paths += [
        root / name
        for name in (
            "apps/server/tests/test_resource_admission.py",
            "scripts/verify.py",
            "scripts/check_security_9c.py",
            "apps/server/import_artifact_cleanup.py",
            "apps/mobile/tests/resourceAdmission.test.ts",
        )
    ]
    hashes = {
        path.relative_to(root).as_posix(): hashlib.sha256(
            path.read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
        for path in sorted(paths)
    }
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()


def artifact(descriptor, root=ROOT):
    path = (root / descriptor["path"]).resolve()
    if not path.is_relative_to((root / "docs/evidence/phase9c").resolve()) or not path.is_file():
        raise RuntimeError("9C evidence missing or outside phase9c")
    if hashlib.sha256(path.read_bytes()).hexdigest() != descriptor["sha256"]:
        raise RuntimeError("9C evidence hash mismatch")
    return path


def gate(record, root=ROOT):
    if (
        record.get("exit_code") != 0
        or artifact(record["exit"], root).read_text("utf-8").strip() != "0"
    ):
        raise RuntimeError("9C requires an independent zero exit")
    artifact(record["log"], root)


def check(root=ROOT, *, completed=False):
    for name in REQUIRED:
        if not (root / name).is_file():
            raise RuntimeError("Missing Phase9C gate: " + name)
    matrix = json.loads((root / "docs/PHASE_9C_MATRIX.json").read_text("utf-8"))
    if matrix.get("phase") != "9C" or matrix.get("open_p0_p1") != []:
        raise RuntimeError("9C scope/blocking findings invalid")
    if matrix.get("production_acceptable") is not False or not matrix.get("production_blockers"):
        raise RuntimeError("9C cannot certify undeployed public/retention/identity controls")
    topology = matrix["topology"]
    if (
        topology.get("shared_local_root") is not True
        or topology.get("actual_worker_processes", 0) < 2
    ):
        raise RuntimeError("9C requires tested shared-filesystem multi-process topology")
    current_fingerprint = source_fingerprint(root)
    if matrix.get("source_fingerprint") != current_fingerprint:
        # A later authorized phase changes the broad server fingerprint. Keep the
        # historical 9C matrix/evidence immutable; require a separately hashed
        # fresh COMPLETE 9C regression on the current source instead of waiving it.
        replacement = root / "docs/PHASE_9E_MATRIX.json"
        evidence_phase, expected_phase = "phase9e", "9E"
        if (root / "docs/PHASE_9F_MATRIX.json").is_file():
            replacement = root / "docs/PHASE_9F_MATRIX.json"
            evidence_phase, expected_phase = "phase9f", "9F"
        if (root / "docs/PHASE_9G_MATRIX.json").is_file():
            replacement = root / "docs/PHASE_9G_MATRIX.json"
            evidence_phase, expected_phase = "phase9g", "9G"
        if not replacement.is_file():
            replacement = root / "docs/PHASE_9D_MATRIX.json"
            evidence_phase, expected_phase = "phase9d", "9D"
        if not replacement.is_file():
            raise RuntimeError("9C tested source fingerprint drift")
        newer = json.loads(replacement.read_text("utf-8"))
        record = newer.get("admission_revalidation", {})
        original_hash = hashlib.sha256(
            (root / "docs/PHASE_9C_MATRIX.json").read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
        if (
            newer.get("phase") != expected_phase
            or record.get("source_fingerprint") != current_fingerprint
            or record.get("historical_matrix_sha256") != original_hash
            or record.get("exit_code") != 0
        ):
            raise RuntimeError("9C tested source fingerprint drift")
        for field in ("log", "exit"):
            descriptor = record[field]
            path = (root / descriptor["path"]).resolve()
            if (
                not path.is_relative_to((root / "docs/evidence" / evidence_phase).resolve())
                or not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != descriptor["sha256"]
            ):
                raise RuntimeError("9C current-source regression evidence invalid")
            if field == "exit" and path.read_text("utf-8").strip() != "0":
                raise RuntimeError("9C current-source regression requires zero exit")
            if field == "log" and "27 passed" not in path.read_text("utf-8"):
                raise RuntimeError("9C complete 27-case regression required")
    required = {
        "early",
        "owner",
        "global",
        "storage",
        "rates",
        "idle",
        "total",
        "disconnect",
        "crash_body",
        "crash_partial",
        "crash_artifact",
        "live_fence",
        "cleanup",
        "database",
        "disk",
        "finalize",
        "metrics",
        "speakers",
        "mobile",
    }
    if set(matrix["coverage"]) != required:
        raise RuntimeError("9C security coverage incomplete")
    for references in matrix["coverage"].values():
        if not references:
            raise RuntimeError("9C coverage lacks linked tests")
        for reference in references:
            filename, _, function = reference.partition("::")
            path = (root / filename).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                raise RuntimeError("9C linked test missing")
            if function and f"def {function}(" not in path.read_text("utf-8"):
                raise RuntimeError("9C linked test function missing")
    gate(matrix["focused"], root)
    if matrix.get("acceptance_state") == "closed" or "post_marker" in matrix:
        gate(matrix["post_marker"], root)
    if completed:
        if matrix.get("status") != "PASS":
            raise RuntimeError("9C completed marker requires PASS")
        gate(matrix["pre_marker"], root)


if __name__ == "__main__":
    check()
    print("PASS: Phase9C shared admission/body deadlines/recovery/privacy gates")
