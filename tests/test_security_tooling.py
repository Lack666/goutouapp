"""Controlled fake credentials exercise error evidence without printing secrets."""

import importlib.util
import subprocess
import sys
import traceback
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_phase8_evidence import categories  # noqa: E402


class SecurityToolingTests(unittest.TestCase):
    def test_history_privacy_screen(self):
        from audit_phase8_evidence import audit
        result = audit()
        self.assertGreater(result["files"], 50)
        self.assertEqual(result["findings"], [])

    def test_fake_credentials_are_detected_without_returning_values(self):
        fake = "Bearer PHASE9A_FAKE_TOKEN_SENTINEL"
        self.assertEqual(categories(fake), ["authorization_value"])
        self.assertEqual(categories("postgresql://synthetic:FAKE_PASSWORD@localhost/test"),
                         ["database_password"])
        self.assertEqual(categories("counts=1; authorization required; JWT expired"), [])

    def test_private_subprocess_failures_hide_arguments_and_output(self):
        spec = importlib.util.spec_from_file_location("native_private", ROOT / "scripts/phase8_android_demo.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        marker = "PHASE9A_PRIVATE_SUBPROCESS_SENTINEL"
        command = ["synthetic-adb", marker]
        errors = [subprocess.TimeoutExpired(command, 20, output=marker, stderr=marker),
                  subprocess.CalledProcessError(1, command, output=marker), OSError(marker)]
        for error in errors:
            with patch.object(module.subprocess, "run", side_effect=error):
                try:
                    module.run_private_command(command)
                except RuntimeError:
                    rendered = traceback.format_exc()
                    self.assertNotIn(marker, rendered)
                else:
                    self.fail("Subprocess failure was presented as success")


if __name__ == "__main__":
    unittest.main()
