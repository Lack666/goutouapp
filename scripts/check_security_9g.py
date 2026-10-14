"""9G current-source audit; preserve historical evidence and conservative closure."""

import hashlib
import io
import json
import subprocess
import tarfile
from functools import lru_cache
from pathlib import Path

from check_security_9b import mobile_fingerprint
from check_security_9c import source_fingerprint as admission_fingerprint
from check_security_9d import source_fingerprint as lifecycle_fingerprint
from check_security_9e import source_fingerprint as erasure_fingerprint
from check_security_9f import source_fingerprint as integration_fingerprint

ROOT = Path(__file__).resolve().parents[1]
BASELINE_COMMIT = "64afd5dcb37001193bed7838ca2d53d45c4ecbb7"
REQUIRED = (
    "docs/PHASE_9G_ACCEPTANCE.md",
    "docs/PHASE_9G_MATRIX.json",
    "docs/PHASE_9_EXIT_CRITERIA_MATRIX.json",
    "docs/AGENT_RUN_RECOVERY.md",
    "docs/AGENT_UNTRUSTED_INPUT.md",
    "docs/PHASE_9G_PRODUCTION_RISKS.json",
    "docs/adr/0042-audit-source-binding-and-unresolved-run-recovery.md",
    "apps/server/tests/test_security_priority_9g.py",
    "apps/server/tests/test_reliability_9g.py",
    "tests/test_security_9g_tooling.py",
)


def content_digest(name, raw):
    if Path(name).suffix in {".py", ".ts", ".tsx", ".json", ".yaml", ".toml", ".lock", ".md"}:
        raw = raw.replace(b"\r\n", b"\n")
    return hashlib.sha256(raw).hexdigest()


def digest(path):
    return content_digest(path.name, path.read_bytes())


@lru_cache(maxsize=4)
def committed_runtime_files(root):
    """Independently reconstruct immutable executable hashes from actual Git objects."""
    pinned = {
        "pyproject.toml",
        "uv.lock",
        "pnpm-lock.yaml",
        "apps/mobile/package.json",
        "scripts/phase8_android_demo.py",
        "scripts/phase8_native_closeout.py",
        "scripts/phase9b_android_smoke.py",
    }
    try:
        result = subprocess.run(
            [
                "git",
                "-c",
                f"safe.directory={root.as_posix()}",
                "archive",
                BASELINE_COMMIT,
                "apps/server",
                "apps/mobile/src",
                "apps/mobile/app",
                "scripts/native",
                *sorted(pinned),
            ],
            cwd=root,
            capture_output=True,
            check=True,
            timeout=30,
        )
        hashes = {}
        with tarfile.open(fileobj=io.BytesIO(result.stdout)) as archive:
            for member in archive:
                name = member.name
                if not member.isfile():
                    continue
                if (
                    name in pinned
                    or name.startswith(("apps/mobile/src/", "apps/mobile/app/", "scripts/native/"))
                    or (
                        name.endswith(".py")
                        and name.startswith(("apps/server/app/", "apps/server/alembic/"))
                    )
                    or (
                        name.startswith("apps/server/")
                        and name.endswith(".py")
                        and len(Path(name).parts) == 3
                    )
                ):
                    hashes[name] = content_digest(name, archive.extractfile(member).read())
        return hashes
    except (OSError, subprocess.SubprocessError, tarfile.TarError):
        raise RuntimeError("9G immutable Git executable provenance unavailable") from None


def runtime_files(root):
    paths = list((root / "apps/server/app").rglob("*.py"))
    paths += list((root / "apps/server/alembic").rglob("*.py"))
    paths += list((root / "apps/server").glob("*.py"))
    paths += [
        root / name
        for name in (
            "pyproject.toml",
            "uv.lock",
            "pnpm-lock.yaml",
            "apps/mobile/package.json",
            "scripts/phase8_android_demo.py",
            "scripts/phase8_native_closeout.py",
            "scripts/phase9b_android_smoke.py",
        )
    ]
    for folder in ("apps/mobile/src", "apps/mobile/app", "scripts/native"):
        paths += [p for p in (root / folder).rglob("*") if p.is_file()]
    return {p.relative_to(root).as_posix(): digest(p) for p in sorted(paths)}


