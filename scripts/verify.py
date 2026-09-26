"""Portable phase-aware equivalent of the repository Make targets."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE = json.loads((ROOT / "project-phase.json").read_text(encoding="utf-8"))["completed_phase"]


def run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def doctor() -> None:
    print(f"Python {sys.version.split()[0]}")
    if sys.version_info < (3, 12):
        raise RuntimeError("Python 3.12+ is required")
    for name in ("git", "uv", "node", "pnpm"):
        location = shutil.which(name)
        if not location:
            raise RuntimeError(f"Required tool missing: {name}")
        version = subprocess.run([location, "--version"], capture_output=True, text=True, check=True).stdout.strip()
        print(f"{name}: {version} ({location})")
    print(f"make: {shutil.which('make') or 'use make.cmd on Windows'}")
    docker = shutil.which("docker")
    if docker:
        version = subprocess.run([docker, "--version"], capture_output=True, text=True, check=True).stdout.strip()
        print(f"docker: {version} ({docker})")
    else:
        print("docker: MISSING (required for Phase 2 PostgreSQL demo)")
    print(f"Completed phase: {PHASE}")


def tests() -> None:
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    run([sys.executable, "knowledge/goutoujunshi/scripts/validate_skill.py"])


def evals() -> None:
    if PHASE < 1:
        print("DEFERRED: golden evaluation gate begins at Phase 1")
        return
    run([sys.executable, "evals/validate.py"])


def repository_checks() -> None:
    safe_directory = f"safe.directory={ROOT.as_posix()}"
    tracked = subprocess.run(
        ["git", "-c", safe_directory, "ls-files", "-z"],
        cwd=ROOT, capture_output=True, check=True,
    ).stdout.decode("utf-8", errors="surrogateescape").split("\0")
    forbidden = [name for name in tracked if Path(name).name.startswith(".env") and Path(name).name != ".env.example"]
    if forbidden:
        raise RuntimeError("Tracked environment secret file found: " + ", ".join(forbidden))
    if not (ROOT / ".env.example").is_file():
        raise RuntimeError("Missing .env.example")
    for name in (".env", ".env.local"):
        ignored = subprocess.run(
            ["git", "-c", safe_directory, "check-ignore", "-q", "--", name],
            cwd=ROOT, check=False,
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
    if PHASE < 2:
        print("DEFERRED: backend lint/tests and Docker validation begin at Phase 2")
    if PHASE < 3:
        print("DEFERRED: executable Agent and behavioral eval begin at Phase 3")
    if PHASE < 7:
        print("DEFERRED: mobile lint/typecheck begin at Phase 7")
    if PHASE >= 2:
        raise RuntimeError("Later-phase verification is not implemented; do not mark that phase complete")
    print(f"PASS: all active Phase 0..{PHASE} gates")


def dev() -> None:
    if PHASE < 2:
        raise RuntimeError("No development service exists before Phase 2")
    raise RuntimeError("Development service launcher not yet implemented")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", choices=("doctor", "dev", "test", "eval", "verify"))
    args = parser.parse_args()
    try:
        {"doctor": doctor, "dev": dev, "test": tests, "eval": evals, "verify": verify}[args.target]()
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
