"""9E does not waive prior evidence, current-source regression or production gaps."""

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
import check_security_9e as security


class Security9EGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.matrix = json.loads((ROOT / "docs/PHASE_9E_MATRIX.json").read_text("utf-8"))
        paths = set(security.REQUIRED) | {
            "docs/DATA_DELETION_MATRIX.json",
            "docs/PHASE_9C_MATRIX.json",
            "docs/PHASE_9D_MATRIX.json",
        }
        for refs in self.matrix["coverage"].values():
            paths.update(ref.partition("::")[0] for ref in refs)
        for value in self.matrix.values():
            if isinstance(value, dict) and "log" in value and "exit" in value:
                paths.update(value[k]["path"] for k in ("log", "exit"))
        for row in self.matrix["native"]["scenes"]:
            paths.update(value["path"] for value in row["artifacts"].values())
        for name in paths:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, path)
        mocks = (
            patch.object(
                security, "source_fingerprint", return_value=self.matrix["source_fingerprint"]
            ),
            patch.object(
                security,
                "admission_fingerprint",
                return_value=self.matrix["admission_revalidation"]["source_fingerprint"],
            ),
            patch.object(
                security,
                "lifecycle_fingerprint",
                return_value=self.matrix["lifecycle_revalidation"]["source_fingerprint"],
            ),
            patch(
                "check_security_9b.mobile_fingerprint",
                return_value=self.matrix["native"]["mobile_fingerprint"],
            ),
        )
        for mock in mocks:
            mock.start()
            self.addCleanup(mock.stop)
        self.write()

    def write(self):
        (self.root / "docs/PHASE_9E_MATRIX.json").write_text(json.dumps(self.matrix), "utf-8")

    def test_actual_evidence_and_explicit_backend_only_limits(self):
        security.check(self.root)

    def test_production_claim_missing_coverage_and_source_drift_rejected(self):
        original = copy.deepcopy(self.matrix)
        for mutate in (
            lambda m: m.update(delivery="App"),
            lambda m: m.update(app_self_service_erasure=True),
            lambda m: m.update(full_account_erasure=True),
            lambda m: m.update(production_disaster_recovery=True),
            lambda m: m.update(authoritative_current_primary_required=False),
            lambda m: m.update(open_p0_p1=["unresolved"]),
            lambda m: m.update(source_fingerprint="0" * 64),
            lambda m: m["coverage"].pop("replay"),
        ):
            self.matrix = copy.deepcopy(original)
            mutate(self.matrix)
            self.write()
            with self.assertRaises(RuntimeError):
                security.check(self.root)

    def test_missing_or_changed_real_evidence_cannot_pass(self):
        original = copy.deepcopy(self.matrix)
        for mutate in (
            lambda m: m["focused"].update(exit_code=1),
            lambda m: m["focused"]["log"].update(sha256="0" * 64),
            lambda m: m["demo"]["log"].update(path="../outside.log"),
            lambda m: m["native"]["scenes"].pop(),
        ):
            self.matrix = copy.deepcopy(original)
            mutate(self.matrix)
            self.write()
            with self.assertRaises(RuntimeError):
                security.check(self.root)

    def test_current_source_and_original_prior_matrix_are_both_required(self):
        for name, fingerprint, original, expected in (
            (
                "admission_revalidation",
                self.matrix["admission_revalidation"]["source_fingerprint"],
                "docs/PHASE_9C_MATRIX.json",
                "27 passed",
            ),
            (
                "lifecycle_revalidation",
                self.matrix["lifecycle_revalidation"]["source_fingerprint"],
                "docs/PHASE_9D_MATRIX.json",
                "44 passed",
            ),
        ):
            changed = copy.deepcopy(self.matrix)
            changed[name]["historical_matrix_sha256"] = "0" * 64
            with self.assertRaises(RuntimeError):
                security.revalidation(changed, self.root, name, fingerprint, original, expected)

    def test_baseline_cannot_be_relabelled_as_final_root(self):
        with self.assertRaisesRegex(RuntimeError, "current-source root"):
            security.root_gate(self.matrix["baseline"], self.root, "9D")

    def test_marker_preserves_all_old_gates_and_rejects_next_phase(self):
        import check_security_9a as a
        import check_security_9b as b
        import check_security_9c as c
        import check_security_9d as d

        spec = importlib.util.spec_from_file_location("verifier_9e", ROOT / "scripts/verify.py")
        verifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(verifier)
        with (
            patch.multiple(verifier, PHASE=8, SUBPHASE="9E"),
            patch.object(a, "check") as ga,
            patch.object(b, "check") as gb,
            patch.object(c, "check") as gc,
            patch.object(d, "check") as gd,
            patch.object(security, "check") as ge,
            patch.object(
                verifier, "native_closeout_check", side_effect=RuntimeError("old native required")
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "old native"):
                verifier.phase_marker_check()
            for gate in (ga, gb, gc, gd, ge):
                gate.assert_called_once_with(completed=True)
        # 9F through 9H are authorized; unsupported stages must still refuse.
        for phase, subphase in ((8, "9I"), (9, None), (10, None)):
            with (
                patch.multiple(verifier, PHASE=phase, SUBPHASE=subphase),
                self.assertRaises(RuntimeError),
            ):
                verifier.phase_marker_check()
