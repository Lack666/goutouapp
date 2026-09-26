"""Phase 0 and 1 regression checks for the frozen specification."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "upstream" / "goutoujunshi"
MANIFEST = json.loads((ROOT / "upstream" / "manifest.json").read_text(encoding="utf-8"))


class RepositoryTests(unittest.TestCase):
    def test_upstream_inventory_and_hashes(self) -> None:
        actual = {
            p.relative_to(SNAPSHOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in SNAPSHOT.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        }
        self.assertEqual(MANIFEST["files"], actual)
        self.assertEqual(MANIFEST["commit"], "6db7354a4002dc7c448a9c87ffdad8132570c9d3")
        self.assertEqual(len(actual), 63)

    def test_license_and_reference_inventory(self) -> None:
        license_text = (SNAPSHOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("MIT License", license_text)
        self.assertIn("Copyright (c) 2026 powerycy", license_text)
        self.assertEqual(len(list((SNAPSHOT / "references" / "knowledge").glob("*.md"))), 20)
        self.assertEqual(len(list((SNAPSHOT / "references" / "practical").glob("*.md"))), 23)

    def test_monorepo_boundaries(self) -> None:
        for path in (
            "AGENTS.md", "Makefile", "pyproject.toml", "pnpm-workspace.yaml",
            "apps/api/README.md", "apps/mobile/README.md", "packages/agent/README.md",
            "packages/knowledge/README.md", "packages/chat_import/README.md",
            "docs/MASTER_PLAN.md", "docs/ARCHITECTURE.md", "docs/SKILL_CONTRACT.md",
        ):
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).is_file())

    def test_phase_one_dataset_when_enabled(self) -> None:
        phase = json.loads((ROOT / "project-phase.json").read_text(encoding="utf-8"))["completed_phase"]
        if phase < 1:
            self.skipTest("Phase 1 gate deferred")
        import sys

        sys.path.insert(0, str(ROOT / "evals"))
        from validate import validate

        result = validate()
        self.assertGreaterEqual(result["cases"], 40)
        self.assertGreaterEqual(result["high_risk"], 8)


if __name__ == "__main__":
    unittest.main()
