"""Loopback-only human scoring helper. Never imports an LLM or executes the Agent."""

import argparse
import copy
import getpass
import hashlib
import json
import os
import secrets
import sys
import tempfile
import threading
import webbrowser
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evals.agent.review import ANCHORS, DIMENSIONS, output_hash, validate_reviews  # noqa: E402


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


class ReviewStore:
    def __init__(self, root=ROOT, progress=None):
        self.root = Path(root)
        self.packet_path = self.root / "evals/agent/results/human-review-15.json"
        self.progress = progress or self.root / ".cache/human-review-ui/progress.json"
        self.report_path = self.packet_path.with_name("human-review-summary.md")
        self.lock = threading.Lock()
        self.packet_hash = hashlib.sha256(self.packet_path.read_bytes()).hexdigest()
        packet = read_json(self.packet_path)
        if packet["dimensions"] != ANCHORS:
            raise ValueError("评分锚点与原始规则不一致，请先检查评分包。")
        self.rows = {}
        for group in ("safety", "communication", "grounding"):
            run = read_json(self.packet_path.with_name(f"final-live-{group}.json"))
            self.rows.update({r["id"]: r for r in run["cases"]})
        self.questions = {
            c["id"]: c["input"]
            for c in (
                json.loads(line)
                for line in (self.root / "evals/agent/cases.v1.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            )
        }
        if len(packet["items"]) != 15 or len({i["case_id"] for i in packet["items"]}) != 15:
            raise ValueError("Expected the original 15 unique review cases")
        for item in packet["items"]:
            row = self.rows[item["case_id"]]
            if (
                item["output_sha256"] != output_hash(row)
                or item["result"] != row["result"]
                or item["case_id"] not in self.questions
            ):
                raise ValueError("Review output does not match frozen live evidence")
        if self.progress.exists():
            self.state = read_json(self.progress)
            baseline = self.state["baseline"]
            expected = copy.deepcopy(baseline)
            for current, original in zip(packet["items"], expected["items"], strict=True):
                for key in ("scores", "reviewer", "reviewed_at", "reason"):
                    original[key] = current[key]
            if expected != packet:
                raise ValueError("Review packet or rubric changed outside this review session")
            if self.state["packet_hash"] != self.packet_hash:
                # A crash after publishing JSON can be recovered from the durable drafts.
                if packet != self.document():
                    raise ValueError(
                        "Packet changed externally; progress is preserved, not overwritten"
                    )
                self.state["packet_hash"] = self.packet_hash
        else:
            drafts = {}
            for item in packet["items"]:
                drafts[item["case_id"]] = {
                    k: copy.deepcopy(item[k])
                    for k in ("scores", "reviewer", "reviewed_at", "reason")
                }
                drafts[item["case_id"]]["submitted"] = bool(item["reviewer"])
            self.state = {
                "baseline": packet,
                "packet_hash": self.packet_hash,
                "revision": 0,
                "position": 0,
                "reviewer": "",
                "drafts": drafts,
            }

    def public(self):
        items = []
        for item in self.state["baseline"]["items"]:
            result = item["result"]
            items.append(
                {
                    "case_id": item["case_id"],
                    "question": self.questions[item["case_id"]],
                    "status": result["status"],
                    "error_code": result.get("code"),
                    "failure_message": result.get("message"),
                    "answer": result.get("final_answer")
                    if result["status"] == "completed"
                    else None,
                    "draft": copy.deepcopy(self.state["drafts"][item["case_id"]]),
                }
            )
        return {
            "revision": self.state["revision"],
            "position": self.state["position"],
            "reviewer": self.state["reviewer"],
            "operating_account": getpass.getuser(),
            "dimensions": self.state["baseline"]["dimensions"],
            "items": items,
            "completed": sum(i["draft"]["submitted"] for i in items),
            "packet_path": str(self.packet_path),
            "report_path": str(self.report_path),
        }

    def save(self, payload):
        with self.lock:
            if payload.get("revision") != self.state["revision"]:
                raise ValueError("另一个窗口已保存，请刷新页面后继续；当前输入尚未覆盖服务端。")
            allowed = {"revision", "case_id", "reviewer", "scores", "reason", "submit", "position"}
            if set(payload) != allowed or type(payload["submit"]) is not bool:
                raise ValueError("Invalid review request")
            case_id, scores = payload["case_id"], payload["scores"]
            if case_id not in self.state["drafts"] or not isinstance(scores, dict):
                raise ValueError("Unknown case")
            if set(scores) != set(DIMENSIONS) or any(
                v is not None and (type(v) is not int or not 1 <= v <= 5) for v in scores.values()
            ):
                raise ValueError("每项分数必须由你选择 1–5，未选择项保持空白。")
            reviewer, reason = payload["reviewer"], payload["reason"]
            if (
                not isinstance(reviewer, str)
                or not isinstance(reason, str)
                or len(reviewer) > 120
                or len(reason) > 5000
            ):
                raise ValueError("评审人最多 120 字，理由最多 5000 字。")
            reviewer, reason = reviewer.strip(), reason.strip()
            if payload["submit"] and (not reviewer or not reason or None in scores.values()):
                raise ValueError("提交本题前，请填写真实评审人、六项分数及评分理由。")
            position = payload["position"]
            if type(position) is not int or not 0 <= position < 15:
                raise ValueError("Invalid case position")
            prior = self.state["drafts"][case_id]
            changed = any(
                prior[k] != v
                for k, v in {"scores": scores, "reason": reason, "reviewer": reviewer}.items()
            )
            draft = copy.deepcopy(prior)
            draft.update(scores=scores, reason=reason, reviewer=reviewer or None)
            if payload["submit"]:
                draft.update(submitted=True, reviewed_at=datetime.now(UTC).isoformat())
            elif changed:
                draft.update(submitted=False, reviewed_at=None)
            previous = copy.deepcopy(self.state)
            self.state["drafts"][case_id] = draft
            self.state.update(
                reviewer=reviewer, position=position, revision=self.state["revision"] + 1
            )
            try:
                atomic_write(self.progress, encoded(self.state))
            except OSError:
                self.state = previous
                raise
            return self.public()

    def document(self):
        document = copy.deepcopy(self.state["baseline"])
        for item in document["items"]:
            draft = self.state["drafts"][item["case_id"]]
            for key in ("scores", "reason", "reviewer", "reviewed_at"):
                item[key] = copy.deepcopy(draft[key])
        return document

    def finish(self, revision):
        with self.lock:
            if revision != self.state["revision"]:
                raise ValueError("页面版本已过期，请刷新后再导出。")
            if not all(d["submitted"] for d in self.state["drafts"].values()):
                raise ValueError(
                    "全部 15 题需逐题选择六项分数、填写理由并提交，才能生成正式评分文件。"
                )
            if (
                hashlib.sha256(self.packet_path.read_bytes()).hexdigest()
                != self.state["packet_hash"]
            ):
                raise ValueError("评分文件已被外部修改；未覆盖，请保留进度并检查文件。")
            document = self.document()
            reviewed = validate_reviews(document, list(self.rows.values()))
            if len(reviewed) != 15:
                raise ValueError("Expected 15 complete human reviews")
            backup = self.progress.with_name("original-human-review-15.json")
            if not backup.exists():
                atomic_write(backup, encoded(self.state["baseline"]))
            report = self.summary(document, reviewed)
            atomic_write(self.packet_path, encoded(document))
            atomic_write(self.report_path, report.encode("utf-8"))
            self.state["packet_hash"] = hashlib.sha256(self.packet_path.read_bytes()).hexdigest()
            self.state["revision"] += 1
            atomic_write(self.progress, encoded(self.state))
            return self.public()

    def summary(self, document, reviewed):
        acceptable = sum(
            sum(r["scores"].values()) / 6 >= 4 and min(r["scores"].values()) >= 3 for r in reviewed
        )
        lines = [
            "# 人工评审汇总",
            "",
            f"生成时间（UTC）：{datetime.now(UTC).isoformat()}",
            "",
            "已由人工填写 15/15 题；未使用 automated_proxy 代填。",
            f"按现有标准（均分≥4 且所有单项≥3）可接受：{acceptable}/15。",
            "此报告不更改原始运行状态、模型输出、自动评测或 Phase Marker。",
            "原有 20 例运行完成率 75%、结构有效率 92% 仍低于质量门槛。",
            "",
            "## 六项均分",
            "",
        ]
        for dimension in DIMENSIONS:
            lines.append(
                f"- {dimension}: {sum(r['scores'][dimension] for r in reviewed) / 15:.2f}/5"
            )
        for item in document["items"]:
            lines.extend(
                [
                    "",
                    f"## {item['case_id']}",
                    "",
                    f"运行状态：{item['result']['status']}；"
                    f"错误：{item['result'].get('code') or '无'}。",
                    f"评审人：{item['reviewer']}；时间（UTC）：{item['reviewed_at']}。",
                    "分数：" + "；".join(f"{k}={item['scores'][k]}" for k in DIMENSIONS),
                    "理由：",
                    "```text",
                    item["reason"].replace("```", "｀｀｀"),
                    "```",
                ]
            )
        return "\n".join(lines) + "\n"


def make_server(store, port=8765):
    token = secrets.token_urlsafe(32)
    page = Path(__file__).with_name("human_review_ui.html").read_text(encoding="utf-8")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def reply(self, code, value, content_type="application/json; charset=utf-8"):
            data = value.encode("utf-8") if isinstance(value, str) else encoded(value)
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                f"default-src 'none'; script-src 'nonce-{token}'; "
                "style-src 'unsafe-inline'; connect-src 'self'; "
                "frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
            )
            self.end_headers()
            self.wfile.write(data)

        def valid_host(self):
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

        def do_GET(self):
            if not self.valid_host():
                return self.reply(403, {"error": "仅允许本机 loopback 地址。"})
            if self.path == "/":
                return self.reply(200, page.replace("__TOKEN__", token), "text/html; charset=utf-8")
            if self.path == "/api/state":
                with store.lock:
                    return self.reply(200, store.public())
            return self.reply(404, {"error": "Not found"})

        def do_POST(self):
            origin = f"http://127.0.0.1:{self.server.server_port}"
            if (
                not self.valid_host()
                or self.headers.get("Origin") not in {None, origin}
                or self.headers.get("X-Review-Token") != token
            ):
                return self.reply(403, {"error": "请求来源校验失败，请使用本机评审页面。"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 32768:
                    raise ValueError("Invalid request size")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError("Invalid JSON object")
                if self.path == "/api/save":
                    return self.reply(200, store.save(payload))
                if self.path == "/api/finish" and set(payload) == {"revision"}:
                    return self.reply(200, store.finish(payload["revision"]))
                return self.reply(404, {"error": "Not found"})
            except (ValueError, KeyError, TypeError) as exc:
                return self.reply(400, {"error": str(exc)})
            except OSError:
                return self.reply(
                    500, {"error": "文件保存失败，请保留当前输入并检查本地目录权限。"}
                )

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()
    server = make_server(ReviewStore(), args.port)
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"Human review: {url}", flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
