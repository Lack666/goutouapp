"""Capture complete process output, exit and source binding without printing credentials."""

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

from check_security_9g import source_fingerprint

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not args.name.replace("-", "").replace("_", "").isalnum() or not args.command:
        parser.error("An opaque evidence name and command are required")
    folder = ROOT / "docs/evidence/phase9g"
    folder.mkdir(parents=True, exist_ok=True)
    log, exit_file = folder / (args.name + ".log"), folder / (args.name + ".exit")
    if log.exists() or exit_file.exists():
        parser.error("Existing evidence is immutable; choose another name")
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    # Repository's documented loopback-only disposable namespaces, no private rows.
    env["TEST_DATABASE_URL"] = "postgresql+psycopg://postgres@127.0.0.1:15434/goutou_test"
    env["DATABASE_URL"] = "postgresql+psycopg://postgres@127.0.0.1:15434/goutou_dev"
    env["PATH"] = r"C:\Windows\System32;" + env.get("PATH", "")
    env["PLAYWRIGHT_CHROME_PATH"] = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    env["PYTEST_ADDOPTS"] = (
        f"--basetemp=.cache/phase9g-{args.name} -o cache_dir=.cache/phase9g-cache-{args.name}"
    )
    provenance = {
        "source_fingerprint": source_fingerprint(ROOT),
        "phase_marker": json.loads((ROOT / "project-phase.json").read_text("utf-8")),
        "git_head": subprocess.check_output(
            ["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "HEAD"], cwd=ROOT
        )
        .decode()
        .strip(),
        "synthetic_only": True,
    }
    with log.open("wb") as stream:
        try:
            code = subprocess.run(
                args.command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT
            ).returncode
        except OSError:
            stream.write(b"FAIL: evidence process could not start\n")
            code = 1
    exit_file.write_text(str(code) + "\n", "utf-8")
    provenance.update(exit_code=code, log_sha256=hashlib.sha256(log.read_bytes()).hexdigest())
    (folder / (args.name + ".source.json")).write_text(
        json.dumps(provenance, indent=2) + "\n", "utf-8"
    )
    print(
        json.dumps({"name": args.name, "exit_code": code, "log_sha256": provenance["log_sha256"]})
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
