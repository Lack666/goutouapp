"""Reject premature/future phase markers without executing external tool gates."""

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("phase_verifier", ROOT / "scripts/verify.py")
assert SPEC and SPEC.loader
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


class MobilePhaseGateTests(unittest.TestCase):
    def test_complete_7d_marker_is_supported(self) -> None:
        with patch.multiple(verifier, PHASE=7, SUBPHASE="7D"):
            verifier.phase_marker_check()

    def test_7c_does_not_complete_phase_seven(self) -> None:
        with patch.multiple(verifier, PHASE=7, SUBPHASE="7C"):
            with self.assertRaisesRegex(RuntimeError, "all Mobile subphase gates"):
                verifier.phase_marker_check()

    def test_missing_integration_gate_prevents_completion(self) -> None:
        with patch.multiple(verifier, PHASE=7, SUBPHASE="7D", MOBILE_FINAL_UI=False):
            with self.assertRaisesRegex(RuntimeError, "all Mobile subphase gates"):
                verifier.phase_marker_check()

    def test_phase_eight_is_not_claimed_by_mobile_mvp(self) -> None:
        with patch.multiple(verifier, PHASE=8):
            with self.assertRaisesRegex(RuntimeError, "Phase 8"):
                verifier.phase_marker_check()
