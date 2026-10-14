"""9D marker/evidence and current-source 9C regression cannot be waived."""

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
import check_security_9c as prior
import check_security_9d as security


class Security9DGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.matrix = json.loads((ROOT / "docs/PHASE_9D_MATRIX.json").read_text("utf-8"))
        older = json.loads((ROOT / "docs/PHASE_9C_MATRIX.json").read_text("utf-8"))
        paths = set(security.REQUIRED) | set(prior.REQUIRED)
        paths.add("docs/PHASE_9C_MATRIX.json")
        for matrix in (self.matrix, older):
            for references in matrix["coverage"].values():
                paths.update(reference.partition("::")[0] for reference in references)
            for record in matrix.values():
                if isinstance(record, dict) and "log" in record and "exit" in record:
                    paths.update(record[k]["path"] for k in ("log", "exit"))
        for name in paths:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, path)
        self.mock_source = patch.object(security, "source_fingerprint", return_value=self.matrix["source_fingerprint"])
        self.mock_source.start()
        self.addCleanup(self.mock_source.stop)
        self.write()

    def write(self):
        (self.root / "docs/PHASE_9D_MATRIX.json").write_text(json.dumps(self.matrix), "utf-8")

    def test_actual_local_native_restore_evidence_and_production_limits(self):
        security.check(self.root)

    def test_no_production_waiver_incomplete_scope_or_missing_coverage(self):
        original = copy.deepcopy(self.matrix)
        for mutate in (
            lambda m: m.update(production_acceptable=True),
            lambda m: m.update(open_p0_p1=["unresolved"]),
            lambda m: m["recovery_scope"].update(authoritative_current_primary_required=False),
            lambda m: m["recovery_scope"].update(production_disaster_recovery=True),
            lambda m: m["coverage"].pop("restore_race"),
            lambda m: m.update(source_fingerprint="0" * 64),
        ):
            self.matrix = copy.deepcopy(original)
            mutate(self.matrix)
            self.write()
            with self.assertRaises(RuntimeError):
                security.check(self.root)

    def test_evidence_hash_path_and_nonzero_exit_fail_closed(self):
        original = copy.deepcopy(self.matrix)
        for mutate in (
            lambda m: m["focused"].update(exit_code=1),
            lambda m: m["demo"]["log"].update(sha256="0" * 64),
            lambda m: m["demo"]["log"].update(path="../outside.log"),
        ):
            self.matrix = copy.deepcopy(original)
            mutate(self.matrix)
            self.write()
            with self.assertRaises(RuntimeError):
                security.check(self.root)

    def test_marker_requires_success_and_independent_pre_post(self):
        self.matrix["status"] = "IN PROGRESS"
        self.write()
        with self.assertRaisesRegex(RuntimeError, "requires PASS"):
            security.check(self.root, completed=True)
        self.matrix["status"] = "PASS"
        self.matrix["pre_marker"] = copy.deepcopy(self.matrix["baseline"])
        self.matrix["pre_marker"]["exit_code"] = 1
        self.write()
        with self.assertRaisesRegex(RuntimeError, "zero exit"):
            security.check(self.root, completed=True)
        self.matrix["pre_marker"] = copy.deepcopy(self.matrix["baseline"])
        self.matrix["post_marker"] = copy.deepcopy(self.matrix["baseline"])
        self.matrix["acceptance_state"] = "closed"
        self.write()
        with patch.object(security, "root_gate"), self.assertRaisesRegex(RuntimeError, "independent pre/post"):
            security.check(self.root, completed=True)

    def test_old_baseline_is_not_current_stage_pre_or_post_root_proof(self):
        with self.assertRaisesRegex(RuntimeError, "current-source root evidence"):
            security.root_gate(self.matrix["baseline"], self.root, subphase="9C")

    def test_current_9c_source_needs_fresh_complete_regression_and_original_hash(self):
        expected = self.matrix["admission_revalidation"]["source_fingerprint"]
        with patch.object(prior, "source_fingerprint", return_value=expected):
            prior.check(self.root, completed=True)
            self.matrix["admission_revalidation"]["historical_matrix_sha256"] = "0" * 64
            self.write()
            with self.assertRaisesRegex(RuntimeError, "fingerprint drift"):
                prior.check(self.root, completed=True)

    def test_9d_keeps_all_old_security_and_native_gates_and_rejects_next_phase(self):
        import check_security_9a
        import check_security_9b
        spec = importlib.util.spec_from_file_location("verifier_9d", ROOT / "scripts/verify.py")
        verifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(verifier)
        with patch.multiple(verifier, PHASE=8, SUBPHASE="9D"), \
             patch.object(check_security_9a, "check") as a, \
             patch.object(check_security_9b, "check") as b, \
             patch.object(prior, "check") as c, patch.object(security, "check") as d, \
             patch.object(verifier, "native_closeout_check", side_effect=RuntimeError("prior native required")):
            with self.assertRaisesRegex(RuntimeError, "prior native"):
                verifier.phase_marker_check()
            for gate in (a, b, c, d):
                gate.assert_called_once_with(completed=True)
        for phase, subphase in ((8, "9G"), (9, None), (10, None)):
            with patch.multiple(verifier, PHASE=phase, SUBPHASE=subphase), self.assertRaises(RuntimeError):
                verifier.phase_marker_check()


if __name__ == "__main__":
    unittest.main()
