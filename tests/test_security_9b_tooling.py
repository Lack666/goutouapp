"""9B privacy checks include all old evidence and generated failure arguments."""

import importlib.util
import copy
import json
import subprocess
import sys
import tempfile
import traceback
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class PrivacyToolingTests(unittest.TestCase):
    def test_old_and_current_evidence_is_read_only_and_pattern_clean(self):
        from audit_evidence_privacy import audit
        result = audit()
        self.assertEqual(result["groups"]["phase8f-closeout"], 131)
        self.assertGreaterEqual(result["groups"]["phase9a"], 21)
        self.assertEqual(result["findings"], [])

    def test_powershell_timeout_python_and_native_failure_output_is_private(self):
        spec = importlib.util.spec_from_file_location("private_9b", ROOT / "scripts/phase8_android_demo.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        marker = uuid4().hex
        command = ["powershell", "-Command", marker]
        errors = [subprocess.TimeoutExpired(command, 1, output=marker, stderr=marker), subprocess.CalledProcessError(1, command, output=marker, stderr=marker), OSError(marker)]
        for error in errors:
            with patch.object(module.subprocess, "run", side_effect=error):
                try:
                    module.run_private_command(command)
                except RuntimeError:
                    self.assertNotIn(marker, traceback.format_exc())
                else:
                    self.fail("Private helper failure claimed success")


class NativeSecurityGateTests(unittest.TestCase):
    def setUp(self):
        import check_security_9b as security

        self.security = security
        self.matrix = json.loads((ROOT / "docs/PHASE_9B_MATRIX.json").read_text("utf-8"))
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        for row in self.matrix["native"]["scenes"]:
            for descriptor in row["artifacts"].values():
                target = self.root / descriptor["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / descriptor["path"]).read_bytes())
        mocked = patch.object(security, "mobile_fingerprint", return_value=self.matrix["native"]["mobile_fingerprint"])
        mocked.start()
        self.addCleanup(mocked.stop)

    def test_actual_complete_native_transcripts_validate(self):
        self.security.native_check(self.matrix, self.root)

    def test_missing_scene_old_dependencies_and_nonzero_exit_are_rejected(self):
        for kind in ("scene", "dependencies", "exit"):
            matrix = copy.deepcopy(self.matrix)
            if kind == "scene":
                matrix["native"]["scenes"].pop()
            elif kind == "dependencies":
                matrix["native"]["mobile_fingerprint"] = "old"
            else:
                matrix["native"]["scenes"][0]["exit_code"] = 1
            with self.assertRaises(RuntimeError):
                self.security.native_check(matrix, self.root)

    def test_altered_artifact_and_outside_evidence_path_are_rejected(self):
        descriptor = self.matrix["native"]["scenes"][0]["artifacts"]["log"]
        target = self.root / descriptor["path"]
        target.write_bytes(b"Changed transcript")
        with self.assertRaisesRegex(RuntimeError, "hash"):
            self.security.native_check(self.matrix, self.root)
        descriptor["path"] = "../outside.log"
        with self.assertRaisesRegex(RuntimeError, "outside"):
            self.security.native_check(self.matrix, self.root)

    def test_9b_marker_keeps_9a_and_phase8_native_gates(self):
        import check_security_9a
        import check_security_9b
        spec = importlib.util.spec_from_file_location("verifier_9b", ROOT / "scripts/verify.py")
        verifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(verifier)
        with patch.multiple(verifier, PHASE=8, SUBPHASE="9B"), patch.object(check_security_9a, "check") as prior, patch.object(check_security_9b, "check") as current, patch.object(verifier, "native_closeout_check", side_effect=RuntimeError("old native still required")):
            with self.assertRaisesRegex(RuntimeError, "old native"):
                verifier.phase_marker_check()
            prior.assert_called_once_with(completed=True)
            current.assert_called_once_with(completed=True)


if __name__ == "__main__":
    unittest.main()
