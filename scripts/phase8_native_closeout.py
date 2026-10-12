"""Run independent Android closeout scenes with immutable steps/logs/exit codes."""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENES = (
    "sse_normal",
    "sse_failed",
    "sse_disconnect",
    "sse_cancel",
    "sse_back_logout",
    "resource_create",
    "rest_replay",
    "owner_isolation",
    "relationship_isolation",
    "import_history_lifecycle",
    "memory_challenge",
    "memory_replay",
    "memory_restart",
    "memory_smoke_preserve",
    "memory_smoke_revoke",
    "token_expiry",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", required=True)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--scenes", nargs="+", choices=SCENES, default=SCENES)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9-]{1,40}", args.batch):
        raise ValueError("Bounded artifact batch name required")
    results = []
    for scene in args.scenes:
        base = ROOT / ".cache" / f"phase8f-{args.batch}-{scene}"
        paths = {
            name: base.with_suffix("." + name) for name in ("steps.json", "json", "log", "exit")
        }
        if any(path.exists() for path in paths.values()):
            raise ValueError("Prior independent execution evidence must not be overwritten")
        source = ROOT / "scripts/native" / f"phase8f_closeout_{scene}.json"
        steps = json.loads(source.read_text(encoding="utf-8"))
        if steps[0] != "restart":
            steps.insert(0, "restart")
        paths["steps.json"].write_text(json.dumps(steps, indent=2), encoding="utf-8")
        started = time.monotonic()
        print(json.dumps({"scene": scene, "status": "START", "log": str(paths["log"])}), flush=True)
        with paths["log"].open("wb") as log:
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/phase8_android_demo.py",
                    "--adb",
                    args.adb,
                    "--serial",
                    args.serial,
                    "--port",
                    "8024",
                    "--closeout",
                    "--steps",
                    str(paths["steps.json"]),
                    "--report",
                    str(paths["json"]),
                ],
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
            )
        paths["exit"].write_text(str(result.returncode) + "\n", encoding="utf-8")
        entry = {
            "scene": scene,
            "exit": result.returncode,
            "seconds": round(time.monotonic() - started, 1),
            "base": str(base),
        }
        results.append(entry)
        print(json.dumps(entry), flush=True)
    summary = ROOT / ".cache" / f"phase8f-{args.batch}-suite.json"
    summary.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return 1 if any(value["exit"] for value in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
