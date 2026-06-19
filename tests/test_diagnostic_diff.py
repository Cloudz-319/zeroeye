import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from tools.diagnostic_diff import compare_metadata, load_metadata, main


class DiagnosticDiffTests(unittest.TestCase):
    def test_diff_generation_tracks_fields_and_module_timing(self):
        before = {
            "commit": "abc123",
            "passed": 1,
            "modules": [
                {"name": "backend", "status": "PASS", "elapsed_seconds": 1.2},
            ],
        }
        after = {
            "commit": "def456",
            "passed": 1,
            "failed": 0,
            "modules": [
                {"name": "backend", "status": "PASS", "elapsed_seconds": 2.5},
                {"name": "frontend", "status": "PASS", "elapsed_seconds": 0.4},
            ],
        }

        diff = compare_metadata(before, after)

        self.assertEqual(diff["added"], {"failed": 0})
        self.assertEqual(diff["changed"]["commit"], {"before": "abc123", "after": "def456"})
        self.assertEqual(diff["modules"]["added"], ["frontend"])
        self.assertEqual(
            diff["modules"]["elapsed_seconds"]["backend"],
            {"before": 1.2, "after": 2.5, "delta": 1.3},
        )
        self.assertFalse(diff["has_regressions"])

    def test_empty_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            empty = Path(temp_dir) / "empty.json"
            empty.write_text("", encoding="utf-8")

            with self.assertRaises(ValueError):
                load_metadata(empty)

            with redirect_stderr(StringIO()):
                self.assertEqual(main([str(empty), str(empty)]), 2)

    def test_status_regression_returns_non_zero(self):
        before = {
            "modules": [
                {"name": "api", "status": "PASS", "elapsed_seconds": 1.0},
            ]
        }
        after = {
            "modules": [
                {"name": "api", "status": "FAIL", "elapsed_seconds": 1.1},
            ]
        }

        diff = compare_metadata(before, after)

        self.assertTrue(diff["has_regressions"])
        self.assertEqual(
            diff["regressions"],
            [{"module": "api", "type": "status", "before": "PASS", "after": "FAIL"}],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            before_path = Path(temp_dir) / "before.json"
            after_path = Path(temp_dir) / "after.json"
            before_path.write_text(json.dumps(before), encoding="utf-8")
            after_path.write_text(json.dumps(after), encoding="utf-8")
            with redirect_stdout(StringIO()):
                self.assertEqual(main([str(before_path), str(after_path)]), 1)


if __name__ == "__main__":
    unittest.main()
