"""9A deliverable and risk validation, without weakening completed phase gates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "docs/SECURITY_THREAT_MODEL.md",
    "docs/UPLOAD_SECURITY_BOUNDARY.md",
    "docs/SECURITY_RISK_REGISTER.md",
    "docs/SECURITY_RISK_REGISTER.json",
    "docs/PHASE_9A_ACCEPTANCE.md",
    "docs/adr/0036-upload-security-and-private-error-logs.md",
    "apps/server/tests/test_upload_security.py",
    "tests/test_security_tooling.py",
    "scripts/audit_phase8_evidence.py",
)


def validate_risks(root: Path = ROOT) -> None:
    register = json.loads((root / "docs/SECURITY_RISK_REGISTER.json").read_text("utf-8"))
    if register.get("phase") != "9A" or not register.get("deployment_scope"):
        raise RuntimeError("9A risk scope missing")
    rows = register["risks"]
    if not rows or len({row["id"] for row in rows}) != len(rows):
        raise RuntimeError("9A risk IDs must be unique and nonempty")
    required = {
        "id",
        "boundary",
        "asset",
        "description",
        "severity",
        "existing_control",
        "tests",
        "status",
        "fix",
        "remaining_risk",
        "responsible_phase",
    }
    for row in rows:
        if not required <= row.keys() or not all(row[name] for name in required):
            raise RuntimeError("9A risk field missing")
        if row["severity"] not in {"P0", "P1", "P2"} or row["status"] not in {"fixed", "deferred"}:
            raise RuntimeError("9A risk classification invalid")
        if row["severity"] in {"P0", "P1"} and row["status"] != "fixed":
            raise RuntimeError("9A has unresolved blocking risk")
        for test in row["tests"]:
            filename, _, function = test.partition("::")
            path = (root / filename).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                raise RuntimeError("9A risk test reference missing")
            if function and f"def {function}(" not in path.read_text("utf-8"):
                raise RuntimeError("9A risk test function missing")


def check(root: Path = ROOT, *, completed: bool = False) -> None:
    for filename in REQUIRED:
        if not (root / filename).is_file():
            raise RuntimeError("Missing Phase 9A gate: " + filename)
    validate_risks(root)
    if not completed:
        return
    evidence = json.loads((root / "docs/PHASE_9A_MATRIX.json").read_text("utf-8"))
    if evidence.get("phase") != "9A" or evidence.get("status") != "PASS":
        raise RuntimeError("9A completed marker requires PASS evidence")
    if evidence.get("open_p0_p1") != []:
        raise RuntimeError("9A completed marker has blocking findings")
    for name in ("focused", "pre_marker"):
        gate = evidence[name]
        if gate["exit_code"] != 0:
            raise RuntimeError("9A requires independent zero exit evidence")
        for field in ("log", "exit"):
            descriptor = gate[field]
            path = (root / descriptor["path"]).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                raise RuntimeError("9A evidence missing or outside repository")
            if hashlib.sha256(path.read_bytes()).hexdigest() != descriptor["sha256"]:
                raise RuntimeError("9A evidence hash mismatch")
            if field == "exit" and path.read_text("utf-8").strip() != "0":
                raise RuntimeError("9A evidence exit is not zero")


if __name__ == "__main__":
    check()
    print("PASS: Phase 9A security documents, risks and linked test coverage")
