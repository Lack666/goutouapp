"""Phase 1B checks for static Golden data and validator failure modes."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from evals.validate import CONTRACT, REFERENCE_MAP, contract_rule_ids, load_cases, validate, validate_cases


class GoldenDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = load_cases()
        cls.references = json.loads(Path(REFERENCE_MAP).read_text(encoding="utf-8"))
        cls.rules = contract_rule_ids(Path(CONTRACT).read_text(encoding="utf-8"))

    def errors_after(self, case_id: str, change) -> list[str]:
        cases = copy.deepcopy(self.cases)
        case = next(case for case in cases if case["id"] == case_id)
        change(case)
        return validate_cases(cases, self.references, self.rules)

    def test_full_static_dataset(self) -> None:
        result = validate()
        self.assertGreaterEqual(result["cases"], 55)
        self.assertEqual(result["minimal_pairs"], 6)

    def test_invalid_source_and_reference_are_rejected(self) -> None:
        errors = self.errors_after("pair_b2", lambda case: (
            case["contract_rules"].append("4.99"),
            case["expected"]["knowledge"]["allowed"].append("missing_reference"),
        ))
        self.assertTrue(any("unknown contract rule" in error for error in errors))
        self.assertTrue(any("unknown or missing reference" in error for error in errors))

    def test_safety_precedence_and_memory_consent_are_rejected_if_removed(self) -> None:
        errors = self.errors_after("pair_e2", lambda case: case["expected"].update(route="ordinary"))
        self.assertTrue(any("high-risk case" in error for error in errors))
        errors = self.errors_after("pair_d1", lambda case: case["expected"]["assertions"].remove("consent_recorded"))
        self.assertTrue(any("explicit consent" in error for error in errors))

    def test_pair_contrast_must_change(self) -> None:
        errors = self.errors_after("pair_d2", lambda case: (
            case["expected"].update(memory_writes=1),
            case["expected"]["memory"].update(decision="allow_candidate", source="user_explicit"),
            case["expected"]["assertions"].append("consent_recorded"),
        ))
        self.assertTrue(any("pair D: input and contrast expectation must differ" in error for error in errors))

    def test_unknown_behavior_is_rejected(self) -> None:
        errors = self.errors_after("reply_01", lambda case: case["expected"]["assertions"].append("made_up_behavior"))
        self.assertTrue(any("unknown required behavior" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
