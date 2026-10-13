"""Evidence and marker gates must reject missing independent resource proof."""

import copy
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_security_9c as security


class Security9CGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.matrix = json.loads((ROOT / "docs/PHASE_9C_MATRIX.json").read_text("utf-8"))
        paths = set(security.REQUIRED)
        for references in self.matrix["coverage"].values():
            paths.update(reference.partition("::")[0] for reference in references)
        for name in ("focused", "pre_marker", "post_marker"):
            if name in self.matrix:
                paths.update(self.matrix[name][kind]["path"] for kind in ("log", "exit"))
        for name in paths:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, path)
        self.fingerprint = patch.object(security, "source_fingerprint", return_value=self.matrix["source_fingerprint"])
        self.fingerprint.start()
        self.addCleanup(self.fingerprint.stop)

    def write(self):
        (self.root / "docs/PHASE_9C_MATRIX.json").write_text(json.dumps(self.matrix), "utf-8")

    def test_actual_complete_local_evidence_passes(self):
        self.write()
        security.check(self.root)

    def test_completed_marker_needs_independent_pre_exit_and_pass(self):
        self.matrix["status"] = "IN PROGRESS"
        self.write()
        with self.assertRaisesRegex(RuntimeError, "requires PASS"):
            security.check(self.root, completed=True)
        self.matrix["status"] = "PASS"
        self.matrix["pre_marker"] = copy.deepcopy(self.matrix["focused"])
        self.matrix["pre_marker"]["exit_code"] = 1
        self.write()
        with self.assertRaisesRegex(RuntimeError, "zero exit"):
            security.check(self.root, completed=True)

    def test_missing_worker_coverage_or_public_waiver_fails(self):
        original = copy.deepcopy(self.matrix)
        for mutate in (
            lambda m: m["topology"].update(actual_worker_processes=1),
            lambda m: m.update(production_acceptable=True),
            lambda m: m["coverage"].pop("idle"),
            lambda m: m.update(open_p0_p1=["unresolved"]),
        ):
            self.matrix = copy.deepcopy(original)
            mutate(self.matrix)
            self.write()
            with self.assertRaises(RuntimeError):
                security.check(self.root)

    def test_evidence_corruption_and_outside_paths_fail(self):
        record = self.matrix["focused"]["log"]
        record["sha256"] = "0" * 64
        self.write()
        with self.assertRaisesRegex(RuntimeError, "hash mismatch"):
            security.check(self.root)
        record["path"] = "../outside.log"
        self.write()
        with self.assertRaisesRegex(RuntimeError, "outside"):
            security.check(self.root)

    def test_new_source_drift_invalidates_evidence(self):
        self.matrix["source_fingerprint"] = "0" * 64
        self.write()
        with self.assertRaisesRegex(RuntimeError, "fingerprint drift"):
            security.check(self.root)

    def test_9c_marker_retains_all_prior_security_and_native_gates(self):
        import check_security_9a
        import check_security_9b

        spec = importlib.util.spec_from_file_location("verifier_9c", ROOT / "scripts/verify.py")
        verifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(verifier)
        with patch.multiple(verifier, PHASE=8, SUBPHASE="9C"), patch.object(check_security_9a, "check") as a, patch.object(check_security_9b, "check") as b, patch.object(security, "check") as c, patch.object(verifier, "native_closeout_check", side_effect=RuntimeError("prior native required")):
            with self.assertRaisesRegex(RuntimeError, "prior native"):
                verifier.phase_marker_check()
            a.assert_called_once_with(completed=True)
            b.assert_called_once_with(completed=True)
            c.assert_called_once_with(completed=True)


if __name__ == "__main__":
    unittest.main()