def source_fingerprint(root=ROOT):
    paths = []
    for folder in ("apps/server", "tests", "scripts", "evals"):
        paths += list((root / folder).rglob("*.py"))
    hashes = {p.relative_to(root).as_posix(): digest(p) for p in sorted(paths)}
    hashes.update(runtime_files(root))
    for name in (
        "docs/AGENT_RUN_RECOVERY.md",
        "docs/AGENT_UNTRUSTED_INPUT.md",
        "docs/adr/0042-audit-source-binding-and-unresolved-run-recovery.md",
    ):
        hashes[name] = digest(root / name)
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()


def artifact(descriptor, root=ROOT):
    path = (root / descriptor["path"]).resolve()
    if not path.is_relative_to((root / "docs/evidence/phase9g").resolve()) or not path.is_file():
        raise RuntimeError("9G evidence missing or outside phase9g")
    if hashlib.sha256(path.read_bytes()).hexdigest() != descriptor["sha256"]:
        raise RuntimeError("9G evidence hash mismatch")
    return path


def gate(record, root=ROOT):
    if (
        record.get("exit_code") != 0
        or artifact(record["exit"], root).read_text("utf-8").strip() != "0"
    ):
        raise RuntimeError("9G independent zero exit required")
    source = json.loads(artifact(record["source"], root).read_text("utf-8"))
    if source.get("source_fingerprint") != source_fingerprint(root) or source.get("exit_code") != 0:
        raise RuntimeError("9G execution-time source fingerprint drift")
    log = artifact(record["log"], root)
    if source.get("log_sha256") != record["log"]["sha256"]:
        raise RuntimeError("9G capture/log binding mismatch")
    return log.read_text("utf-8")


def prior_9f(root=ROOT):
    """Permit historical native scenes only when ALL executable inputs are identical.

    Tests/tooling-only changes require fresh full service regressions, but cannot
    relabel an old native execution as a new Android run.
    """
    matrix = json.loads((root / "docs/PHASE_9G_MATRIX.json").read_text("utf-8"))
    prior = matrix["historical_native"]
    baseline = json.loads(artifact(prior["runtime_manifest"], root).read_text("utf-8"))
    if baseline.get("commit") != "64afd5d" or baseline.get("files") != runtime_files(root):
        raise RuntimeError("9G historical native executable source drift: fresh Android required")
    if baseline["files"] != committed_runtime_files(root):
        raise RuntimeError("9G updated manifest differs from Git: fresh Android required")
    historical = root / "docs/PHASE_9F_MATRIX.json"
    if prior.get("historical_matrix_sha256") != digest(historical):
        raise RuntimeError("9G historical 9F matrix hash drift")
    old = json.loads(historical.read_text("utf-8"))
    if mobile_fingerprint(root) != old["native"]["mobile_fingerprint"]:
        raise RuntimeError("9G historical Mobile source drift")
    baseline_log = artifact(matrix["baseline"]["log"], root).read_text("utf-8")
    if (
        matrix["baseline"]["exit_code"] != 0
        or artifact(matrix["baseline"]["exit"], root).read_text("utf-8").strip() != "0"
        or "761 passed" not in baseline_log
        or "396 passed" not in baseline_log
        or "PASS: all active Phase 0..8 gates" not in baseline_log
    ):
        raise RuntimeError("9G complete original-source baseline required")
    from check_security_9e import revalidation

    revalidation(
        matrix,
        root,
        "integration_revalidation",
        integration_fingerprint(root),
        "docs/PHASE_9F_MATRIX.json",
        "7 passed",
    )
    return old


def root_gate(record, root, subphase):
    log = gate(record, root)
    source = json.loads(artifact(record["source"], root).read_text("utf-8"))
    if source["phase_marker"] != {"completed_phase": 8, "completed_subphase": subphase}:
        raise RuntimeError("9G root marker provenance mismatch")
    for value in (
        "PASS: all active Phase 0..8 gates",
        "PASS: Phase9F Mobile self-service erasure gates",
        "PASS: Phase9G safety/reliability audit gates",
        f"Completed subphase: {subphase}",
        "396 passed",
        "810 passed",
        "Ran 99 tests",
        "21/21 checks passed",
        "22 passed",
        "2 passed",
    ):
        if value not in log:
            raise RuntimeError("9G complete root regression evidence required")


