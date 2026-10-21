"""Independent current-source native scenes; historical transcripts are immutable."""

import argparse
import json
import os
import re
import shutil
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
    "dataset": "phase9f_dataset.json",
    "conversation": "phase9f_conversation.json",
    "erasure_faults": "phase9f_faults.json",
    "erasure_restart": "phase9f_restart_session.json",
    "person": "phase9h_person.json",
    "relationship": "phase9h_relationship.json",
    "lifecycle_faults": "phase9h_faults.json",
    "lifecycle_restart": "phase9h_restart_session.json",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", required=True)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--scenes", nargs="+", choices=SCENES, default=list(SCENES))
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9-]{1,30}", args.batch):
        parser.error("Bounded evidence batch required")
    failures = []
    for scene in args.scenes:
        name = f"android-{args.batch}-{scene}"
        report = ROOT / ".cache" / (name + ".json")
        if report.exists():
            raise RuntimeError("Native report is immutable")
        command = [
            sys.executable,
            "scripts/phase9h_capture.py",
            "--name",
            name,
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
            "scripts/native/" + SCENES[scene],
            "--report",
            str(report),
        ]
        print(json.dumps({"scene": scene, "status": "START"}), flush=True)
        result = subprocess.run(
            command,
            cwd=ROOT,
            env={
                **os.environ,
                "GOUTOU_ERASURE_E2E": "1",
                "GOUTOU_NATIVE_BUILD_SOURCE_REQUIRED": "1",
            },
        )
        destination = ROOT / "docs/evidence/phase9h" / (name + ".json")
        if destination.exists():
            raise RuntimeError("Native evidence is immutable")
        if report.is_file():
            shutil.copyfile(report, destination)
        failures.append(result.returncode)
        print(json.dumps({"scene": scene, "exit_code": result.returncode}), flush=True)
    return int(any(failures))


if __name__ == "__main__":
    raise SystemExit(main())
