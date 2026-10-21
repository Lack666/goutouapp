"""Immutable full-process evidence for Phase 9H; credentials stay in private pipes."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fingerprint(root=ROOT):
    files = []
    for folder in (
        "apps/server",
        "apps/mobile/src",
        "apps/mobile/app",
        "apps/mobile/tests",
        "apps/mobile/connected",
        "apps/mobile/agent-connected",
        "apps/mobile/import-connected",
        "apps/mobile/memory-connected",
        "apps/mobile/final-connected",
        "apps/mobile/erasure-connected",
        "scripts",
        "tests",
        "tools",
    ):
        files.extend(
            p
            for p in (root / folder).rglob("*")
            if p.is_file()
            and p.suffix in {".py", ".ts", ".tsx", ".mjs", ".json"}
            and not {"__pycache__", "node_modules", ".cache"}.intersection(p.parts)
        )
    files.extend(
        root / p
        for p in ("pyproject.toml", "uv.lock", "pnpm-lock.yaml", "apps/mobile/package.json")
    )
    files.extend((root / "apps/mobile").glob("*.ts"))
    files.extend((root / "apps/mobile").glob("*.json"))
    files.extend((root / "docs/adr").glob("*.md"))
    files.append(root / "docs/contracts/openapi.json")
    files.extend(
        root / name
        for name in (
            "docs/DATA_DELETION_CONTRACT.md",
            "docs/DATA_DELETION_MATRIX.json",
            "docs/DATA_LIFECYCLE_INVENTORY.md",
            "docs/BACKUP_RESTORE_POLICY.md",
            "docs/AGENT_RUN_RECOVERY.md",
            "docs/RETENTION_MAINTENANCE.md",
            "docs/SECURITY_THREAT_MODEL.md",
            "docs/SECURITY_RISK_REGISTER.md",
            "docs/AUTHENTICATION.md",
            "docs/IDEMPOTENCY.md",
            "docs/MOBILE_DATA_ERASURE.md",
        )
    )
    hashes = {
        p.relative_to(root).as_posix(): hashlib.sha256(
            p.read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
        for p in sorted(set(files))
    }
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not args.name.replace("-", "").replace("_", "").isalnum() or not args.command:
        parser.error("Opaque evidence name and command required")
    folder = ROOT / "docs/evidence/phase9h"
    folder.mkdir(parents=True, exist_ok=True)
    log = folder / (args.name + ".log")
    if log.exists():
        parser.error("Evidence is immutable")
    env = os.environ.copy()
    env.update(
        PYTHONUTF8="1",
        PYTHONUNBUFFERED="1",
        TEST_DATABASE_URL="postgresql+psycopg://postgres@127.0.0.1:15434/goutou_test",
        DATABASE_URL="postgresql+psycopg://postgres@127.0.0.1:15434/goutou_dev",
        PLAYWRIGHT_CHROME_PATH=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        PYTEST_ADDOPTS=(
            f"--basetemp=.cache/phase9h-{args.name} -o cache_dir=.cache/phase9h-cache-{args.name}"
        ),
    )
    env["PATH"] = r"C:\Windows\System32;" + env.get("PATH", "")
    source = {
        "source_fingerprint": fingerprint(),
        "phase_marker": json.loads((ROOT / "project-phase.json").read_text("utf-8")),
        "synthetic_only": True,
        "command": args.command,
    }
    with log.open("wb") as stream:
        command = args.command
        executable = shutil.which(command[0])
        if os.name == "nt" and executable and Path(executable).suffix.lower() in {".cmd", ".bat"}:
            command = [
                os.environ.get("COMSPEC", r"C:\Windows\System32\cmd.exe"),
                "/d",
                "/c",
                executable,
                *command[1:],
            ]
        try:
            code = subprocess.run(
                command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT
            ).returncode
        except OSError:
            stream.write(b"Evidence command could not start.\n")
            code = 127
    (folder / (args.name + ".exit")).write_text(str(code) + "\n", "utf-8")
    source.update(
        exit_code=code,
        log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),
        end_source_fingerprint=fingerprint(),
    )
    (folder / (args.name + ".source.json")).write_text(json.dumps(source, indent=2) + "\n", "utf-8")
    print(json.dumps({"name": args.name, "exit_code": code}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
