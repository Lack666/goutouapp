"""Native completion must be complete, independently successful and reviewable."""

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "closeout_verifier", Path(__file__).resolve().parents[1] / "scripts/verify.py"
)
assert SPEC and SPEC.loader
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


class NativeCloseoutGateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / "docs").mkdir()
        self.patch = patch.object(verifier, "ROOT", self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.matrix = {"status": "PASS", "open_p0_p1": [], "tests": []}
        for scene in sorted(verifier.NATIVE_CLOSEOUT_SCENES):
            steps = ["case 8F-SYNTHETIC-GATE", "evidence", "stop"]
            report = [
                {"execution": {"steps": steps}},
                {"command": "case", "status": "done"},
                {"command": "evidence", "status": "done"},
            ]
            test = {
                "scene": scene,
                "status": "PASS",
                "exit_code": 0,
                "id": "8F-SYNTHETIC-GATE",
                "preconditions": "Unit fixture only",
                "steps": steps,
                "expected": "Gate validation",
                "actual": "Unit fixture",
                "server_evidence": "Unit fixture only",
                "artifacts": {},
            }
            for name, content in (
                ("steps", json.dumps(steps)),
                ("report", json.dumps(report)),
                ("log", "Unit fixture\n"),
                ("exit", "0\n"),
            ):
                test["artifacts"][name] = self.write(f"{scene}.{name}", content)
            self.matrix["tests"].append(test)
        self.matrix["pre_marker"] = {
            "exit_code": 0,
            "log": self.write("pre.log", "Unit fixture\n"),
            "exit": self.write("pre.exit", "0\n"),
        }

    def write(self, name, content):
        path = self.root / name
        path.write_text(content, encoding="utf-8")
        return {"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    def check(self):
        (self.root / "docs/PHASE_8F_CLOSEOUT_MATRIX.json").write_text(
            json.dumps(self.matrix), encoding="utf-8"
        )
        verifier.native_closeout_check()

    def test_complete_independent_evidence_is_accepted(self):
        self.check()

    def test_missing_native_scene_is_rejected(self):
        self.matrix["tests"].pop()
        with self.assertRaisesRegex(RuntimeError, "coverage"):
            self.check()

    def test_one_failed_scene_blocks_closure(self):
        self.matrix["tests"][0]["exit_code"] = 1
        with self.assertRaisesRegex(RuntimeError, "independently"):
            self.check()

    def test_partial_execution_cannot_be_spliced_into_pass(self):
        test = self.matrix["tests"][0]
        descriptor = test["artifacts"]["report"]
        rows = json.loads((self.root / descriptor["path"]).read_text("utf-8"))
        rows.pop()
        test["artifacts"]["report"] = self.write(descriptor["path"], json.dumps(rows))
        with self.assertRaisesRegex(RuntimeError, "complete independent"):
            self.check()

    def test_evidence_changed_after_manifest_is_rejected(self):
        (self.root / self.matrix["tests"][0]["artifacts"]["log"]["path"]).write_text("Changed")
        with self.assertRaisesRegex(RuntimeError, "hash mismatch"):
            self.check()

    def test_external_artifacts_are_rejected(self):
        self.matrix["tests"][0]["artifacts"]["log"]["path"] = "../external.log"
        with self.assertRaisesRegex(RuntimeError, "outside"):
            self.check()

    def test_pre_marker_failure_blocks_closure(self):
        self.matrix["pre_marker"]["exit_code"] = 1
        with self.assertRaisesRegex(RuntimeError, "pre-marker"):
            self.check()

    def test_future_phase_is_rejected(self):
        with patch.multiple(verifier, PHASE=9, SUBPHASE="9A"):
            with self.assertRaisesRegex(RuntimeError, "Phase 9"):
                verifier.phase_marker_check()

    def test_native_state_snapshot_is_an_execution_step(self):
        test = self.matrix["tests"][0]
        steps = ["state", "stop"]
        report = [{"execution": {"steps": steps}}, {"ui_state": [{"text": "Synthetic UI"}]}]
        test["artifacts"]["steps"] = self.write("state.steps", json.dumps(steps))
        test["artifacts"]["report"] = self.write("state.report", json.dumps(report))
        self.check()
