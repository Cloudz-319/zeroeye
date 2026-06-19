"""Tests for tools/build_diff.py — structured diagnostic diff utility."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

test_dir = Path(__file__).resolve().parent
root_dir = test_dir.parents[1]

# Direct import of build_diff module
bd_path = str(root_dir / "tools" / "build_diff.py")
import importlib.util
spec = importlib.util.spec_from_file_location("build_diff", bd_path)
bd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bd)
load_report = bd.load_report
diff_scalars = bd.diff_scalars
diff_modules = bd.diff_modules
main = bd.main


def make_metadata(
    commit: str = "abc12345",
    modules: list[dict] | None = None,
    passed: int = 8,
    failed: int = 1,
) -> dict:
    if modules is None:
        modules = [
            {"name": "backend", "status": "PASS", "elapsed_seconds": 12.5, "artifact": None, "output": ""},
            {"name": "frontend", "status": "PASS", "elapsed_seconds": 8.3, "artifact": None, "output": ""},
            {"name": "market", "status": "PASS", "elapsed_seconds": 4.1, "artifact": None, "output": ""},
            {"name": "frailbox", "status": "PASS", "elapsed_seconds": 0.8, "artifact": None, "output": ""},
            {"name": "engine", "status": "PASS", "elapsed_seconds": 15.2, "artifact": None, "output": ""},
            {"name": "compliance", "status": "PASS", "elapsed_seconds": 3.5, "artifact": None, "output": ""},
            {"name": "v2-market-stream", "status": "PASS", "elapsed_seconds": 0.2, "artifact": None, "output": ""},
            {"name": "nfc-scanner", "status": "PASS", "elapsed_seconds": 0.1, "artifact": None, "output": ""},
            {"name": "openapi-haskell", "status": "FAIL", "elapsed_seconds": 45.0, "artifact": None, "output": "GHC error"},
        ]
    return {
        "generated_at": "2026-06-19T12:00:00+00:00",
        "commit": commit,
        "total_modules": len(modules),
        "passed": passed,
        "failed": failed,
        "modules": modules,
    }


import unittest

class TestLoadReport(unittest.TestCase):
    def test_valid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"key": "val"}, f)
            path = f.name
        try:
            result = load_report(Path(path))
            self.assertEqual(result, {"key": "val"})
        finally:
            Path(path).unlink()

class TestDiffScalars(unittest.TestCase):
    def test_identical(self):
        self.assertEqual(diff_scalars("commit", "abc", "abc"), [])
    def test_different(self):
        r = diff_scalars("commit", "abc", "def")
        self.assertIn(" 'abc' -> 'def'", r[0])

class TestDiffModules(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(diff_modules([], []), [])
    def test_added(self):
        old = make_metadata(modules=[{"name": "a", "status": "PASS", "elapsed_seconds": 1.0}])
        new = make_metadata(modules=[{"name": "a", "status": "PASS", "elapsed_seconds": 1.0}, {"name": "b", "status": "PASS", "elapsed_seconds": 2.0}])
        r = diff_modules(old["modules"], new["modules"])
        self.assertTrue(any("+ADDED+" in c for c in r))
    def test_regression(self):
        old = make_metadata(modules=[{"name": "a", "status": "PASS", "elapsed_seconds": 1.0}])
        new = make_metadata(modules=[{"name": "a", "status": "FAIL", "elapsed_seconds": 2.0}])
        r = diff_modules(old["modules"], new["modules"])
        self.assertTrue(any("REGRESSION" in c for c in r))

class TestEndToEnd(unittest.TestCase):
    def test_cli_identical(self):
        data = make_metadata()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f1:
            json.dump(data, f1); p1 = f1.name
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f2:
            json.dump(data, f2); p2 = f2.name
        try:
            r = subprocess.run([sys.executable, bd_path, p1, p2], capture_output=True, text=True, timeout=10)
            self.assertEqual(r.returncode, 0)
        finally:
            Path(p1).unlink(missing_ok=True); Path(p2).unlink(missing_ok=True)
    
    def test_cli_regression(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f1:
            json.dump(make_metadata(modules=[{"name":"a","status":"PASS","elapsed_seconds":1.0}]), f1); p1=f1.name
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f2:
            json.dump(make_metadata(modules=[{"name":"a","status":"FAIL","elapsed_seconds":3.0}]), f2); p2=f2.name
        try:
            r = subprocess.run([sys.executable, bd_path, p1, p2], capture_output=True, text=True, timeout=10)
            self.assertEqual(r.returncode, 1)
            self.assertIn("REGRESSION", r.stdout)
        finally:
            Path(p1).unlink(missing_ok=True); Path(p2).unlink(missing_ok=True)
