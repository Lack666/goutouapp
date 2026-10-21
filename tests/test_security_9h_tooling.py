"""Evidence counterexamples: no prose, partial native or source drift waiver."""

import ast
import hashlib
import json
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_security_9h as security  # noqa: E402


class Phase9HEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "docs/evidence/phase9h").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def artifact(self, name, value):
        path = self.root / "docs/evidence/phase9h" / name
        path.write_text(value, "utf-8")
        return {
            "path": path.relative_to(self.root).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    def build(self):
        return {
            "native_build": {
                "compiled_mobile_fingerprint": "a" * 64,
                "expected_mobile_fingerprint": "a" * 64,
                "verified": True,
                "transport": "actual Android accessibility",
            }
        }

    def record(self, *, source="current", end="current", exit="0", text="49 passed"):
        log = self.artifact("run.log", text)
        return {
            "log": log,
            "exit": self.artifact("run.exit", exit),
            "exit_code": int(exit),
            "source": self.artifact(
                "run.source.json",
                json.dumps(
                    {
                        "source_fingerprint": source,
                        "end_source_fingerprint": end,
                        "log_sha256": log["sha256"],
                        "exit_code": int(exit),
                        "phase_marker": {"completed_phase": 8, "completed_subphase": "9G"},
                        "command": ["make.cmd", "verify"],
                    }
                ),
            ),
        }

    def test_path_escape_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "outside"):
            security.artifact({"path": "../private", "sha256": "fake"}, self.root)

    def test_changed_log_rejected(self):
        record = self.record()
        (self.root / record["log"]["path"]).write_text("PASS", "utf-8")
        with self.assertRaisesRegex(RuntimeError, "hash"):
            security.gate(record, self.root)

    def test_failed_exit_cannot_be_replaced_by_pass_text(self):
        with self.assertRaisesRegex(RuntimeError, "zero exit"):
            security.gate(self.record(exit="1", text="PASS"), self.root)

    def test_both_execution_time_source_fingerprints_required(self):
        with patch.object(security, "fingerprint", return_value="current"):
            for source, end in (("old", "current"), ("current", "old")):
                with self.assertRaisesRegex(RuntimeError, "source fingerprint"):
                    security.gate(self.record(source=source, end=end), self.root)

    def test_valid_current_focused_record_is_only_focused(self):
        with patch.object(security, "fingerprint", return_value="current"):
            self.assertEqual(security.gate(self.record(), self.root)[0], "49 passed")
            with self.assertRaisesRegex(RuntimeError, "complete root"):
                security.root_gate(
                    self.record(), self.root, {"completed_phase": 8, "completed_subphase": "9G"}
                )

    def test_root_marker_cannot_be_inferred_from_prose(self):
        with patch.object(security, "fingerprint", return_value="current"):
            with self.assertRaisesRegex(RuntimeError, "marker provenance"):
                security.root_gate(
                    self.record(), self.root, {"completed_phase": 9, "completed_subphase": "9H"}
                )

    def test_all_thirteen_current_android_scenes_required(self):
        with patch.object(security, "runtime_files", return_value={}):
            with self.assertRaisesRegex(RuntimeError, "thirteen"):
                security.native({"native": []}, self.root)

    def test_supplement_requires_complete_exact_original_flow_and_current_runtime(self):
        steps = ["restart", "tap synthetic", "evidence", "stop"]
        report = [
            {"execution": {"steps": steps, "runtime_fingerprint_9h": "runtime"}},
            *({"command": s.partition(" ")[0], "status": "done"} for s in steps[:-1]),
            {"database": {"wire": {"requests": []}}},
        ]
        for invalid in ("changed_steps", "partial", "failed", "stale_runtime"):
            with self.subTest(invalid=invalid):
                rows = json.loads(json.dumps(report))
                if invalid == "changed_steps":
                    rows[0]["execution"]["steps"] = ["evidence", "stop"]
                elif invalid == "partial":
                    rows.pop(2)
                elif invalid == "failed":
                    rows.append({"status": "failed"})
                else:
                    rows[0]["execution"]["runtime_fingerprint_9h"] = "old"
                row = {"report": self.artifact("supplement.json", json.dumps(rows))}
                with patch.object(security, "gate", return_value=("", {"synthetic_only": True})):
                    with self.assertRaisesRegex(RuntimeError, "stale|partial/spliced/failed"):
                        security.native_report(row, self.root, steps, "runtime", current=True)

    def test_complete_wire_supplement_retains_raw_signed_requests_and_strict_capture_gate(self):
        steps = ["restart", "evidence", "stop"]
        request = {
            "path": "/api/v1/lifecycle-erasures/receipts/id",
            "bearer": True,
            "status": 200,
            "host_setup": False,
        }
        rows = [
            {"execution": {"steps": steps, "runtime_fingerprint_9h": "runtime"}},
            self.build(),
            {"command": "restart", "status": "done"},
            {"command": "evidence", "status": "done"},
            {"database": {"wire": {"requests": [request]}}},
        ]
        row = {"report": self.artifact("supplement.json", json.dumps(rows))}
        with (
            patch.object(security, "gate", return_value=("", {"synthetic_only": True})) as gate,
            patch.object(security, "compiled_mobile_fingerprint", return_value="a" * 64),
        ):
            _, requests = security.native_report(row, self.root, steps, "runtime", current=True)
        gate.assert_called_once_with(row, self.root, current=True)
        self.assertEqual(requests, [request])

    def test_supplement_cannot_borrow_signed_operations_from_another_execution(self):
        canonical = ["restart", "stop"]
        folder = self.root / "scripts/native"
        folder.mkdir(parents=True)
        (folder / "faults.json").write_text(json.dumps(canonical), "utf-8")
        runtime = hashlib.sha256(json.dumps({}, sort_keys=True).encode()).hexdigest()

        def execution(name, steps, suffixes):
            requests = [
                {
                    "path": "/api/v1/lifecycle-erasures/" + suffix,
                    "bearer": True,
                    "status": 200,
                    "host_setup": False,
                }
                for suffix in suffixes
            ]
            rows = [
                {"execution": {"steps": steps, "runtime_fingerprint_9h": runtime}},
                self.build(),
                *({"command": step, "status": "done"} for step in steps[:-1]),
                {"database": {"wire": {"requests": requests}}},
            ]
            return {"report": self.artifact(name, json.dumps(rows))}

        row = {
            "scene": "lifecycle_faults",
            **execution("primary.json", canonical, ["prepare", "execute"]),
            "wire_supplement": execution(
                "extra.json", ["restart", "evidence", "stop"], ["receipts/id"]
            ),
        }
        with (
            patch.object(security, "SCENES", {"lifecycle_faults": "faults.json"}),
            patch.object(security, "runtime_files", return_value={}),
            patch.object(security, "compiled_mobile_fingerprint", return_value="a" * 64),
            patch.object(security, "gate", return_value=("", {"synthetic_only": True})),
        ):
            with self.assertRaisesRegex(RuntimeError, "formal lifecycle"):
                security.native({"native": [row]}, self.root)

    def test_filesystem_hash_cannot_replace_actual_compiled_native_source(self):
        steps = ["restart", "stop"]
        for invalid in ("missing", "compiled", "expected", "verified", "transport"):
            with self.subTest(invalid=invalid):
                build = self.build()
                proof = build["native_build"]
                if invalid == "compiled":
                    proof["compiled_mobile_fingerprint"] = "b" * 64
                elif invalid == "expected":
                    proof["expected_mobile_fingerprint"] = "b" * 64
                elif invalid == "verified":
                    proof["verified"] = False
                elif invalid == "transport":
                    proof["transport"] = "filesystem/source map only"
                rows = [
                    {"execution": {"steps": steps, "runtime_fingerprint_9h": "runtime"}},
                    *([] if invalid == "missing" else [build]),
                    {"command": "restart", "status": "done"},
                    {"database": {"wire": {"requests": []}}},
                ]
                row = {"report": self.artifact("compiled.json", json.dumps(rows))}
                with (
                    patch.object(security, "gate", return_value=("", {"synthetic_only": True})),
                    patch.object(security, "compiled_mobile_fingerprint", return_value="a" * 64),
                    self.assertRaisesRegex(RuntimeError, "actual compiled Android source"),
                ):
                    security.native_report(row, self.root, steps, "runtime", current=True)

    def test_live_android_marker_rejects_missing_stale_or_conflicting_loaded_builds(self):
        from phase8_android_demo import compiled_build_proof

        expected = "a" * 64
        current = ET.Element("node", {"content-desc": "NATIVE-BUILD " + expected})
        old = ET.Element("node", {"text": "NATIVE-BUILD " + "b" * 64})
        self.assertTrue(compiled_build_proof([current], expected)["verified"])
        for nodes in ([], [old], [current, old]):
            with (
                self.subTest(markers=len(nodes)),
                self.assertRaisesRegex(RuntimeError, "missing or stale"),
            ):
                compiled_build_proof(nodes, expected)

    def test_compiled_source_proof_changes_when_metro_configuration_changes(self):
        from check_security_9b import mobile_fingerprint
        from phase8_android_demo import compiled_mobile_fingerprint

        mobile = self.root / "apps/mobile"
        (mobile / "src").mkdir(parents=True)
        (mobile / "app").mkdir()
        (mobile / "package.json").write_text("{}", "utf-8")
        (self.root / "pnpm-lock.yaml").write_text("lockfileVersion: 9", "utf-8")
        configuration = mobile / "metro.config.js"
        configuration.write_text("module.exports = {resolver: {}};", "utf-8")
        old_source = mobile_fingerprint(self.root)
        old_build = compiled_mobile_fingerprint(self.root)
        configuration.write_text("module.exports = {resolver: {sourceExts: []}};", "utf-8")
        self.assertEqual(mobile_fingerprint(self.root), old_source)
        self.assertNotEqual(compiled_mobile_fingerprint(self.root), old_build)

    def test_historical_matrix_cannot_be_rewritten(self):
        (self.root / "docs/PHASE_9G_MATRIX.json").write_text('{"phase":"fake"}', "utf-8")
        with patch.object(security, "pinned_matrix", return_value=b'{"phase":"9G"}'):
            with self.assertRaisesRegex(RuntimeError, "differs from Git"):
                security.historical(self.root, "9G")

    def test_historical_evidence_cannot_be_rehashed_in_matrix(self):
        original = json.dumps({"gate": {"path": "docs/evidence/phase9h/old.log", "sha256": "old"}})
        (self.root / "docs/PHASE_9G_MATRIX.json").write_text(original, "utf-8")
        with patch.object(security, "pinned_matrix", return_value=original.encode()):
            with self.assertRaisesRegex(RuntimeError, "historical artifact"):
                security.historical(self.root, "9G")

    def test_missing_9h_does_not_waive_any_old_gate(self):
        self.assertFalse(security.revalidate_prior("9G", self.root))

    def test_whole_phase_marker_requires_independent_pre_marker_evidence(self):
        import verify

        with ExitStack() as stack:
            stack.enter_context(patch.multiple(verify, PHASE=9, SUBPHASE="9H"))
            for phase in ("9a", "9b", "9c", "9d", "9e", "9f", "9g"):
                module = __import__("check_security_" + phase)
                stack.enter_context(patch.object(module, "check"))
            check = stack.enter_context(
                patch.object(
                    security, "check", side_effect=RuntimeError("independent pre-marker required")
                )
            )
            with self.assertRaisesRegex(RuntimeError, "independent pre-marker"):
                verify.phase_marker_check()
            check.assert_called_once_with(completed=True)

    def test_whole_phase_marker_rejects_partial_original_engineering_criterion(self):
        import verify

        (self.root / "docs/PHASE_9_EXIT_CRITERIA_MATRIX.json").write_text(
            json.dumps({"requirements": [{"status": "PARTIAL", "blocks_phase9": True}]}), "utf-8"
        )
        with ExitStack() as stack:
            stack.enter_context(patch.multiple(verify, PHASE=9, SUBPHASE="9H", ROOT=self.root))
            for phase in ("9a", "9b", "9c", "9d", "9e", "9f", "9g", "9h"):
                module = __import__("check_security_" + phase)
                stack.enter_context(patch.object(module, "check"))
            with self.assertRaisesRegex(RuntimeError, "every original engineering"):
                verify.phase_marker_check()

    def test_missing_implementation_gate_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "Missing"):
            security.check(self.root)


