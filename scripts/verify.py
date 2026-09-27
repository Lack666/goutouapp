"""Portable phase-aware equivalent of the repository Make targets."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE_STATE = json.loads((ROOT / "project-phase.json").read_text(encoding="utf-8"))
PHASE = PHASE_STATE["completed_phase"]
SUBPHASE = PHASE_STATE.get("completed_subphase")
BACKEND_FOUNDATION = PHASE >= 2 or SUBPHASE in {"2A", "2B", "2C", "2D"}
DATABASE_FOUNDATION = PHASE >= 2 or SUBPHASE in {"2B", "2C", "2D"}
LLM_FOUNDATION = PHASE >= 2 or SUBPHASE in {"2C", "2D"}
INTEGRATION_FOUNDATION = PHASE >= 2 or SUBPHASE == "2D"
AGENT_CONTRACTS = PHASE >= 3 or SUBPHASE in {"3A", "3B", "3C"}
AGENT_RUNTIME = PHASE >= 3 or SUBPHASE in {"3B", "3C"}
AGENT_SEMANTIC = PHASE >= 3 or SUBPHASE == "3C"


def run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def doctor() -> None:
    print(f"Python {sys.version.split()[0]}")
    if sys.version_info < (3, 12):  # noqa: UP036 - doctor checks before uv starts
        raise RuntimeError("Python 3.12+ is required")
    for name in ("git", "uv", "node", "pnpm"):
        location = shutil.which(name)
        if not location:
            raise RuntimeError(f"Required tool missing: {name}")
        version = subprocess.run(
            [location, "--version"], capture_output=True, text=True, check=True
        ).stdout.strip()
        print(f"{name}: {version} ({location})")
    print(f"make: {shutil.which('make') or 'use make.cmd on Windows'}")
    docker = shutil.which("docker")
    if docker:
        version = subprocess.run(
            [docker, "--version"], capture_output=True, text=True, check=True
        ).stdout.strip()
        print(f"docker: {version} ({docker})")
    else:
        print("docker: MISSING (required for Phase 2B PostgreSQL demo)")
    print(f"Completed phase: {PHASE}")
    if SUBPHASE:
        print(f"Completed subphase: {SUBPHASE}")


def uv_run(*args: str) -> None:
    command = ["uv", "--cache-dir", str(ROOT / ".cache" / "uv")]
    if sys.platform == "win32":
        command.append("--no-managed-python")
    command.extend(["run", "--locked"])
    if (ROOT / ".env").is_file():
        command.extend(["--env-file", ".env"])
    run([*command, *args])


def tests() -> None:
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    run([sys.executable, "knowledge/goutoujunshi/scripts/validate_skill.py"])
    if DATABASE_FOUNDATION:
        uv_run("python", "scripts/check_db_migrations.py")
    if LLM_FOUNDATION:
        uv_run(
            "pytest",
            "-q",
            "apps/server/tests/test_llm_mock.py",
            "apps/server/tests/test_llm_openai_compatible.py",
        )
    if INTEGRATION_FOUNDATION:
        uv_run("pytest", "-q", "apps/server/tests/test_backend_integration.py")
    if AGENT_CONTRACTS:
        uv_run("pytest", "-q", "apps/server/tests/test_agent_contracts.py")
    if AGENT_RUNTIME:
        uv_run("pytest", "-q", "apps/server/tests/test_agent_runtime.py")
    if AGENT_SEMANTIC:
        uv_run("pytest", "-q", "apps/server/tests/test_agent_semantic.py")
    if BACKEND_FOUNDATION:
        uv_run("pytest", "-q", "apps/server/tests")


def lint() -> None:
    if not BACKEND_FOUNDATION:
        print("DEFERRED: backend lint begins at Phase 2A")
        return
    uv_run(
        "ruff",
        "check",
        "apps/server",
        "evals/phase3c_semantic.py",
        "scripts/verify.py",
        "scripts/check_db_migrations.py",
    )
    uv_run(
        "ruff",
        "format",
        "--check",
        "apps/server",
        "evals/phase3c_semantic.py",
        "scripts/verify.py",
        "scripts/check_db_migrations.py",
    )


def evals() -> None:
    if PHASE < 1:
        print("DEFERRED: golden evaluation gate begins at Phase 1")
        return
    run([sys.executable, "evals/validate.py"])


def repository_checks() -> None:
    safe_directory = f"safe.directory={ROOT.as_posix()}"
    tracked = (
        subprocess.run(
            ["git", "-c", safe_directory, "ls-files", "-z"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        )
        .stdout.decode("utf-8", errors="surrogateescape")
        .split("\0")
    )
    forbidden = [
        name
        for name in tracked
        if Path(name).name.startswith(".env") and Path(name).name != ".env.example"
    ]
    if forbidden:
        raise RuntimeError("Tracked environment secret file found: " + ", ".join(forbidden))
    if not (ROOT / ".env.example").is_file():
        raise RuntimeError("Missing .env.example")
    for name in (".env", ".env.local"):
        ignored = subprocess.run(
            ["git", "-c", safe_directory, "check-ignore", "-q", "--", name],
            cwd=ROOT,
            check=False,
        )
        if ignored.returncode != 0:
            raise RuntimeError(f"Git does not ignore {name}")
    mobile = ROOT / "apps" / "mobile"
    if mobile.exists():
        for path in mobile.rglob("*"):
            if path.is_file() and path.suffix in {".ts", ".tsx", ".js", ".json"}:
                content = path.read_text(encoding="utf-8")
                if "EXPO_PUBLIC_OPENAI" in content or "EXPO_PUBLIC_DEEPSEEK" in content:
                    raise RuntimeError(f"Model key prefix in mobile: {path}")
    print("Repository secret boundary check passed")


def verify() -> None:
    doctor()
    tests()
    evals()
    repository_checks()
    lint()
    if DATABASE_FOUNDATION:
        print("PASS: PostgreSQL migration and integration gate")
    elif BACKEND_FOUNDATION:
        print("DEFERRED: PostgreSQL models, migrations and Docker demo begin at Phase 2B")
    else:
        print("DEFERRED: backend foundation begins at Phase 2A")
    if LLM_FOUNDATION:
        print("PASS: LLM Provider unit gate")
    if INTEGRATION_FOUNDATION:
        print("PASS: Backend integration smoke gate")
    if AGENT_CONTRACTS:
        print("PASS: Agent contracts and Golden schema compatibility gate")
    if AGENT_RUNTIME:
        print("PASS: Minimal standalone LangGraph runtime gate")
    else:
        print("DEFERRED: Minimal LangGraph runtime")
    if AGENT_SEMANTIC:
        print("PASS: Safety, Scenario and FIU node/24-case replay gate")
    else:
        print("DEFERRED: Safety, Scenario and FIU semantic nodes")
    print("DEFERRED: Full relationship reasoning, knowledge router and full Golden runtime eval")
    if PHASE < 7:
        print("DEFERRED: Mobile lint/typecheck begin at Phase 7")
    if PHASE > 2:
        raise RuntimeError(
            "Later-phase verification is not implemented; do not mark that phase complete"
        )
    if PHASE == 2:
        print("PASS: Phase 2 Backend Foundation")
        if AGENT_CONTRACTS:
            print("PASS: Phase 3A Agent State and Runtime Contracts")
            if AGENT_RUNTIME:
                print("PASS: Phase 3B Minimal Standalone LangGraph Runtime")
                if AGENT_SEMANTIC:
                    print("PASS: Phase 3C Safety, Scenario and FIU Semantic Nodes")
                    print("PASS: all active Phase 0..2 and 3A..3C gates")
                else:
                    print("PASS: all active Phase 0..2 and 3A..3B gates")
            else:
                print("PASS: all active Phase 0..2 and 3A gates")
        else:
            print("PASS: all active Phase 0..2 gates")
        return
    passed = f"Phase 0..{PHASE}"
    if BACKEND_FOUNDATION:
        passed += " and Phase 2A"
    if DATABASE_FOUNDATION:
        passed += " and Phase 2B"
    if LLM_FOUNDATION:
        passed += " and Phase 2C"
    print(f"PASS: all active {passed} gates")


def dev() -> None:
    if not BACKEND_FOUNDATION:
        raise RuntimeError("No development service exists before Phase 2A")
    uv_run("python", "apps/server/run.py")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", choices=("doctor", "dev", "test", "lint", "eval", "verify"))
    args = parser.parse_args()
    try:
        {
            "doctor": doctor,
            "dev": dev,
            "test": tests,
            "lint": lint,
            "eval": evals,
            "verify": verify,
        }[args.target]()
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
