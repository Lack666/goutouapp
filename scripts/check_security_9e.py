"""9E needs current-source real erasure/maintenance/restore and independent exits."""

import hashlib
import json
from pathlib import Path

from check_security_9b import mobile_fingerprint, native_check
from check_security_9c import source_fingerprint as admission_fingerprint
from check_security_9d import source_fingerprint as lifecycle_fingerprint

ROOT = Path(__file__).resolve().parents[1]
COVERAGE = {
    "dataset",
    "conversation",
    "associations",
    "account_gap",
    "confirmation",
    "replay",
    "changed_target",
    "owner",
    "history_cursor",
    "import_replay",
    "agent_replay",
    "memory",
    "restore",
    "missing_primary",
    "maintenance",
    "backup",
    "privacy",
    "mobile",
    "native_regression",
    "quota",
}
REQUIRED = (
    "docs/PHASE_9E_ACCEPTANCE.md",
    "docs/PHASE_9E_RISK_ASSESSMENT.json",
    "docs/PHASE_9E_MATRIX.json",
    "docs/DATA_DELETION_MATRIX.json",
    "docs/DATA_DELETION_CONTRACT.md",
    "docs/DATA_LIFECYCLE_INVENTORY.md",
    "docs/BACKUP_RESTORE_POLICY.md",
    "docs/RETENTION_MAINTENANCE.md",
    "docs/adr/0040-guarded-dataset-and-conversation-erasure.md",
    "apps/server/app/services/erasure.py",
    "apps/server/app/api/v1/erasure.py",
    "apps/server/app/db/models/erasure.py",
    "apps/server/app/schemas/erasure.py",
    "apps/server/alembic/versions/20261013_02_guarded_erasure.py",
    "apps/server/tests/test_erasure.py",
    "apps/server/erasure_demo.py",
    "tests/test_security_9e_tooling.py",
)


