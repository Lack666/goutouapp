"""Private-pipe Android acceptance helper for a disposable synthetic database.

This is test tooling, not an App endpoint. No credentials are printed or persisted.
The UI uses the unchanged application and actual signed HTTP services.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]
DEVICE_FILE = "/sdcard/Download/phase8f-synthetic.md"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", required=True, type=Path)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--port", type=int, choices=(8022, 8024), default=8022)
    parser.add_argument(
        "--steps", type=Path, help="JSON array of synthetic commands; no credentials"
    )
    parser.add_argument("--report", type=Path, help="Sanitized metadata report within .cache")
    args = parser.parse_args()
    target = args.report.resolve() if args.report else None
    if target and not target.is_relative_to((ROOT / ".cache").resolve()):
        raise ValueError("Evidence report must remain within workspace .cache")
    inputs = json.loads(args.steps.read_text(encoding="utf-8")) if args.steps else sys.stdin
    if args.steps and (
        not isinstance(inputs, list) or not all(isinstance(value, str) for value in inputs)
    ):
        raise ValueError("Steps must be a JSON array of command strings")

    def adb(*parts: str) -> bytes:
        try:
            value = subprocess.run(
                [str(args.adb), "-s", args.serial, *parts],
                capture_output=True,
                timeout=20,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Android command timed out; private arguments suppressed") from None
        if value.returncode:
            raise RuntimeError("Android command failed; private arguments suppressed")
        return value.stdout

    if adb("shell", "getprop", "sys.boot_completed").strip() != b"1":
        raise RuntimeError("Android boot is incomplete")
    print(
        json.dumps(
            {"android_api": adb("shell", "getprop", "ro.build.version.sdk").decode().strip()}
        ),
        flush=True,
    )
    env = {**os.environ, "GOUTOU_MEMORY_E2E": "1", "GOUTOU_IMPORT_E2E": "1", "PYTHONUTF8": "1"}
    env["GOUTOU_MEMORY_PORT"] = str(args.port)
    with subprocess.Popen(
        [sys.executable, "apps/server/mobile_connected_fixture.py"],
        cwd=ROOT,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
    ) as fixture:
        assert fixture.stdin and fixture.stdout
        first = fixture.stdout.readline()
        if not first:
            raise RuntimeError("Disposable fixture unavailable; check TEST_DATABASE_URL")
        credentials = json.loads(first)
        identity = "a"
        context: dict[str, str] = {}

        def nodes():
            raw = adb("exec-out", "uiautomator", "dump", "/dev/tty").decode("utf-8")
            if "<?xml" not in raw or "</hierarchy>" not in raw:
                raise RuntimeError("Android accessibility hierarchy unavailable")
            return list(
                ET.fromstring(raw[raw.index("<?xml") : raw.index("</hierarchy>") + 12]).iter("node")
            )

        def tap(label: str, direction="up"):
            for attempt in range(12):
                current = nodes()
                labelled = [node for node in current if node.get("content-desc") == label]
                for node in labelled or current:
                    if label not in {node.get("text"), node.get("content-desc")}:
                        continue
                    x1, y1, x2, y2 = map(int, re.findall(r"\d+", node.get("bounds", "")))
                    if (
                        node.get("enabled") != "false"
                        and x2 > x1
                        and y2 > y1
                        and 140 <= y1
                        and y2 <= 2320
                    ):
                        adb("shell", "input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2))
                        return
                    direction = "up" if y1 > 1600 else "down"
                if attempt == 5:
                    direction = "down" if direction == "up" else "up"
                adb(
                    "shell",
                    "input",
                    "swipe",
                    "90",
                    "1750" if direction == "up" else "600",
                    "90",
                    "600" if direction == "up" else "1750",
                    "350",
                )
                time.sleep(0.2)
            raise RuntimeError("Requested synthetic UI control is unavailable")

        def command(value: str):
            fixture.stdin.write(value + "\n")
            fixture.stdin.flush()
            return json.loads(fixture.stdout.readline())

        print(
            json.dumps(
                {
                    "fixture": "ready",
                    "baseURL": credentials["baseURL"],
                    "commands": (
                        "state, tap [label,direction?], login a|b|expired, "
                        "seed, evidence, stage, cleanup, back, home, stop"
                    ),
                }
            ),
            flush=True,
        )
        evidence: list[dict] = []
        try:
            for line in inputs:
                action, _, parameter = line.strip().partition(" ")
                if action == "stop":
                    break
                try:
                    if action == "tap":
                        for key, value in context.items():
                            parameter = parameter.replace("{" + key + "}", value)
                        tap(*json.loads(parameter))
                        time.sleep(0.4)
                    elif action == "state":
                        # Password nodes are omitted even while a credential is being entered.
                        rows = [
                            {
                                "text": n.get("text"),
                                "label": n.get("content-desc"),
                                "bounds": n.get("bounds"),
                                "enabled": n.get("enabled"),
                            }
                            for n in nodes()
                            if n.get("password") != "true"
                            and (n.get("text") or n.get("content-desc"))
                        ]
                        output = json.dumps(rows, ensure_ascii=False)
                        for credential in (
                            credentials["a"],
                            credentials["b"],
                            credentials["expired"],
                        ):
                            output = output.replace(credential, "[redacted]")
                        evidence.append({"ui_state": json.loads(output)})
                        print(output, flush=True)
                    elif action == "login":
                        if parameter not in {"a", "b", "expired"}:
                            raise ValueError("Only disposable fixture identities are allowed")
                        if parameter != "expired":
                            credentials[parameter] = command(f"renew_token {parameter}")[
                                "credential"
                            ]
                        tap("使用 Connected Development Mode", "down")
                        tap("开发 JWT（隐藏输入）", "down")
                        for offset in range(0, len(credentials[parameter]), 12):
                            adb(
                                "shell",
                                "input",
                                "text",
                                credentials[parameter][offset : offset + 12],
                            )
                            time.sleep(0.15)
                        adb("shell", "input", "keyevent", "4")
                        tap("验证并接入开发会话", "down")
                        identity = parameter
                        if parameter != "expired":
                            # Authentication is acknowledged only after SecureStore write.
                            tap("开发会话已连接", "down")
                    elif action == "seed":
                        if identity == "expired":
                            raise ValueError("Expired identity cannot seed resources")
                        with httpx.Client(
                            base_url=credentials["baseURL"],
                            headers={"Authorization": "Bearer " + credentials[identity]},
                        ) as client:

                            def create(path, body):
                                result = client.post(
                                    "/api/v1/" + path, json={"id": str(uuid4()), **body}
                                )
                                if result.status_code != 201:
                                    raise RuntimeError("Synthetic resource creation failed")
                                return result.json()["id"]

                            person = create("persons", {"display_name": "8F Native synthetic"})
                            relationship = create(
                                "relationships",
                                {
                                    "person_id": person,
                                    "relationship_type": "unknown",
                                    "status": "unknown",
                                },
                            )
                            conversation = create(
                                "conversations", {"relationship_id": relationship}
                            )
                            context = {
                                "person": person,
                                "relationship": relationship,
                                "conversation": conversation,
                            }
                            print(json.dumps(context), flush=True)
                    elif action == "input":
                        label, text = json.loads(parameter)
                        if not text.isascii() or len(text) > 120:
                            raise ValueError("Only bounded synthetic ASCII input is accepted")
                        tap(label)
                        adb("shell", "input", "text", text.replace(" ", "%s"))
                        adb("shell", "input", "keyevent", "4")
                    elif action == "memory_id":
                        with httpx.Client(
                            base_url=credentials["baseURL"],
                            headers={"Authorization": "Bearer " + credentials[identity]},
                        ) as client:
                            result = client.get("/api/v1/memories")
                            if result.status_code != 200 or not result.json()["items"]:
                                raise RuntimeError("Synthetic memory unavailable")
                            context["memory"] = result.json()["items"][0]["id"]
                    elif action == "confirm_file":
                        for node in nodes():
                            if (
                                node.get("text") == "选择"
                                and node.get("class") == "android.widget.Button"
                            ):
                                x1, y1, x2, y2 = map(
                                    int, re.findall(r"\d+", node.get("bounds", ""))
                                )
                                adb(
                                    "shell",
                                    "input",
                                    "tap",
                                    str((x1 + x2) // 2),
                                    str((y1 + y2) // 2),
                                )
                                break
                    elif action in {"open", "restart"}:
                        if action == "restart":
                            adb("shell", "am", "force-stop", "host.exp.exponent")
                            parameter = "settings"
                            time.sleep(1)
                            adb(
                                "shell",
                                "am",
                                "start",
                                "-a",
                                "android.intent.action.VIEW",
                                "-d",
                                "exp://127.0.0.1:8092",
                                "-p",
                                "host.exp.exponent",
                            )
                            time.sleep(20)
                        if parameter not in {
                            "settings",
                            "import",
                            "history",
                            "chat",
                            "relationship",
                        }:
                            raise ValueError("Only existing native App routes are allowed")
                        adb(
                            "shell",
                            "am",
                            "start",
                            "-a",
                            "android.intent.action.VIEW",
                            "-d",
                            "exp://127.0.0.1:8092/--/" + parameter,
                            "-p",
                            "host.exp.exponent",
                        )
                        time.sleep(1)
                    elif action == "save":
                        if not context or parameter not in {"一", "二", "三", "四", "五"}:
                            raise ValueError(
                                "Seed scope and an allowed synthetic week are required"
                            )
                        with httpx.Client(
                            base_url=credentials["baseURL"],
                            headers={"Authorization": "Bearer " + credentials[identity]},
                        ) as client:
                            result = client.post(
                                f"/api/v1/conversations/{context['conversation']}/agent-runs",
                                json={
                                    "message": f"我们计划第{parameter}周见面。请存入长期记忆。",
                                    "operation_key": str(uuid4()),
                                    "expected_relationship_id": context["relationship"],
                                },
                            )
                            if result.status_code != 200:
                                raise RuntimeError("Synthetic Agent setup failed")
                            print(
                                json.dumps(
                                    {
                                        "setup_transport": "host REST",
                                        "run_id": result.json()["run_id"],
                                        "memory_status": result.json()["memory_status"],
                                    }
                                ),
                                flush=True,
                            )
                    elif action == "evidence":
                        proof = {
                            "agent": command("agent_evidence"),
                            "memory": command("memory_evidence"),
                            "import": command("import_evidence"),
                        }
                        evidence.append({"database": proof})
                        print(json.dumps(proof), flush=True)
                    elif action == "stage":
                        content = "".join(
                            f"## 2024-01-01 08:00:00 {'我' if index % 2 == 0 else '匿名同学🥰'}"
                            "\n\n匿名合成重复消息。\n\n"
                            for index in range(301)
                        ).encode()
                        local = ROOT / ".cache/phase8f-synthetic.md"
                        local.write_bytes(content)
                        present = adb(
                            "shell", "sh", "-c", f"'if [ -f {DEVICE_FILE} ]; then echo present; fi'"
                        ).strip()
                        if (
                            present
                            and hashlib.sha256(adb("exec-out", "cat", DEVICE_FILE)).digest()
                            != hashlib.sha256(content).digest()
                        ):
                            raise RuntimeError(
                                "Existing device file identity mismatch; not overwritten"
                            )
                        adb("push", str(local), DEVICE_FILE)
                        if (
                            hashlib.sha256(adb("exec-out", "cat", DEVICE_FILE)).digest()
                            != hashlib.sha256(content).digest()
                        ):
                            raise RuntimeError("Device fixture hash mismatch")
                    elif action == "cleanup":
                        local = ROOT / ".cache/phase8f-synthetic.md"
                        if (
                            not local.is_file()
                            or hashlib.sha256(adb("exec-out", "cat", DEVICE_FILE)).digest()
                            != hashlib.sha256(local.read_bytes()).digest()
                        ):
                            raise RuntimeError("Device fixture identity mismatch; not removed")
                        adb("shell", "rm", DEVICE_FILE)
                    elif action in {"back", "home"}:
                        adb("shell", "input", "keyevent", "4" if action == "back" else "3")
                    else:
                        raise ValueError("Unknown demo command")
                    if action != "state":
                        evidence.append({"command": action, "status": "done"})
                        print(json.dumps({"command": action, "status": "done"}), flush=True)
                except (RuntimeError, ValueError, httpx.HTTPError):
                    # No exception arguments, command lines or credentials reach the transcript.
                    print(json.dumps({"command": action, "status": "failed"}), flush=True)
                    evidence.append({"command": action, "status": "failed"})
                    if action in {"tap", "open"}:
                        evidence[-1]["control"] = parameter
                    if args.steps:
                        raise RuntimeError(
                            "Native sequence failed; inspect sanitized evidence"
                        ) from None
        finally:
            try:
                if target:
                    target.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
            finally:
                fixture.stdin.write("stop\n")
                fixture.stdin.flush()
                try:
                    fixture.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    fixture.terminate()
                    raise RuntimeError("Disposable fixture cleanup timed out") from None
                if fixture.returncode:
                    raise RuntimeError("Disposable fixture cleanup failed")


if __name__ == "__main__":
    main()
