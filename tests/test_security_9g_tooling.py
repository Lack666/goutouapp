"""Reject stale execution, weakened native provenance and premature whole Phase9."""

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_security_9g as security


class Security9GGateTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        patched = patch.object(security, "source_fingerprint", return_value="current")
        patched.start()
        self.addCleanup(patched.stop)

    def artifact(self, name, content):
        path = self.root / "docs/evidence/phase9g" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, "utf-8")
        return {"path": path.relative_to(self.root).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    def record(self, *, exit="0", fingerprint="current", log="49 passed"):
        descriptor = self.artifact("focused.log", log)
        return {"exit_code": 0, "log": descriptor, "exit": self.artifact("focused.exit", exit),
            "source": self.artifact("focused.source.json", json.dumps({
                "source_fingerprint": fingerprint, "exit_code": 0,
                "log_sha256": descriptor["sha256"],
                "phase_marker": {"completed_phase": 8, "completed_subphase": "9F"},
            }))}

    def test_changed_evidence_rejected(self):
        record = self.record()
        (self.root / record["log"]["path"]).write_text("changed", "utf-8")
        with self.assertRaisesRegex(RuntimeError, "hash"):
            security.gate(record, self.root)

    def test_evidence_path_escape_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "outside"):
            security.artifact({"path": "../outside", "sha256": "bad"}, self.root)

    def test_independent_exit_cannot_be_replaced_by_pass_prose(self):
        with self.assertRaisesRegex(RuntimeError, "zero exit"):
            security.gate(self.record(exit="1"), self.root)

    def test_execution_time_source_is_required(self):
        with self.assertRaisesRegex(RuntimeError, "source fingerprint"):
            security.gate(self.record(fingerprint="old"), self.root)

    def test_successful_current_source_focused_record(self):
        self.assertEqual(security.gate(self.record(), self.root), "49 passed")

    def test_focused_tests_cannot_replace_complete_root(self):
        with self.assertRaisesRegex(RuntimeError, "complete root"):
            security.root_gate(self.record(), self.root, "9F")

    def test_root_marker_provenance_cannot_be_inferred_from_stdout(self):
        with self.assertRaisesRegex(RuntimeError, "marker provenance"):
            security.root_gate(self.record(), self.root, "9G")

    def test_missing_formal_gate_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "Missing"):
            security.check(self.root)

    def test_historical_native_requires_identical_executable_inputs(self):
        manifest = self.artifact("runtime.json", json.dumps({"commit": "64afd5d", "files": {"app.py": "old"}}))
        (self.root / "docs/PHASE_9G_MATRIX.json").write_text(json.dumps({
            "historical_native": {"runtime_manifest": manifest}}), "utf-8")
        with patch.object(security, "runtime_files", return_value={"app.py": "new"}):
            with self.assertRaisesRegex(RuntimeError, "fresh Android required"):
                security.prior_9f(self.root)

    def test_updating_manifest_cannot_relabel_changed_runtime_as_old_native(self):
        manifest = self.artifact("runtime.json", json.dumps({"commit": "64afd5d", "files": {"app.py": "new"}}))
        (self.root / "docs/PHASE_9G_MATRIX.json").write_text(json.dumps({
            "historical_native": {"runtime_manifest": manifest}}), "utf-8")
        with patch.object(security, "runtime_files", return_value={"app.py": "new"}), \
             patch.object(security, "committed_runtime_files", return_value={"app.py": "old"}):
            with self.assertRaisesRegex(RuntimeError, "differs from Git"):
                security.prior_9f(self.root)

    def test_9g_preserves_every_prior_gate_and_rejects_9h_and_whole9(self):
        spec = importlib.util.spec_from_file_location("verifier_9g", ROOT / "scripts/verify.py")
        verifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(verifier)
        from contextlib import ExitStack

        with ExitStack() as stack:
            stack.enter_context(patch.multiple(verifier, PHASE=8, SUBPHASE="9G"))
            checks = []
            for name in ("9a", "9b", "9c", "9d", "9e", "9f", "9g"):
                module = __import__("check_security_" + name)
                checks.append(stack.enter_context(patch.object(module, "check")))
            stack.enter_context(patch.object(verifier, "native_closeout_check", side_effect=RuntimeError("prior native required")))
            with self.assertRaisesRegex(RuntimeError, "prior native"):
                verifier.phase_marker_check()
            for check in checks:
                check.assert_called_once_with(completed=True)
        for phase, subphase in ((8, "9I"), (9, "9G"), (10, None)):
            with patch.multiple(verifier, PHASE=phase, SUBPHASE=subphase):
                with self.assertRaises(RuntimeError):
                    verifier.phase_marker_check()
