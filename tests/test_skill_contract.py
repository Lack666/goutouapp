"""Phase 1A acceptance checks for the frozen Skill behavior contract."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "SKILL_CONTRACT.md"
UPSTREAM = ROOT / "knowledge" / "goutoujunshi"


class SkillContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = CONTRACT.read_text(encoding="utf-8")

    def section(self, start: str, end: str) -> str:
        return self.text.split(start, 1)[1].split(end, 1)[0]

    def test_contract_identifies_frozen_source_and_required_sections(self) -> None:
        manifest = json.loads(
            (ROOT / "knowledge" / "upstream-manifest.json").read_text(encoding="utf-8")
        )
        self.assertIn(manifest["source_url"], self.text)
        self.assertIn(manifest["commit"], self.text)
        self.assertIn("MIT", self.text)
        for heading in (
            "Purpose",
            "Scope",
            "Scenario Taxonomy",
            "Core Reasoning Principles",
            "Facts / Inferences / Unknowns",
            "Knowledge Routing",
            "Response Behaviour",
            "Memory Contract",
            "Safety Contract",
            "Anti-Patterns",
            "Open Questions",
            "Source Mapping",
        ):
            with self.subTest(heading=heading):
                self.assertRegex(self.text, rf"(?m)^## \d+\. {re.escape(heading)}")

    def test_scenarios_examples_and_anti_patterns_are_substantive(self) -> None:
        scenarios = self.section("## 3. Scenario Taxonomy", "## 4.")
        self.assertGreaterEqual(len(re.findall(r"(?m)^\|[^|-].*\|$", scenarios)) - 2, 15)
        examples = self.section("### 5.2 判定示例", "## 6.")
        self.assertGreaterEqual(len(re.findall(r"(?m)^\|[^|-].*\|$", examples)) - 2, 5)
        anti_patterns = self.section("## 10. Anti-Patterns", "## 11.")
        self.assertGreaterEqual(len(re.findall(r"(?m)^\d+\. ", anti_patterns)), 10)
        for marker in ("**MUST**", "**SHOULD**", "**MUST NOT**", "无明确同意，长期记忆写入为零"):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.text)

    def test_every_upstream_reference_is_traceable_in_contract(self) -> None:
        references = sorted((UPSTREAM / "references").rglob("*.md"))
        self.assertEqual(len(references), 43)
        for reference in references:
            with self.subTest(reference=reference.name):
                self.assertIn(reference.name, self.text)


if __name__ == "__main__":
    unittest.main()
