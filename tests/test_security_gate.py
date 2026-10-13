"""Negative checks for risk/evidence validation and phase marker restrictions."""

import copy
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
import check_security_9a as security

SPEC = importlib.util.spec_from_file_location("security_verifier", ROOT / "scripts/verify.py")
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


class SecurityGateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.register = json.loads((ROOT / "docs/SECURITY_RISK_REGISTER.json").read_text("utf-8"))
        for name in security.REQUIRED:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text((ROOT / name).read_text("utf-8"), encoding="utf-8")
        for row in self.register["risks"]:
            for test in row["tests"]:
                name = test.partition("::")[0]
                target = self.root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text((ROOT / name).read_text("utf-8"), encoding="utf-8")
        self.write_register()

    def write_register(self):
        (self.root / "docs/SECURITY_RISK_REGISTER.json").write_text(json.dumps(self.register), encoding="utf-8")

    def test_actual_risk_register_is_valid(self):
        security.check(self.root)

    def test_unresolved_p1_cannot_be_waived(self):
        self.register["risks"][0]["status"] = "deferred"
        self.write_register()
        with self.assertRaisesRegex(RuntimeError, "blocking"):
            security.check(self.root)

    def test_missing_field_duplicate_id_and_fake_test_are_rejected(self):
        original = copy.deepcopy(self.register)
        for mutation in ("field", "duplicate", "test"):
            self.register = copy.deepcopy(original)
            if mutation == "field":
                self.register["risks"][0].pop("responsible_phase")
            elif mutation == "duplicate":
                self.register["risks"][1]["id"] = self.register["risks"][0]["id"]
            else:
                self.register["risks"][0]["tests"] = ["apps/server/tests/test_upload_security.py::test_fake_missing"]
            self.write_register()
            with self.assertRaises(RuntimeError):
                security.check(self.root)

    def test_completed_marker_requires_immutable_successful_evidence(self):
        log = self.root / "synthetic.log"
        exit_file = self.root / "synthetic.exit"
        log.write_text("Unit test evidence only\n", encoding="utf-8")
        exit_file.write_text("0\n", encoding="utf-8")
        gate = {"exit_code": 0,
                "log": {"path": "synthetic.log", "sha256": hashlib.sha256(log.read_bytes()).hexdigest()},
                "exit": {"path": "synthetic.exit", "sha256": hashlib.sha256(exit_file.read_bytes()).hexdigest()}}
        matrix = {"phase": "9A", "status": "PASS", "open_p0_p1": [], "focused": gate, "pre_marker": gate}
        (self.root / "docs/PHASE_9A_MATRIX.json").write_text(json.dumps(matrix), encoding="utf-8")
        security.check(self.root, completed=True)
        log.write_text("Changed\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "hash"):
            security.check(self.root, completed=True)

    def test_only_8_9a_is_allowed_and_phase8_evidence_stays_required(self):
        with patch.multiple(verifier, PHASE=8, SUBPHASE="9A"), \
             patch.object(security, "check") as security_check, \
             patch.object(verifier, "native_closeout_check", side_effect=RuntimeError("native evidence required")):
            with self.assertRaisesRegex(RuntimeError, "native evidence"):
                verifier.phase_marker_check()
            security_check.assert_called_once()
        for phase, subphase in ((9, "9A"), (8, "9C"), (7, "9A")):
            with patch.multiple(verifier, PHASE=phase, SUBPHASE=subphase):
                with self.assertRaises(RuntimeError):
                    verifier.phase_marker_check()


if __name__ == "__main__":
    unittest.main()
