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

    def test_8a_keeps_phase_seven_complete_and_phase_eight_incomplete(self) -> None:
        with patch.multiple(verifier, PHASE=7, SUBPHASE="8A"):
            verifier.phase_marker_check()

    def test_8a_requires_resource_gate(self) -> None:
        with patch.multiple(verifier, PHASE=7, SUBPHASE="8A", PUBLIC_RESOURCES_API=False):
            with self.assertRaisesRegex(RuntimeError, "resource gates"):
                verifier.phase_marker_check()

    def test_8a_cannot_skip_phase_seven(self) -> None:
        with patch.multiple(verifier, PHASE=6, SUBPHASE="8A"):
            with self.assertRaisesRegex(RuntimeError, "complete Phase 7"):
                verifier.phase_marker_check()

    def test_8b_requires_connected_implementation(self) -> None:
        with patch.multiple(verifier, PHASE=7, SUBPHASE="8B", MOBILE_CONNECTED=False):
            with self.assertRaisesRegex(RuntimeError, "connected Mobile gates"):
                verifier.phase_marker_check()

    def test_8b_keeps_phase_eight_incomplete(self) -> None:
        with patch.multiple(verifier, PHASE=7, SUBPHASE="8B"):
            verifier.phase_marker_check()

    def test_8c_is_not_supported_by_8b(self) -> None:
        with patch.multiple(verifier, PHASE=7, SUBPHASE="8C", MOBILE_AGENT_CHAT=False):
            with self.assertRaisesRegex(RuntimeError, "Agent Chat gates"):
                verifier.phase_marker_check()

    def test_8c_keeps_phase_eight_incomplete(self) -> None:
        with patch.multiple(verifier, PHASE=7, SUBPHASE="8C"):
            verifier.phase_marker_check()

    def test_8c_cannot_skip_phase_seven(self) -> None:
        with patch.multiple(verifier, PHASE=6, SUBPHASE="8C"):
            with self.assertRaisesRegex(RuntimeError, "complete Phase 7"):
                verifier.phase_marker_check()

    def test_8d_is_not_supported_by_8c(self) -> None:
        with patch.multiple(verifier, PHASE=7, SUBPHASE="8D"):
            with self.assertRaisesRegex(RuntimeError, "all Mobile subphase gates"):
                verifier.phase_marker_check()

    def test_8b_cannot_skip_phase_seven(self) -> None:
        with patch.multiple(verifier, PHASE=6, SUBPHASE="8B"):
            with self.assertRaisesRegex(RuntimeError, "complete Phase 7"):
                verifier.phase_marker_check()
