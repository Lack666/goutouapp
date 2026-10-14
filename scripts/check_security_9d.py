"""9D gates: immutable actual lifecycle/restore evidence, source binding and limits."""

import hashlib
import json
from pathlib import Path

from check_security_9c import source_fingerprint as admission_fingerprint

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "docs/PHASE_9D_ACCEPTANCE.md",
    "docs/DATA_LIFECYCLE_INVENTORY.md",
    "docs/DATA_DELETION_CONTRACT.md",
    "docs/RETENTION_MAINTENANCE.md",
    "docs/BACKUP_RESTORE_POLICY.md",
    "docs/PHASE_9D_RISK_ASSESSMENT.json",
    "docs/adr/0039-controlled-retention-and-authoritative-restore-barrier.md",
    "apps/server/app/services/maintenance.py",
    "apps/server/app/services/backup_restore.py",
    "apps/server/retention_maintenance.py",
    "apps/server/backup_restore_demo.py",
    "apps/server/tests/test_data_lifecycle.py",
    "apps/server/tests/test_backup_restore.py",
    "tests/test_security_9d_tooling.py",
)
COVERAGE = {
    "lifecycle",
    "memory",
    "periodic",
    "cleanup",
    "quota",
    "crash",
    "multi_worker",
    "owner",
    "receipt",
    "backup_restore",
    "restore_failure",
    "restore_race",
    "privacy",
}


def source_fingerprint(root=ROOT):
    names = [
        "scripts/check_security_9d.py",
        "scripts/audit_evidence_privacy.py",
        "apps/server/retention_maintenance.py",
        "apps/server/backup_restore_demo.py",
        "tests/test_security_9d_tooling.py",
        "tests/test_security_gate.py",
    ]
    values = {
        name: hashlib.sha256((root / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        for name in names
    }
    values["admission"] = admission_fingerprint(root)
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def artifact(descriptor, root=ROOT):
    path = (root / descriptor["path"]).resolve()
    if not path.is_relative_to((root / "docs/evidence/phase9d").resolve()) or not path.is_file():
        raise RuntimeError("9D evidence missing or outside phase9d")
    if hashlib.sha256(path.read_bytes()).hexdigest() != descriptor["sha256"]:
        raise RuntimeError("9D evidence hash mismatch")
    return path


def gate(record, root=ROOT):
    if (
        record.get("exit_code") != 0
        or artifact(record["exit"], root).read_text("utf-8").strip() != "0"
    ):
        raise RuntimeError("9D requires independent zero exit")
    return artifact(record["log"], root)


def root_gate(record, root=ROOT, *, subphase):
    log = gate(record, root).read_text("utf-8")
    required = (
        "PASS: all active Phase 0..8 gates",
        "PASS: Phase9D lifecycle/maintenance/controlled restore gates",
        f"Completed subphase: {subphase}",
    )
    if not all(message in log for message in required):
        raise RuntimeError("9D complete current-source root evidence required")


def check(root=ROOT, *, completed=False):
    for name in REQUIRED:
        if not (root / name).is_file():
            raise RuntimeError("Missing Phase9D gate: " + name)
    matrix = json.loads((root / "docs/PHASE_9D_MATRIX.json").read_text("utf-8"))
    risks = json.loads((root / "docs/PHASE_9D_RISK_ASSESSMENT.json").read_text("utf-8"))
    if (
        risks.get("phase") != "9D"
        or risks.get("open_p0_p1") != []
        or risks.get("production_acceptable") is not False
        or {row["id"] for row in risks["risks"]} != {"R-06", "R-09"}
        or any(not row.get("remaining") or not row.get("tests") for row in risks["risks"])
    ):
        raise RuntimeError("9D risk/production boundaries invalid")
    if matrix.get("phase") != "9D" or matrix.get("open_p0_p1") != []:
        raise RuntimeError("9D scope/blockers invalid")
    if matrix.get("source_fingerprint") != source_fingerprint(root):
        replacement = root / "docs/PHASE_9E_MATRIX.json"
        if (root / "docs/PHASE_9F_MATRIX.json").is_file():
            replacement = root / "docs/PHASE_9F_MATRIX.json"
        if not replacement.is_file():
            raise RuntimeError("9D tested source fingerprint drift")
        from check_security_9e import revalidation

        newer = json.loads(replacement.read_text("utf-8"))
        revalidation(
            newer,
            root,
            "lifecycle_revalidation",
            source_fingerprint(root),
            "docs/PHASE_9D_MATRIX.json",
            "44 passed",
        )
    if matrix.get("production_acceptable") is not False or not matrix.get("production_blockers"):
        raise RuntimeError("9D cannot certify production deployment")
    scope = matrix["recovery_scope"]
    if (
        scope.get("synthetic_only") is not True
        or scope.get("native_postgresql") is not True
        or scope.get("authoritative_current_primary_required") is not True
        or scope.get("agent_operation_fences_required") is not True
        or scope.get("production_disaster_recovery") is not False
    ):
        raise RuntimeError("9D restore boundary invalid")
    if set(matrix["coverage"]) != COVERAGE:
        raise RuntimeError("9D lifecycle coverage incomplete")
    for references in matrix["coverage"].values():
        if not references:
            raise RuntimeError("9D coverage lacks tests")
        for reference in references:
            filename, _, function = reference.partition("::")
            path = (root / filename).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                raise RuntimeError("9D linked test missing")
            if function and f"def {function}(" not in path.read_text("utf-8"):
                raise RuntimeError("9D test function missing")
    gate(matrix["baseline"], root)
    gate(matrix["focused"], root)
    demo = gate(matrix["demo"], root).read_text("utf-8")
    results = [json.loads(line) for line in demo.splitlines() if line.startswith("{")]
    if not results or not all(
        results[-1].get(field) is True
        for field in ("postgresql", "native_dump_restore", "original_receipt_replayed")
    ):
        raise RuntimeError("9D actual native restore demo required")
    result = results[-1]
    if (
        result.get("owners") != 2
        or result.get("maintenance_iterations", 0) < 2
        or result.get("maintenance_failures") != 0
        or result.get("deleted_memory_recalled") != 0
        or result.get("retained_owner_recalled") != 1
        or result.get("restored_artifact_files") != 0
        or result.get("production_deployed") is not False
    ):
        raise RuntimeError("9D controlled demo outcome invalid")
    if completed:
        if matrix.get("status") != "PASS":
            raise RuntimeError("9D completed marker requires PASS")
        root_gate(matrix["pre_marker"], root, subphase="9C")
    if matrix.get("acceptance_state") == "closed":
        root_gate(matrix["post_marker"], root, subphase="9D")
        if matrix["pre_marker"]["log"]["path"] == matrix["post_marker"]["log"]["path"]:
            raise RuntimeError("9D independent pre/post processes required")


if __name__ == "__main__":
    check()
    print("PASS: Phase9D primary lifecycle/periodic maintenance/native controlled restore gates")