class NativeTapViewportTests(unittest.TestCase):
    def run_tap(self, control, *, reveal_on_up=False):
        source = ast.parse((ROOT / "scripts/phase8_android_demo.py").read_text("utf-8"))
        tap = next(
            n for n in ast.walk(source) if isinstance(n, ast.FunctionDef) and n.name == "tap"
        )
        viewport = ET.Element("node", {"scrollable": "true", "bounds": "[0,142][1080,1909]"})
        node = ET.Element("node", control)
        calls = []

        def adb(*parts):
            calls.append(parts)
            if reveal_on_up and parts[:3] == ("shell", "input", "swipe"):
                if int(parts[4]) > int(parts[6]):
                    node.set("bounds", "[174,1500][908,1630]")

        namespace = {
            "nodes": lambda: [viewport, node],
            "adb": adb,
            "screen_height": 2424,
            "re": re,
            "time": SimpleNamespace(sleep=lambda _: None),
        }
        exec(compile(ast.Module(body=[tap], type_ignores=[]), "native-tap", "exec"), namespace)
        return namespace["tap"], calls

    def test_chat_receipt_clipped_by_fixed_composer_scrolls_up(self):
        # Exact r16 failure geometry: the receipt is below the list's1909px edge,
        # but above the full screen's footer threshold. Scrolling down oscillates.
        tap, calls = self.run_tap(
            {"text": "receipt", "bounds": "[174,2278][908,1909]", "enabled": "true"},
            reveal_on_up=True,
        )
        tap("receipt")
        self.assertEqual(calls[0][:3], ("shell", "input", "swipe"))
        self.assertGreater(int(calls[0][4]), int(calls[0][6]))
        self.assertEqual(calls[-1][:3], ("shell", "input", "tap"))
        self.assertTrue(142 < int(calls[-1][4]) < 1909)
        self.assertEqual(len(calls), 2)

    def test_inverted_or_disabled_controls_never_receive_a_click(self):
        for bounds, enabled in (
            ("[174,2278][908,1909]", "true"),
            ("[174,1500][908,1630]", "false"),
        ):
            with self.subTest(bounds=bounds, enabled=enabled):
                tap, calls = self.run_tap({"text": "receipt", "bounds": bounds, "enabled": enabled})
                with self.assertRaisesRegex(RuntimeError, "control is unavailable"):
                    tap("receipt")
                self.assertEqual(len(calls), 24)
                self.assertTrue(all(parts[2] == "swipe" for parts in calls))

    def test_fixed_composer_button_remains_clickable_outside_list(self):
        tap, calls = self.run_tap(
            {"text": "send", "bounds": "[108,2200][900,2320]", "enabled": "true"}
        )
        tap("send")
        self.assertEqual(calls, [("shell", "input", "tap", "504", "2260")])


if __name__ == "__main__":
    unittest.main()