def check(root=ROOT, *, completed=False):
    for name in REQUIRED:
        if not (root / name).is_file():
            raise RuntimeError("Missing Phase9G gate: " + name)
    matrix = json.loads((root / "docs/PHASE_9G_MATRIX.json").read_text("utf-8"))
    if matrix.get("phase") != "9G" or matrix.get("source_fingerprint") != source_fingerprint(root):
        raise RuntimeError("9G tested source fingerprint drift")
    if matrix.get("open_p0_p1") != [] or matrix.get("production_acceptable") is not False:
        raise RuntimeError("9G blockers/production boundary invalid")
    if matrix.get("phase9_overall") != "IN PROGRESS" or not matrix.get("phase9_blockers"):
        raise RuntimeError("9G cannot waive unfinished Phase9 closure prerequisites")
    criteria = json.loads((root / "docs/PHASE_9_EXIT_CRITERIA_MATRIX.json").read_text("utf-8"))
    if (
        criteria.get("phase9_overall") != "IN PROGRESS"
        or criteria.get("public_production_readiness") != "NOT APPROVED"
    ):
        raise RuntimeError("9G exit matrix cannot certify unfinished closure")
    expected = {
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
    if {r["id"] for r in criteria["requirements"]} != expected or len(
        criteria["requirements"]
    ) != len(expected):
        raise RuntimeError("9G original exit criteria traceability incomplete")
    for row in criteria["requirements"]:
        if type(row.get("blocks_phase9")) is not bool or row.get("status") not in {
            "PASS",
            "PARTIAL",
            "IN PROGRESS",
        }:
            raise RuntimeError("9G exit criteria status invalid")
        for field in (
            "requirement",
            "implementation",
            "tests",
            "evidence",
            "status",
            "remaining",
            "blocks_phase9",
        ):
            if field not in row or (field != "blocks_phase9" and not row[field]):
                raise RuntimeError("9G exit criteria row incomplete")
        for reference in row["implementation"] + row["tests"]:
            name, _, function = reference.partition("::")
            path = (root / name).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                raise RuntimeError("9G linked implementation/test missing")
            if function and f"def {function}(" not in path.read_text("utf-8"):
                raise RuntimeError("9G linked test function missing")
        for evidence in row["evidence"]:
            gate(matrix[evidence], root)
    if not any(
        row["blocks_phase9"] and row["status"] != "PASS" for row in criteria["requirements"]
    ):
        raise RuntimeError("9G retained Phase9 blockers must be explicit")
    risks = json.loads((root / "docs/PHASE_9G_PRODUCTION_RISKS.json").read_text("utf-8"))
    expected_risks = {
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
    }
    if (
        risks.get("production_acceptable") is not False
        or {row["id"] for row in risks["risks"]} != expected_risks
        or len(risks["risks"]) != len(expected_risks)
    ):
        raise RuntimeError("9G production risk audit incomplete")
    for row in risks["risks"]:
        if not all(
            row.get(f)
            for f in (
                "id",
                "implementation_state",
                "validation_state",
                "remaining",
                "responsible_stage",
                "acceptance_condition",
            )
        ):
            raise RuntimeError("9G production risk status incomplete")
    from check_security_9e import revalidation

    for name, fingerprint, original, count in (
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
        revalidation(matrix, root, name, fingerprint, original, count)
    prior_9f(root)
    if "49 passed" not in gate(matrix["focused"], root):
        raise RuntimeError("9G actual focused regression required")
    if completed:
        if matrix.get("status") != "PASS":
            raise RuntimeError("9G marker requires PASS")
        root_gate(matrix["pre_marker"], root, "9F")
    if matrix.get("acceptance_state") == "closed":
        root_gate(matrix["post_marker"], root, "9G")
        if matrix["pre_marker"]["log"]["path"] == matrix["post_marker"]["log"]["path"]:
            raise RuntimeError("9G independent pre/post processes required")


if __name__ == "__main__":
    check()
    print("PASS: Phase9G safety/reliability audit gates")
