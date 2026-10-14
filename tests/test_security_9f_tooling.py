"""Evidence guards reject stale, missing, partial and non-native acceptance."""

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_security_9f as security


class Security9FGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name, value in (("mobile_fingerprint", "mfp"), ("erasure_fingerprint", "efp")):
            mock = patch.object(security, name, return_value=value)
            mock.start()
            self.addCleanup(mock.stop)

    def artifact(self, name, content):
        path = self.root / "docs/evidence/phase9f" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, "utf-8")
        return {
            "path": path.relative_to(self.root).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    def record(self, name="test", log="2 passed", exit="0"):
        return {
            "exit_code": 0,
            "log": self.artifact(name + ".log", log),
            "exit": self.artifact(name + ".exit", exit),
        }

    def native(self):
        rows = []
        for scene in sorted(security.NATIVE_SCENES):
            steps = ["evidence", "assert_erased", "stop"]
            canonical = self.root / "scripts/native" / f"phase9f_{scene}.json"
            canonical.parent.mkdir(parents=True, exist_ok=True)
            canonical.write_text(json.dumps(steps), "utf-8")
            requests = [
                {"path": "/api/v1" + suffix, "bearer": True, "host_setup": False, "status": 200}
                for suffix in ("/erasures/prepare", "/erasures/execute", "/erasures/receipts/id")
            ]
            report = [
                {
                    "execution": {
                        "steps": steps,
                        "mobile_fingerprint": "mfp",
                        "erasure_fingerprint": "efp",
                    }
                },
                {"database": {"erasure": {}, "wire": {"requests": requests}}},
                {"command": "evidence", "status": "done"},
                {"assert_erased": scene, "deleted": True, "message_count": 0},
                {"command": "assert_erased", "status": "done"},
            ]
            artifacts = {
                "steps": self.artifact(scene + "-steps.json", json.dumps(steps)),
                "report": self.artifact(scene + ".json", json.dumps(report)),
                "log": self.artifact(scene + ".log", "actual run"),
                "exit": self.artifact(scene + ".exit", "0"),
            }
            rows.append({"scene": scene, "status": "PASS", "exit_code": 0, "artifacts": artifacts})
        return {
            "erasure_native": {
                "status": "PASS",
                "source_fingerprint": "fp",
                "synthetic_only": True,
                "device": "unit fixture",
                "scenes": rows,
            }
        }

    def test_hash_drift_rejected(self):
        descriptor = self.artifact("test.log", "original")
        (self.root / descriptor["path"]).write_text("changed", "utf-8")
        with self.assertRaisesRegex(RuntimeError, "hash"):
            security.artifact(descriptor, self.root)

    def test_path_escape_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "outside"):
            security.artifact({"path": "../outside", "sha256": "x"}, self.root)

    def test_independent_exit_file_required(self):
        with self.assertRaisesRegex(RuntimeError, "zero exit"):
            security.gate(self.record(exit="1"), self.root)

    def test_root_log_cannot_be_a_focused_test(self):
        with self.assertRaisesRegex(RuntimeError, "complete root"):
            security.root_gate(self.record(), self.root, "9E")

    def test_missing_code_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "Missing"):
            security.check(self.root)

    @patch.object(security, "source_fingerprint", return_value="fp")
    def test_complete_native_unit_fixture(self, _):
        security.native_erasure(self.native(), self.root)

    @patch.object(security, "source_fingerprint", return_value="fp")
    def test_partial_or_stale_native_rejected(self, _):
        matrix = self.native()
        matrix["erasure_native"]["scenes"].pop()
        with self.assertRaisesRegex(RuntimeError, "coverage"):
            security.native_erasure(matrix, self.root)
        matrix = self.native()
        matrix["erasure_native"]["source_fingerprint"] = "old"
        with self.assertRaisesRegex(RuntimeError, "fresh actual"):
            security.native_erasure(matrix, self.root)

    @patch.object(security, "source_fingerprint", return_value="fp")
    def test_spliced_transcript_cannot_pass_with_updated_hash(self, _):
        matrix = self.native()
        row = matrix["erasure_native"]["scenes"][0]
        report = json.loads((self.root / row["artifacts"]["report"]["path"]).read_text("utf-8"))
        report.pop()
        row["artifacts"]["report"] = self.artifact("partial.json", json.dumps(report))
        with self.assertRaisesRegex(RuntimeError, "partial/spliced"):
            security.native_erasure(matrix, self.root)
