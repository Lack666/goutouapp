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
from uuid import UUID, uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]
DEVICE_FILE = "/sdcard/Download/phase8f-synthetic.md"


def run_private_command(parts: list[str], *, timeout: float = 20) -> bytes:
    """Never let subprocess exceptions serialize private native input arguments."""
    try:
        value = subprocess.run(parts, capture_output=True, timeout=timeout, check=False)
    except (subprocess.SubprocessError, OSError):
        raise RuntimeError("Android command unavailable; private arguments suppressed") from None
    if value.returncode:
        raise RuntimeError("Android command failed; private arguments suppressed")
    return value.stdout


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", required=True, type=Path)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--port", type=int, choices=(8022, 8024), default=8022)
    parser.add_argument(
        "--steps", type=Path, help="JSON array of synthetic commands; no credentials"
    )
    parser.add_argument("--report", type=Path, help="Sanitized metadata report within .cache")
    parser.add_argument(
        "--closeout", action="store_true", help="Enable disposable native observer/fault fixture"
    )
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
        return run_private_command([str(args.adb), "-s", args.serial, *parts])

    if adb("shell", "getprop", "sys.boot_completed").strip() != b"1":
        raise RuntimeError("Android boot is incomplete")
    screen_height = int(re.findall(rb"\d+x(\d+)", adb("shell", "wm", "size"))[-1])
    print(
        json.dumps(
            {"android_api": adb("shell", "getprop", "ro.build.version.sdk").decode().strip()}
        ),
        flush=True,
    )
    env = {**os.environ, "GOUTOU_MEMORY_E2E": "1", "GOUTOU_IMPORT_E2E": "1", "PYTHONUTF8": "1"}
    env["GOUTOU_MEMORY_PORT"] = str(args.port)
    if args.closeout:
        env["GOUTOU_NATIVE_ACCEPTANCE"] = "1"
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
        bookmarks: dict[str, dict[str, str]] = {}
        identity_boundary = 0

        def nodes():
            raw = adb("exec-out", "uiautomator", "dump", "/dev/tty").decode("utf-8")
            if "<?xml" not in raw or "</hierarchy>" not in raw:
                raise RuntimeError("Android accessibility hierarchy unavailable")
            return list(
                ET.fromstring(raw[raw.index("<?xml") : raw.index("</hierarchy>") + 12]).iter("node")
            )

        def tap(label: str, direction="up"):
            initial_direction = direction
            for attempt in range(24):
                direction = (
                    initial_direction
                    if attempt < 12
                    else ("down" if initial_direction == "up" else "up")
                )
                current = nodes()
                # FlatList may publish inverted bounds for clipped header nodes.
                # Use its actual viewport, not the full screen (the fixed paging
                # footer is outside that scrollable region).
                viewport_bottom = screen_height - 64
                for candidate in current:
                    if candidate.get("content-desc") == "历史消息列表":
                        viewport = list(map(int, re.findall(r"\d+", candidate.get("bounds", ""))))
                        if len(viewport) == 4 and viewport[3] > viewport[1]:
                            viewport_bottom = viewport[3]
                labelled = [node for node in current if node.get("content-desc") == label]
                for node in labelled or current:
                    if label not in {node.get("text"), node.get("content-desc")}:
                        continue
                    x1, y1, x2, y2 = map(int, re.findall(r"\d+", node.get("bounds", "")))
                    if (
                        node.get("enabled") != "false"
                        and x2 > x1
                        and y2 - y1 >= 40
                        and 140 <= y1
                        and y2 <= screen_height - 64
                    ):
                        adb("shell", "input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2))
                        return
                    direction = "up" if max(y1, y2) > viewport_bottom - 64 else "down"
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

        def find(fragment: str, visible=False):
            lower_section = fragment.startswith(
                ("Mutation 状态：", "Confirmation ID：", "Mutation ID：", "删除后撤销授权：")
            )
            for attempt in range(24):
                preferred_up = None
                for node in nodes():
                    if node.get("password") == "true":
                        continue
                    text = node.get("text", "") or node.get("content-desc", "")
                    if fragment in text:
                        bounds = list(map(int, re.findall(r"\d+", node.get("bounds", ""))))
                        if not visible or (
                            len(bounds) == 4
                            and bounds[3] - bounds[1] >= 40
                            and bounds[1] >= 140
                            and bounds[3] <= screen_height - 64
                        ):
                            return text
                        if len(bounds) == 4:
                            preferred_up = bounds[1] > 1000
                # Most assertions inspect a header after FlatList scrolled to
                # its committed message. Search upward in content first.
                up = (
                    preferred_up
                    if preferred_up is not None
                    else (lower_section if attempt < 12 else not lower_section)
                )
                adb(
                    "shell",
                    "input",
                    "swipe",
                    "90",
                    "1750" if up else "600",
                    "90",
                    "600" if up else "1750",
                    "350",
                )
                time.sleep(0.25)
            raise RuntimeError("Expected synthetic UI evidence is unavailable")

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
        from check_security_9b import mobile_fingerprint
        from check_security_9e import source_fingerprint as erasure_fingerprint

        evidence: list[dict] = [
            {
                "execution": {
                    "steps_file": str(args.steps) if args.steps else "interactive",
                    "steps": inputs if args.steps else None,
                    "helper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    "device": args.serial,
                    "mobile_fingerprint": mobile_fingerprint(ROOT),
                    "erasure_fingerprint": erasure_fingerprint(ROOT),
                }
            }
        ]
        try:
            for line in inputs:
                action, _, parameter = line.strip().partition(" ")
                if action != "login":
                    for key, value in context.items():
                        parameter = parameter.replace("{" + key + "}", value)
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
                    elif action == "case":
                        if not re.fullmatch(r"(?:8F|9F)-[A-Z0-9-]+", parameter):
                            raise ValueError("Invalid acceptance test ID")
                        evidence.append({"case": parameter})
                        print(json.dumps({"case": parameter}), flush=True)
                    elif action == "wait":
                        seconds = float(parameter)
                        if not 0 <= seconds <= 30:
                            raise ValueError("Bounded native wait required")
                        time.sleep(seconds)
                    elif action in {"assert_ui", "assert_visible_ui"}:
                        actual = find(json.loads(parameter), visible=action == "assert_visible_ui")
                        evidence.append({action: actual, "status": "PASS"})
                        print(json.dumps(evidence[-1]), flush=True)
                    elif action == "assert_absent":
                        fragments = json.loads(parameter)
                        texts = [
                            n.get("text", "") + n.get("content-desc", "")
                            for n in nodes()
                            if n.get("password") != "true"
                        ]
                        if any(fragment in text for fragment in fragments for text in texts):
                            raise RuntimeError("Old synthetic owner/scope data is visible")
                        evidence.append({"assert_absent": fragments, "status": "PASS"})
                    elif action == "observe":
                        text = find("NATIVE-SSE ")
                        observation = json.loads(text.split("NATIVE-SSE ", 1)[1])
                        evidence.append({"native_sse": observation})
                        print(json.dumps(evidence[-1]), flush=True)
                        if parameter:
                            if (
                                observation["terminal"] != parameter
                                or not observation["consistentRun"]
                            ):
                                raise RuntimeError("Native SSE terminal/Run consistency failed")
                            if (
                                not observation["reader"]["reads"]
                                or not observation["reader"]["cancels"]
                                or not observation["reader"]["releases"]
                            ):
                                raise RuntimeError("Native Reader cleanup evidence missing")
                            types = [value["type"] for value in observation["events"]]
                            if parameter == "completed":
                                if (
                                    types[0] != "run_started"
                                    or types[-1] != "completed"
                                    or "status" not in types
                                    or "final_response" not in types
                                ):
                                    raise RuntimeError("Native event sequence failed")
                                final_ms = next(
                                    value["ms"]
                                    for value in observation["events"]
                                    if value["type"] == "final_response"
                                )
                                if not any(
                                    value["phase"] == "running"
                                    and value["progress"]
                                    and value["ms"] < final_ms
                                    for value in observation["ui"]
                                ):
                                    raise RuntimeError(
                                        "No rendered native progress before final response"
                                    )
                            if parameter == "failed" and "failed" not in types:
                                raise RuntimeError("Missing failed event")
                    elif action == "fault":
                        if not args.closeout:
                            raise ValueError("Faults require disposable Closeout mode")
                        evidence.append({"fault": command("fault " + parameter)})
                    elif action == "assert_observer_same":
                        snapshots = [
                            value["native_sse"] for value in evidence if "native_sse" in value
                        ]
                        if len(snapshots) < 2 or snapshots[-2] != snapshots[-1]:
                            raise RuntimeError(
                                "Late SSE processing changed cancelled screen metadata"
                            )
                        evidence.append(
                            {
                                "assert_observer_same": "No late events or rendered state changes",
                                "status": "PASS",
                            }
                        )
                    elif action == "adopt":
                        with httpx.Client(
                            base_url=credentials["baseURL"],
                            headers={"Authorization": "Bearer " + credentials[identity]},
                        ) as client:
                            for kind, key in (
                                ("persons", "person"),
                                ("relationships", "relationship"),
                                ("conversations", "conversation"),
                            ):
                                result = client.get("/api/v1/" + kind)
                                if result.status_code != 200:
                                    raise RuntimeError("Owned resource witness read failed")
                                items = result.json()["items"]
                                if len(items) == 1:
                                    context[key] = items[0]["id"]
                        evidence.append(
                            {"owned_resource_witness": dict(context), "transport": "host GET only"}
                        )
                        print(json.dumps(evidence[-1]), flush=True)
                    elif action == "bookmark":
                        bookmarks[parameter] = dict(context)
                    elif action == "scope":
                        if parameter == "missing":
                            bookmarks[parameter] = {
                                key: str(uuid4())
                                for key in ("person", "relationship", "conversation")
                            }
                        context = dict(bookmarks[parameter])
                    elif action == "route":
                        path, name = json.loads(parameter)
                        if path not in {"chat", "relationship", "history", "import"}:
                            raise ValueError("Invalid native route")
                        selected = bookmarks.get(name, context)
                        relationship = str(UUID(selected["relationship"]))
                        query = "?relationshipId=" + relationship
                        if path == "chat":
                            query += "&conversationId=" + str(UUID(selected["conversation"]))
                        adb(
                            "shell",
                            "am",
                            "start",
                            "-a",
                            "android.intent.action.VIEW",
                            "-d",
                            "'exp://127.0.0.1:8092/--/" + path + query + "'",
                            "-p",
                            "host.exp.exponent",
                        )
                        time.sleep(1)
                    elif action == "expire_confirmation":
                        text = find("Confirmation ID：")
                        identifier = re.search(
                            r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", text
                        ).group()
                        evidence.append({"expiry": command("expire_confirmation " + identifier)})
                    elif action == "expire_erasure":
                        text = find("Confirmation ID：")
                        identifier = re.search(
                            r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", text
                        ).group()
                        evidence.append({"erasure_expiry": command("expire_erasure " + identifier)})
                    elif action == "busy_conversation":
                        evidence.append(
                            {"busy": command("busy_conversation " + context["conversation"])}
                        )
                    elif action == "stale_memory":
                        evidence.append({"stale": command("stale_memory " + context["memory"])})
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
                        if args.closeout:
                            identity_boundary = len(command("wire_evidence")["requests"])
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

                            name = parameter or "8F Native synthetic"
                            if len(name) > 40 or (parameter and not parameter.isascii()):
                                raise ValueError("Bounded synthetic resource name required")
                            person = create("persons", {"display_name": name})
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
                    elif action == "history_setup":
                        count, tag = json.loads(parameter)
                        if not 1 <= count <= 301 or not tag.isascii() or len(tag) > 30:
                            raise ValueError("Bounded synthetic history required")
                        content = "".join(
                            f"## 2024-01-01 08:00:00 {'我' if i % 2 == 0 else '匿名同学'}\n\n"
                            f"Synthetic {tag} history occurrence.\n\n"
                            for i in range(count)
                        ).encode()
                        with httpx.Client(
                            base_url=credentials["baseURL"],
                            headers={"Authorization": "Bearer " + credentials[identity]},
                            timeout=30,
                        ) as client:

                            def checked(result):
                                if result.status_code not in {200, 201}:
                                    raise RuntimeError("Synthetic history setup failed")
                                return result.json()

                            job = checked(
                                client.post(
                                    "/api/v1/chat-imports",
                                    data={
                                        "source_timezone": "Asia/Shanghai",
                                        "source_format": "wechat_markdown_v1",
                                    },
                                    files={
                                        "file": ("closeout-synthetic.md", content, "text/markdown")
                                    },
                                )
                            )
                            path = "/api/v1/chat-imports/" + job["id"]
                            for label, kind in (("我", "self"), ("匿名同学", "person")):
                                job = checked(
                                    client.put(
                                        path + "/speakers",
                                        json={
                                            "raw_speaker_label": label,
                                            "binding_kind": kind,
                                            "person_id": context["person"]
                                            if kind == "person"
                                            else None,
                                            "expected_revision": job["binding_revision"],
                                        },
                                    )
                                )
                            job = checked(
                                client.put(
                                    path + "/relationship",
                                    json={
                                        "relationship_id": context["relationship"],
                                        "expected_revision": job["binding_revision"],
                                    },
                                )
                            )
                            job = checked(client.post(path + "/ready"))
                            receipt = checked(
                                client.post(
                                    path + "/finalize",
                                    json={"expected_revision": job["binding_revision"]},
                                )
                            )
                            context["job"] = job["id"]
                            evidence.append(
                                {
                                    "history_setup": {
                                        "transport": "host REST preconditions",
                                        "count": count,
                                        "relationship": context["relationship"],
                                        "job": job["id"],
                                        "receipt_status": receipt["status"],
                                    }
                                }
                            )
                            print(json.dumps(evidence[-1]), flush=True)
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
                    elif action == "receipt_id":
                        proof = command("memory_evidence")
                        if not proof["mutations"]:
                            raise RuntimeError("No authoritative mutation witness")
                        context["receipt"] = proof["mutations"][-1]["id"]
                        time.sleep(1)
                    elif action == "save":
                        if not context or parameter not in {"一", "二", "三", "四", "五"}:
                            raise ValueError(
                                "Seed scope and an allowed synthetic week are required"
                            )
                        with httpx.Client(
                            base_url=credentials["baseURL"],
                            headers={"Authorization": "Bearer " + credentials[identity]},
                            timeout=30,
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
                            "resources": command("counts"),
                        }
                        if args.closeout:
                            proof["wire"] = command("wire_evidence")
                        if os.environ.get("GOUTOU_ERASURE_E2E") == "1":
                            proof["erasure"] = command("erasure_evidence")
                        evidence.append({"database": proof})
                        print(json.dumps(proof), flush=True)
                    elif action == "assert_erased":
                        domain, name, deleted, count = json.loads(parameter)
                        selected = bookmarks.get(name, context)
                        key = "job" if domain == "dataset" else "conversation"
                        proof = command("erasure_evidence")
                        rows = proof["datasets" if domain == "dataset" else "conversations"]
                        row = next(row for row in rows if row["id"] == selected[key])
                        if row["deleted"] != deleted or row["messages"] != count:
                            raise RuntimeError("Erasure SQL target witness mismatch")
                        evidence.append(
                            {
                                "assert_erased": domain,
                                "target": selected[key],
                                "deleted": deleted,
                                "message_count": count,
                                "status": "PASS",
                            }
                        )
                    elif action == "assert_erasure_replay":
                        requests = command("wire_evidence")["requests"]
                        executed = [
                            row
                            for row in requests
                            if row["path"] == "/api/v1/erasures/execute"
                            and not row["host_setup"]
                            and row.get("status") == 200
                        ]
                        if (
                            len(executed) < 2
                            or not executed[-1].get("body_sha256")
                            or executed[-1]["body_sha256"] != executed[-2].get("body_sha256")
                        ):
                            raise RuntimeError(
                                "Native original erasure body/key replay witness missing"
                            )
                        evidence.append(
                            {
                                "assert_erasure_replay": "exact body SHA256 unchanged",
                                "status": "PASS",
                            }
                        )
                    elif action == "assert_erasure_http":
                        name, expected = json.loads(parameter)
                        selected = bookmarks.get(name, context)
                        with httpx.Client(
                            base_url=credentials["baseURL"],
                            headers={"Authorization": "Bearer " + credentials[identity]},
                        ) as client:
                            response = client.get(
                                "/api/v1/conversations/" + selected["conversation"] + "/messages"
                            )
                            if response.status_code != expected:
                                raise RuntimeError(
                                    "Erasure authoritative History rejection mismatch"
                                )
                        evidence.append(
                            {
                                "assert_erasure_http": selected["conversation"],
                                "actual": expected,
                                "status": "PASS",
                            }
                        )
                    elif action == "assert_db":
                        path, expected = json.loads(parameter)
                        actual = next(
                            value["database"] for value in reversed(evidence) if "database" in value
                        )
                        for key in path.split("."):
                            if isinstance(actual, list):
                                actual = len(actual) if key == "length" else actual[int(key)]
                            else:
                                actual = actual[key]
                        if actual != expected:
                            raise RuntimeError("Database witness assertion failed")
                        evidence.append(
                            {
                                "assert_db": path,
                                "expected": expected,
                                "actual": actual,
                                "status": "PASS",
                            }
                        )
                    elif action == "assert_same":
                        snapshots = [
                            value["database"]["agent"] for value in evidence if "database" in value
                        ]
                        if len(snapshots) < 2 or snapshots[-2] != snapshots[-1]:
                            raise RuntimeError(
                                "Replay changed persisted run/messages/provider calls/Memory"
                            )
                        evidence.append(
                            {
                                "assert_same": "Run/message IDs, keys, calls and Memory unchanged",
                                "status": "PASS",
                            }
                        )
                    elif action == "assert_identity":
                        proof = command("wire_evidence")
                        requests = [
                            value
                            for value in proof["requests"][identity_boundary:]
                            if not value["host_setup"]
                        ]
                        if not requests or any(
                            value["verified_owner"] != identity for value in requests
                        ):
                            raise RuntimeError(
                                "Native requests used an old or unverified owner credential"
                            )
                        evidence.append(
                            {
                                "native_identity": identity,
                                "requests_checked": len(requests),
                                "status": "PASS",
                            }
                        )
                    elif action == "foreign":
                        if identity != "b":
                            raise ValueError("Foreign witness uses independent B identity")
                        with httpx.Client(
                            base_url=credentials["baseURL"],
                            headers={"Authorization": "Bearer " + credentials["b"]},
                        ) as client:
                            proof = {}
                            for kind, key in (
                                ("persons", "person"),
                                ("relationships", "relationship"),
                                ("conversations", "conversation"),
                                ("memories", "memory"),
                                ("chat-imports", "job"),
                            ):
                                if key in context:
                                    status = client.get(
                                        "/api/v1/" + kind + "/" + context[key]
                                    ).status_code
                                    proof[kind] = status
                                    if status != 404:
                                        raise RuntimeError(
                                            "Real owner validation did not fail closed"
                                        )
                            evidence.append({"foreign_owner_http": proof})
                            print(json.dumps(evidence[-1]), flush=True)
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
