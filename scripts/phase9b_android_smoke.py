"""Fresh Android smoke; reuse actual private native helper, never old results."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENES = {
    "resource_create": "phase8f_closeout_resource_create.json",
    "sse_normal": "phase8f_closeout_sse_normal.json",
    "memory_smoke_revoke": "phase8f_closeout_memory_smoke_revoke.json",
    "session": "phase9b_session_smoke.json",
    "import_history": "phase8f_import_steps.json",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", required=True)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--batch", required=True, choices=("r1", "r2", "r3"))
    parser.add_argument("--scenes", nargs="+", choices=SCENES, default=list(SCENES))
    args = parser.parse_args()
    exits = []
    for scene in args.scenes:
        base = ROOT / ".cache" / f"phase9b-android-{args.batch}-{scene}"
        paths = {
            name: base.with_suffix("." + name) for name in ("steps.json", "json", "log", "exit")
        }
        if any(path.exists() for path in paths.values()):
            raise RuntimeError("Independent native evidence already exists; choose a fresh batch")
        steps = json.loads((ROOT / "scripts/native" / SCENES[scene]).read_text("utf-8"))
        if steps[0] != "restart":
            steps.insert(0, "restart")
        paths["steps.json"].write_text(json.dumps(steps, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"scene": scene, "status": "START"}), flush=True)
        with paths["log"].open("wb") as output:
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
                stdout=output,
                stderr=subprocess.STDOUT,
                check=False,
            )
        paths["exit"].write_text(str(result.returncode) + "\n", encoding="utf-8")
        exits.append(result.returncode)
        print(json.dumps({"scene": scene, "exit": result.returncode}), flush=True)
    return int(any(exits))


if __name__ == "__main__":
    raise SystemExit(main())