def source_fingerprint(root=ROOT):
    names = (
        "scripts/check_security_9e.py",
        "scripts/check_security_9b.py",
        "scripts/check_security_9d.py",
        "scripts/audit_authorization.py",
        "scripts/export_openapi.py",
        "scripts/check_db_migrations.py",
        "apps/server/erasure_demo.py",
        "scripts/phase8_android_demo.py",
        "scripts/phase9b_android_smoke.py",
        "tools/api-codegen/generate-api.mjs",
        "tests/test_security_9e_tooling.py",
    )
    hashes = {
        name: hashlib.sha256((root / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        for name in names
    }
    hashes.update(admission=admission_fingerprint(root), mobile=mobile_fingerprint(root))
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()


def artifact(descriptor, root=ROOT):
    path = (root / descriptor["path"]).resolve()
    if not path.is_relative_to((root / "docs/evidence/phase9e").resolve()) or not path.is_file():
        raise RuntimeError("9E evidence missing or outside phase9e")
    if hashlib.sha256(path.read_bytes()).hexdigest() != descriptor["sha256"]:
        raise RuntimeError("9E evidence hash mismatch")
    return path


def gate(record, root=ROOT):
    if (
        record.get("exit_code") != 0
        or artifact(record["exit"], root).read_text("utf-8").strip() != "0"
    ):
        raise RuntimeError("9E independent zero exit required")
    return artifact(record["log"], root).read_text("utf-8")


def revalidation(matrix, root, name, fingerprint, original, expected):
    record = matrix.get(name, {})
    # A later phase supplies new evidence without modifying the historical matrix.
    if matrix.get("phase") == "9E" and record.get("source_fingerprint") != fingerprint:
        replacement = root / "docs/PHASE_9F_MATRIX.json"
        if replacement.is_file():
            return revalidation(
                json.loads(replacement.read_text("utf-8")),
                root,
                name,
                fingerprint,
                original,
                expected,
            )
    original_hash = hashlib.sha256(
        (root / original).read_bytes().replace(b"\r\n", b"\n")
    ).hexdigest()
    if (
        matrix.get("phase") not in {"9E", "9F"}
        or record.get("source_fingerprint") != fingerprint
        or record.get("historical_matrix_sha256") != original_hash
    ):
        raise RuntimeError("9E current-source regression fingerprint drift")
    if matrix.get("phase") == "9F":
        from check_security_9f import gate as evidence_gate
    else:
        evidence_gate = gate
    if expected not in evidence_gate(record, root):
        raise RuntimeError("9E complete prior regression required")


def root_gate(record, root, subphase):
    log = gate(record, root)
    if not all(
        message in log
        for message in (
            "PASS: all active Phase 0..8 gates",
            "PASS: Phase9D lifecycle/maintenance/controlled restore gates",
            "PASS: Phase9E guarded dataset/conversation erasure gates",
            f"Completed subphase: {subphase}",
        )
    ):
        raise RuntimeError("9E complete current-source root evidence required")


def check(root=ROOT, *, completed=False):
    for name in REQUIRED:
        if not (root / name).is_file():
            raise RuntimeError("Missing Phase9E gate: " + name)
    matrix = json.loads((root / "docs/PHASE_9E_MATRIX.json").read_text("utf-8"))
    risks = json.loads((root / "docs/PHASE_9E_RISK_ASSESSMENT.json").read_text("utf-8"))
    if matrix.get("phase") != "9E" or matrix.get("open_p0_p1") != []:
        raise RuntimeError("9E scope/blockers invalid")
    changed_source = matrix.get("source_fingerprint") != source_fingerprint(root)
    if changed_source:
        replacement = root / "docs/PHASE_9F_MATRIX.json"
        if not replacement.is_file():
            raise RuntimeError("9E tested source fingerprint drift")
        newer = json.loads(replacement.read_text("utf-8"))
        revalidation(
            newer,
            root,
            "erasure_revalidation",
            source_fingerprint(root),
            "docs/PHASE_9E_MATRIX.json",
            "39 passed",
        )
    if (
        matrix.get("delivery") != "Backend-only"
        or matrix.get("app_self_service_erasure") is not False
    ):
        raise RuntimeError("9E cannot advertise an absent App deletion flow")
    if (
        risks.get("phase") != "9E"
        or risks.get("production_acceptable") is not False
        or risks.get("open_p0_p1") != []
        or {r["id"] for r in risks["risks"]} != {"R-06", "R-07", "R-08", "R-09"}
    ):
        raise RuntimeError("9E production risk boundaries invalid")
    for risk in risks["risks"]:
        for field in (
            "status",
            "controls",
            "tests",
            "remaining",
            "development_risk",
            "production_risk",
            "next_task",
        ):
            if not risk.get(field):
                raise RuntimeError("9E risk review incomplete")
        if risk.get("blocks_public_exposure") is not True:
            raise RuntimeError("9E production prerequisite cannot be waived")
    for field in (
        "full_account_erasure",
        "production_disaster_recovery",
        "production_scheduler",
        "independent_deletion_journal",
    ):
        if matrix.get(field) is not False:
            raise RuntimeError("9E undeployed capability claim")
    if matrix.get("authoritative_current_primary_required") is not True:
        raise RuntimeError("9E authoritative restore evidence required")
    if set(matrix["coverage"]) != COVERAGE:
        raise RuntimeError("9E coverage incomplete")
    inventory = json.loads((root / "docs/DATA_DELETION_MATRIX.json").read_text("utf-8"))
    expected_domains = {
        "account",
        "person",
        "relationship",
        "conversation",
        "agent_history",
        "dataset",
        "relationship_message",
        "memory",
    }
    fields = {
        "self_service",
        "authorized_actor",
        "confirmation",
        "affected_resources",
        "primary_rows",
        "retained_metadata",
        "import_dedup",
        "memory_effect",
        "backup_effect",
        "ui_api_limit",
    }
    if set(inventory["domains"]) != expected_domains or any(
        not fields <= set(row) for row in inventory["domains"].values()
    ):
        raise RuntimeError("9E deletion capability inventory incomplete")
    for references in matrix["coverage"].values():
        if not references:
            raise RuntimeError("9E coverage incomplete")
        for reference in references:
            filename, _, function = reference.partition("::")
            path = (root / filename).resolve()
            if (
                not path.is_relative_to(root.resolve())
                or not path.is_file()
                or (function and f"def {function}(" not in path.read_text("utf-8"))
            ):
                raise RuntimeError("9E linked test missing")
    baseline = gate(matrix["baseline"], root)
    if "715 passed" not in baseline or "363 passed" not in baseline:
        raise RuntimeError("9E original 9D baseline required")
    if "39 passed" not in gate(matrix["focused"], root):
        raise RuntimeError("9E complete erasure contract suite required")
    revalidation(
        matrix,
        root,
        "admission_revalidation",
        admission_fingerprint(root),
        "docs/PHASE_9C_MATRIX.json",
        "27 passed",
    )
    revalidation(
        matrix,
        root,
        "lifecycle_revalidation",
        lifecycle_fingerprint(root),
        "docs/PHASE_9D_MATRIX.json",
        "44 passed",
    )
    native_check(matrix, root, historical=changed_source, evidence_phase="phase9e")
    if changed_source:
        native_check(newer, root, evidence_phase="phase9f")
    results = [
        json.loads(line) for line in gate(matrix["demo"], root).splitlines() if line.startswith("{")
    ]
    if not results or not all(
        results[-1].get(k) is True
        for k in (
            "postgresql",
            "signed_http",
            "dataset_deleted",
            "conversation_deleted",
            "original_receipts_replayed",
            "native_dump_restore",
            "memory_preserved",
            "owner_b_preserved",
        )
    ):
        raise RuntimeError("9E real guarded erasure/restore demonstration required")
    if completed:
        if matrix.get("status") != "PASS":
            raise RuntimeError("9E completed marker requires PASS")
        root_gate(matrix["pre_marker"], root, "9D")
    if matrix.get("acceptance_state") == "closed":
        root_gate(matrix["post_marker"], root, "9E")
        if matrix["pre_marker"]["log"]["path"] == matrix["post_marker"]["log"]["path"]:
            raise RuntimeError("9E independent pre/post processes required")


if __name__ == "__main__":
    check()
    print("PASS: Phase9E guarded dataset/conversation erasure gates")
