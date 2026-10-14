"""9B cannot pass without fresh complete native and independent root evidence."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "docs/PHASE_9B_ACCEPTANCE.md",
    "docs/AUTHORIZATION_SECURITY_AUDIT.md",
    "docs/AUTHORIZATION_API_INVENTORY.json",
    "docs/PRIVACY_LOGGING_POLICY.md",
    "docs/PHASE_9B_RISK_ASSESSMENT.json",
    "docs/EVIDENCE_PRIVACY_REVIEW_9B.md",
    "apps/server/tests/test_authorization_security.py",
    "apps/server/tests/test_privacy_logging.py",
    "apps/mobile/tests/authPrivacy.test.ts",
    "scripts/audit_authorization.py",
    "scripts/audit_evidence_privacy.py",
    "scripts/phase9b_android_smoke.py",
    "docs/adr/0037-scoped-navigation-and-per-event-session-guards.md",
)
SCENES = {"resource_create", "sse_normal", "memory_smoke_revoke", "session", "import_history"}


def mobile_fingerprint(root=ROOT):
    paths = [root / "apps/mobile/package.json", root / "pnpm-lock.yaml"]
    for folder in ("apps/mobile/src", "apps/mobile/app"):
        paths.extend(path for path in (root / folder).rglob("*") if path.is_file())
    hashes = {
        path.relative_to(root).as_posix(): hashlib.sha256(
            path.read_bytes().replace(b"\r\n", b"\n")
            if path.suffix in {".ts", ".tsx", ".json", ".yaml"}
            else path.read_bytes()
        ).hexdigest()
        for path in sorted(paths)
    }
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()


def artifact(descriptor, root=ROOT, *, evidence_phase="phase9b"):
    path = (root / descriptor["path"]).resolve()
    if (
        not path.is_relative_to((root / "docs/evidence" / evidence_phase).resolve())
        or not path.is_file()
    ):
        raise RuntimeError("9B evidence missing or outside phase9b")
    if hashlib.sha256(path.read_bytes()).hexdigest() != descriptor["sha256"]:
        raise RuntimeError("9B evidence hash mismatch")
    return path


def native_check(matrix, root=ROOT, *, historical=False, evidence_phase="phase9b"):
    native = matrix["native"]
    if native.get("status") != "PASS" or (
        not historical and native["mobile_fingerprint"] != mobile_fingerprint(root)
    ):
        raise RuntimeError("9B requires fresh Android PASS for current source/dependencies")
    if {row["scene"] for row in native["scenes"]} != SCENES or len(native["scenes"]) != len(SCENES):
        raise RuntimeError("9B Android smoke coverage incomplete")
    if not native.get("device") or native.get("synthetic_only") is not True:
        raise RuntimeError("9B native environment/provenance missing")
    for row in native["scenes"]:
        if row["exit_code"] != 0 or row["status"] != "PASS":
            raise RuntimeError("9B native independent scene failed")
        paths = {
            name: artifact(row["artifacts"][name], root, evidence_phase=evidence_phase)
            for name in ("steps", "report", "log", "exit")
        }
        if paths["exit"].read_text("utf-8").strip() != "0":
            raise RuntimeError("9B native independent exit not zero")
        steps = json.loads(paths["steps"].read_text("utf-8"))
        report = json.loads(paths["report"].read_text("utf-8"))
        expected = [step.partition(" ")[0] for step in steps if step != "stop"]
        completed = [
            value["command"] if value.get("status") == "done" else "state"
            for value in report
            if value.get("status") == "done" or "ui_state" in value
        ]
        if report[0]["execution"]["steps"] != steps or completed != expected:
            raise RuntimeError("9B native partial/spliced scene rejected")
        if any(value.get("status") in {"FAIL", "failed"} for value in report):
            raise RuntimeError("9B native contains failed step")


def check(root=ROOT, *, completed=False):
    for filename in REQUIRED:
        if not (root / filename).is_file():
            raise RuntimeError("Missing Phase 9B gate: " + filename)
    risks = json.loads((root / "docs/PHASE_9B_RISK_ASSESSMENT.json").read_text("utf-8"))
    if risks.get("phase") != "9B" or risks.get("production_acceptable") is not False:
        raise RuntimeError("9B must preserve production deployment blockers")
    if not risks.get("production_blockers") or risks.get("open_p0_p1") != []:
        raise RuntimeError("9B has blocking findings or missing R-07 gate")
    for finding in risks.get("fixed_findings", []):
        filename, _, function = finding["test"].partition("::")
        path = root / filename
        if not path.is_file() or (function and f"def {function}(" not in path.read_text("utf-8")):
            raise RuntimeError("9B finding lacks linked regression coverage")
    matrix = json.loads((root / "docs/PHASE_9B_MATRIX.json").read_text("utf-8"))
    if matrix.get("phase") != "9B" or matrix.get("open_p0_p1") != []:
        raise RuntimeError("Invalid 9B acceptance scope/findings")
    if matrix["native"]["mobile_fingerprint"] == mobile_fingerprint(root):
        native_check(matrix, root)
    else:
        # Preserve all historical transcripts and require five NEW complete native
        # scenes on the changed generated/client source. No Web substitution.
        native_check(matrix, root, historical=True)
        replacement = root / "docs/PHASE_9E_MATRIX.json"
        evidence_phase, expected_phase = "phase9e", "9E"
        if (root / "docs/PHASE_9F_MATRIX.json").is_file():
            replacement = root / "docs/PHASE_9F_MATRIX.json"
            evidence_phase, expected_phase = "phase9f", "9F"
        if not replacement.is_file():
            raise RuntimeError("9B requires fresh Android PASS for current source/dependencies")
        newer = json.loads(replacement.read_text("utf-8"))
        original_hash = hashlib.sha256(
            (root / "docs/PHASE_9B_MATRIX.json").read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
        if (
            newer.get("phase") != expected_phase
            or newer.get("historical_native_matrix_sha256") != original_hash
        ):
            raise RuntimeError("9B native historical authority drift")
        native_check(newer, root, evidence_phase=evidence_phase)
    if not completed:
        return
    if matrix.get("status") != "PASS":
        raise RuntimeError("9B completed marker requires PASS evidence")
    for name in ("focused", "pre_marker"):
        gate = matrix[name]
        if gate["exit_code"] != 0:
            raise RuntimeError("9B requires independent zero exit evidence")
        artifact(gate["log"], root)
        if artifact(gate["exit"], root).read_text("utf-8").strip() != "0":
            raise RuntimeError("9B independent exit not zero")


if __name__ == "__main__":
    check()
    print("PASS: Phase 9B authorization/privacy/native/deployment gates")
